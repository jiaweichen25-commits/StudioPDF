"""La finestra «Percorsi»: da quale cartella prendere i libri e dove salvare le note."""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Rosso scuro per il messaggio di errore (come nella finestra Keybinding).
COLORE_ERRORE = "#B42318"


def chiedi_percorsi(genitore: QWidget | None, cartella_libri: str, cartella_note: str) -> tuple[str, str] | None:
    """Mostra la finestra e restituisce (cartella dei libri, cartella delle note), o None se si annulla."""
    dialogo = DialogoPercorsi(genitore, cartella_libri, cartella_note)
    dialogo.exec()
    return dialogo.risultato


class DialogoPercorsi(QDialog):
    def __init__(self, genitore: QWidget | None, cartella_libri: str, cartella_note: str = "") -> None:
        super().__init__(genitore)
        self.setWindowTitle("Percorsi")
        self.resize(560, 220)
        self.risultato: tuple[str, str] | None = None  # resta None se si annulla

        # --- Cartella dei libri: [campo] [Sfoglia…] ---
        self.campo_cartella = QLineEdit(cartella_libri)
        self.campo_cartella.setPlaceholderText("vuoto = cartella predefinita di Windows")
        riga_libri = self._riga(self.campo_cartella, self._sfoglia_libri)

        # --- Cartella delle note: [campo] [Sfoglia…] ---
        self.campo_note = QLineEdit(cartella_note)
        self.campo_note.setPlaceholderText("vuoto = accanto a ogni PDF")
        riga_note = self._riga(self.campo_note, self._sfoglia_note)
        self.campo_note.textChanged.connect(self._controlla)

        # Messaggio di errore (vuoto se è tutto a posto).
        self.etichetta_errore = QLabel("")
        self.etichetta_errore.setStyleSheet(f"color: {COLORE_ERRORE};")

        # --- Pulsanti in basso a destra ---
        self.pulsante_annulla = QPushButton("Annulla")
        self.pulsante_salva = QPushButton("Salva")
        self.pulsante_salva.setDefault(True)
        self.pulsante_annulla.clicked.connect(self.reject)
        self.pulsante_salva.clicked.connect(self._quando_salva)
        riga_pulsanti = QHBoxLayout()
        riga_pulsanti.addStretch()
        riga_pulsanti.addWidget(self.pulsante_annulla)
        riga_pulsanti.addWidget(self.pulsante_salva)

        colonna = QVBoxLayout(self)
        colonna.addWidget(QLabel("Cartella dei libri — «Apri…» parte da qui (se non c'è un ultimo libro):"))
        colonna.addLayout(riga_libri)
        colonna.addSpacing(10)
        colonna.addWidget(QLabel("Cartella delle note — dove salvare le note di tutti i libri:"))
        colonna.addLayout(riga_note)
        colonna.addWidget(self.etichetta_errore)
        colonna.addStretch()
        colonna.addLayout(riga_pulsanti)

        self._controlla()

    def _riga(self, campo: QLineEdit, quando_sfoglia) -> QHBoxLayout:
        """Una riga [campo con il percorso] [Sfoglia…]; il pulsante chiama quando_sfoglia.

        Attenzione: al pulsante si collega un METODO della finestra, non una lambda.
        Una lambda che usa "self" terrebbe in vita la finestra fino alla chiusura di
        Python, quando Qt è già smontato: e lì il programma va in crash.
        """
        pulsante = QPushButton("Sfoglia…")
        pulsante.clicked.connect(quando_sfoglia)
        riga = QHBoxLayout()
        riga.addWidget(campo)
        riga.addWidget(pulsante)
        return riga

    def _sfoglia_libri(self) -> None:
        self._sfoglia(self.campo_cartella, "Cartella dei libri")

    def _sfoglia_note(self) -> None:
        self._sfoglia(self.campo_note, "Cartella delle note")

    def _sfoglia(self, campo: QLineEdit, titolo: str) -> None:
        """Finestra di Windows per scegliere una cartella."""
        cartella = QFileDialog.getExistingDirectory(self, titolo, campo.text())
        if cartella:  # "" = annullato
            campo.setText(cartella)

    def _controlla(self) -> None:
        """La cartella delle note deve esistere (oppure essere vuota = accanto al PDF).

        Altrimenti le note non si potrebbero salvare: «Salva» si spegne finché non si sistema.
        """
        testo = self.campo_note.text().strip()
        valida = not testo or Path(testo).is_dir()
        self.etichetta_errore.setText("" if valida else "Questa cartella delle note non esiste.")
        self.pulsante_salva.setEnabled(valida)

    def _quando_salva(self) -> None:
        self.risultato = (self.campo_cartella.text().strip(), self.campo_note.text().strip())
        self.accept()
