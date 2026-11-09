"""La finestrella (pop-up) per leggere, scrivere, modificare o eliminare una nota.

Tastiera: il tasto «salva» (predefinito Invio, si cambia in ⚙ Config → Keybinding)
salva la nota senza dover cliccare «Salva»; con Shift+Invio si va a capo.
"""

from collections.abc import Sequence
from typing import Literal

from PySide6.QtCore import QEvent, QKeyCombination, QObject, Qt
from PySide6.QtGui import QFont, QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from studiopdf.impostazioni import TASTI_SALVA_NOTA

# Il colore della scritta-promemoria in basso (grigio: è solo un aiuto).
COLORE_PROMEMORIA = "#8A8A8A"

# Cosa ha deciso l'utente:
#   ("salva", "testo scritto")   -> salvare questo testo
#   ("elimina", "")              -> eliminare la nota
#   None                         -> ha annullato (o chiuso la finestrella)
RisultatoPopup = tuple[Literal["salva", "elimina"], str] | None


def crea_domanda_conferma(genitore: QWidget | None, titolo: str, testo: str) -> QMessageBox:
    """Una domanda Sì/No in cui il pulsante già selezionato è «No».

    Così premere Invio per sbaglio NON elimina niente.
    """
    domanda = QMessageBox(QMessageBox.Icon.Question, titolo, testo, parent=genitore)
    domanda.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    domanda.setDefaultButton(QMessageBox.StandardButton.No)
    return domanda


def chiedi_conferma(genitore: QWidget | None, titolo: str, testo: str) -> bool:
    """Mostra la domanda e restituisce True solo se l'utente sceglie «Sì»."""
    return crea_domanda_conferma(genitore, titolo, testo).exec() == QMessageBox.StandardButton.Yes


def chiedi_nota(
    genitore: QWidget | None,
    titolo: str,
    testo: str = "",
    eliminabile: bool = False,
    tasti_salva: Sequence[str] = TASTI_SALVA_NOTA,
) -> RisultatoPopup:
    """Mostra il pop-up, aspetta che l'utente scelga e restituisce la sua scelta.

    tasti_salva = i tasti che salvano la nota (stringhe come "Return" o "Ctrl+S").
    """
    popup = FinestraNota(genitore, titolo, testo, eliminabile, tasti_salva)
    popup.exec()  # exec() blocca qui finché il pop-up non viene chiuso
    return popup.risultato


def nome_tasto(tasto: str) -> str:
    """Il nome di un tasto come lo legge una persona: "Ctrl+Return" -> "Ctrl+Invio".

    Qt chiama "Return" l'Invio grande ed "Enter" quello del tastierino:
    per l'utente sono entrambi semplicemente "Invio".
    """
    testo = QKeySequence(tasto).toString()  # forma "standard", es. "Ctrl+Return"
    return testo.replace("Return", "Invio").replace("Enter", "Invio")


def promemoria_tasti(tasti_salva: Sequence[str]) -> str:
    """La scritta-promemoria del pop-up, es. "Invio = salva · Shift+Invio = a capo"."""
    # dict.fromkeys toglie i doppioni tenendo l'ordine ("Return" ed "Enter" sono entrambi "Invio").
    nomi = list(dict.fromkeys(nome_tasto(tasto) for tasto in tasti_salva if tasto.strip()))
    if not nomi:
        return "Invio = a capo"  # nessun tasto per salvare: si salva solo con il pulsante

    # Se Invio da solo salva, per andare a capo serve Shift+Invio; altrimenti basta Invio.
    a_capo = "Shift+Invio" if "Invio" in nomi else "Invio"
    return f"{' o '.join(nomi)} = salva · {a_capo} = a capo"


class FinestraNota(QDialog):
    """Il pop-up vero e proprio: un titolo, un'area di testo e tre pulsanti."""

    def __init__(
        self,
        genitore: QWidget | None,
        titolo: str,
        testo: str = "",
        eliminabile: bool = False,
        tasti_salva: Sequence[str] = TASTI_SALVA_NOTA,
    ) -> None:
        super().__init__(genitore)
        self.setWindowTitle("Nota")
        self.resize(380, 240)
        self.risultato: RisultatoPopup = None  # resta None se si annulla

        # I tasti che salvano la nota, già convertiti nel formato di Qt
        # (le caselle vuote "" non contano).
        self._tasti_salva = [QKeySequence(tasto) for tasto in tasti_salva if tasto.strip()]

        # --- Titolo (es. «monotona» oppure ● da ripassare) ---
        etichetta = QLabel(titolo)
        carattere = QFont(etichetta.font())
        carattere.setBold(True)
        carattere.setPointSizeF(carattere.pointSizeF() * 1.2)
        etichetta.setFont(carattere)

        # --- Area di testo ---
        self.area_testo = QPlainTextEdit(testo)
        self.area_testo.setPlaceholderText("Scrivi qui la tua nota…")
        # Un "filtro di eventi": ogni tasto premuto nell'area di testo passa PRIMA
        # da eventFilter() qui sotto, che può fermarlo (es. Invio = salva).
        self.area_testo.installEventFilter(self)

        # --- Promemoria dei tasti (piccolo e grigio, in basso a sinistra) ---
        self.etichetta_tasti = QLabel(promemoria_tasti(tasti_salva))
        self.etichetta_tasti.setStyleSheet(f"color: {COLORE_PROMEMORIA};")

        # --- Pulsanti ---
        self.pulsante_elimina = QPushButton("Elimina")
        self.pulsante_annulla = QPushButton("Annulla")
        self.pulsante_salva = QPushButton("Salva")
        self.pulsante_salva.setDefault(True)
        self.pulsante_elimina.setVisible(eliminabile)  # si elimina solo una nota che esiste già

        self.pulsante_salva.clicked.connect(self._quando_salva)
        self.pulsante_elimina.clicked.connect(self._quando_elimina)
        self.pulsante_annulla.clicked.connect(self.reject)  # reject = chiudi senza fare niente
        self.area_testo.textChanged.connect(self._aggiorna_pulsante_salva)

        # --- Disposizione: titolo, testo, e sotto la riga dei pulsanti ---
        riga_pulsanti = QHBoxLayout()
        riga_pulsanti.addWidget(self.pulsante_elimina)
        riga_pulsanti.addWidget(self.etichetta_tasti)
        riga_pulsanti.addStretch()  # spazio elastico: spinge gli altri due a destra
        riga_pulsanti.addWidget(self.pulsante_annulla)
        riga_pulsanti.addWidget(self.pulsante_salva)

        colonna = QVBoxLayout(self)
        colonna.addWidget(etichetta)
        colonna.addWidget(self.area_testo)
        colonna.addLayout(riga_pulsanti)

        self._aggiorna_pulsante_salva()
        self.area_testo.setFocus()

    # =========================================================================
    # Tastiera
    # =========================================================================

    def eventFilter(self, oggetto: QObject, evento: QEvent) -> bool:
        """Riceve i tasti premuti nell'area di testo prima che li scriva.

        Restituire True vuol dire "questo tasto l'ho gestito io": l'area di testo
        non lo riceve (quindi, per esempio, Invio non aggiunge una riga vuota).
        """
        if oggetto is self.area_testo and evento.type() == QEvent.Type.KeyPress and self._e_tasto_salva(evento):
            if self.pulsante_salva.isEnabled():  # una nota vuota non si salva
                self._quando_salva()
            return True
        return super().eventFilter(oggetto, evento)

    def _e_tasto_salva(self, evento: QKeyEvent) -> bool:
        """Il tasto premuto (con Ctrl, Shift...) è uno di quelli che salvano?"""
        # L'Invio del tastierino arriva con in più il modificatore "tastierino":
        # lo togliamo, altrimenti non corrisponderebbe mai a "Enter".
        modificatori = evento.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        premuto = QKeySequence(QKeyCombination(modificatori, Qt.Key(evento.key())))
        return premuto in self._tasti_salva

    # =========================================================================
    # Pulsanti
    # =========================================================================

    def _aggiorna_pulsante_salva(self) -> None:
        """Non si può salvare una nota vuota (o fatta solo di spazi)."""
        self.pulsante_salva.setEnabled(bool(self.area_testo.toPlainText().strip()))

    def _quando_salva(self) -> None:
        self.risultato = ("salva", self.area_testo.toPlainText().strip())
        self.accept()  # accept = chiudi il pop-up

    def _quando_elimina(self) -> None:
        if not self.conferma_eliminazione():
            return  # ci ha ripensato: il pop-up resta aperto
        self.risultato = ("elimina", "")
        self.accept()

    def conferma_eliminazione(self) -> bool:
        """Chiede "sei sicuro?" prima di eliminare. True = sì."""
        return chiedi_conferma(self, "Elimina nota", "Eliminare questa nota?\nL'operazione non si può annullare.")
