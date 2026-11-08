"""La finestra «Keybinding»: scegliere i tasti per ogni azione (come in melonDS).

Una tabella con una riga per azione e due caselle per i tasti:

    Azione               | Tasto 1 | Tasto 2
    Pagina precedente    | Left    | PgUp
    Pagina successiva    | Right   | PgDown
    ...

Si clicca su una casella e si preme il tasto (o la combinazione, es. Ctrl+W).
La ✕ nella casella la svuota. Se lo stesso tasto finisce su due azioni,
il nome di quelle azioni diventa rosso e «Salva» si disattiva finché non si sistema.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from studiopdf.impostazioni import TASTI_PER_AZIONE, trova_conflitti

COLORE_CONFLITTO = QColor("#FADBD8")  # rosa chiaro per il nome delle azioni in conflitto


def chiedi_tasti(
    genitore: QWidget | None,
    azioni: list[tuple[str, str]],
    tasti: dict[str, list[str]],
    predefiniti: dict[str, list[str]],
) -> dict[str, list[str]] | None:
    """Mostra la finestra e restituisce i tasti scelti (None se si annulla)."""
    dialogo = DialogoTasti(genitore, azioni, tasti, predefiniti)
    dialogo.exec()
    return dialogo.risultato


class DialogoTasti(QDialog):
    def __init__(
        self,
        genitore: QWidget | None,
        azioni: list[tuple[str, str]],
        tasti: dict[str, list[str]],
        predefiniti: dict[str, list[str]],
    ) -> None:
        super().__init__(genitore)
        self.setWindowTitle("Keybinding")
        self.resize(560, 480)
        self.risultato: dict[str, list[str]] | None = None

        self._azioni = azioni
        self._predefiniti = predefiniti
        self._descrizioni = dict(azioni)  # chiave -> descrizione, per i messaggi

        # caselle["pagina_successiva"] = [casella tasto 1, casella tasto 2]
        self.caselle: dict[str, list[QKeySequenceEdit]] = {}

        self.tabella = self._crea_tabella()
        self.etichetta_conflitti = QLabel("")
        self.etichetta_conflitti.setStyleSheet("color: #B42318;")  # rosso scuro
        self.etichetta_conflitti.setWordWrap(True)

        # Pulsanti: [Ripristina predefiniti]          [Annulla] [Salva]
        self.pulsante_ripristina = QPushButton("Ripristina predefiniti")
        self.pulsante_annulla = QPushButton("Annulla")
        self.pulsante_salva = QPushButton("Salva")
        self.pulsante_salva.setDefault(True)
        self.pulsante_ripristina.clicked.connect(self._ripristina)
        self.pulsante_annulla.clicked.connect(self.reject)
        self.pulsante_salva.clicked.connect(self._quando_salva)
        riga_pulsanti = QHBoxLayout()
        riga_pulsanti.addWidget(self.pulsante_ripristina)
        riga_pulsanti.addStretch()
        riga_pulsanti.addWidget(self.pulsante_annulla)
        riga_pulsanti.addWidget(self.pulsante_salva)

        colonna = QVBoxLayout(self)
        colonna.addWidget(QLabel("Clicca su una casella e premi il tasto da usare. La ✕ svuota la casella."))
        colonna.addWidget(self.tabella)
        colonna.addWidget(self.etichetta_conflitti)
        colonna.addLayout(riga_pulsanti)

        self._mostra_tasti(tasti)

    # =========================================================================
    # Costruzione della tabella
    # =========================================================================

    def _crea_tabella(self) -> QTableWidget:
        tabella = QTableWidget(len(self._azioni), 1 + TASTI_PER_AZIONE, self)
        tabella.setHorizontalHeaderLabels(["Azione", "Tasto 1", "Tasto 2"])
        tabella.verticalHeader().setVisible(False)  # niente numeri di riga
        tabella.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        intestazione = tabella.horizontalHeader()
        intestazione.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # la colonna "Azione" si allarga

        for riga, (azione, descrizione) in enumerate(self._azioni):
            cella_nome = QTableWidgetItem(descrizione)
            cella_nome.setFlags(cella_nome.flags() & ~Qt.ItemFlag.ItemIsEditable)  # il nome non si modifica
            tabella.setItem(riga, 0, cella_nome)

            self.caselle[azione] = []
            for colonna in range(TASTI_PER_AZIONE):
                casella = QKeySequenceEdit()
                casella.setMaximumSequenceLength(1)  # un solo tasto (o combinazione) per casella
                casella.setClearButtonEnabled(True)  # la ✕ per svuotarla
                casella.keySequenceChanged.connect(self._aggiorna_conflitti)
                tabella.setCellWidget(riga, 1 + colonna, casella)
                self.caselle[azione].append(casella)
        return tabella

    def _mostra_tasti(self, tasti: dict[str, list[str]]) -> None:
        """Riempie le caselle con i tasti indicati."""
        for azione, caselle in self.caselle.items():
            coppia = tasti.get(azione, [""] * TASTI_PER_AZIONE)
            for casella, tasto in zip(caselle, coppia):
                casella.setKeySequence(QKeySequence(tasto))
        self._aggiorna_conflitti()

    # =========================================================================
    # Lettura dei tasti e conflitti
    # =========================================================================

    def tasti_correnti(self) -> dict[str, list[str]]:
        """I tasti scritti ora nelle caselle: {azione: [tasto 1, tasto 2]}."""
        return {
            azione: [casella.keySequence().toString() for casella in caselle]
            for azione, caselle in self.caselle.items()
        }

    def _aggiorna_conflitti(self) -> None:
        """Colora di rosso il nome delle azioni con tasti doppi e disattiva «Salva» se ce ne sono."""
        conflitti = trova_conflitti(self.tasti_correnti())
        azioni_in_conflitto = {azione for elenco in conflitti.values() for azione in elenco}

        for riga, (azione, _) in enumerate(self._azioni):
            colore = COLORE_CONFLITTO if azione in azioni_in_conflitto else QColor(0, 0, 0, 0)
            self.tabella.item(riga, 0).setBackground(colore)

        # trova_conflitti restituisce i tasti in MAIUSCOLO (per confrontarli):
        # per il messaggio usiamo la forma scritta nelle caselle (es. "Right").
        come_scritti = {
            tasto.upper(): tasto for coppia in self.tasti_correnti().values() for tasto in coppia if tasto
        }
        righe_messaggio = [
            f"«{come_scritti.get(tasto, tasto)}» è usato da: "
            + ", ".join(self._descrizioni[a] for a in dict.fromkeys(elenco))  # dict.fromkeys toglie i doppioni
            for tasto, elenco in conflitti.items()
        ]
        self.etichetta_conflitti.setText("\n".join(righe_messaggio))
        self.pulsante_salva.setEnabled(not conflitti)

    # =========================================================================
    # Pulsanti
    # =========================================================================

    def _ripristina(self) -> None:
        self._mostra_tasti(self._predefiniti)

    def _quando_salva(self) -> None:
        self.risultato = self.tasti_correnti()
        self.accept()
