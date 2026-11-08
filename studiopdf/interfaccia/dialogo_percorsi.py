"""La finestra «Percorsi»: da quale cartella prendere i libri."""

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


def chiedi_cartella_libri(genitore: QWidget | None, attuale: str) -> str | None:
    """Mostra la finestra e restituisce la cartella scelta (None se si annulla)."""
    dialogo = DialogoPercorsi(genitore, attuale)
    dialogo.exec()
    return dialogo.risultato


class DialogoPercorsi(QDialog):
    def __init__(self, genitore: QWidget | None, cartella_libri: str) -> None:
        super().__init__(genitore)
        self.setWindowTitle("Percorsi")
        self.resize(520, 140)
        self.risultato: str | None = None  # resta None se si annulla

        spiegazione = QLabel("Cartella dei libri — «Apri…» parte da qui:")

        # Riga: [campo con il percorso] [Sfoglia…]
        self.campo_cartella = QLineEdit(cartella_libri)
        self.campo_cartella.setPlaceholderText("vuoto = cartella predefinita di Windows")
        pulsante_sfoglia = QPushButton("Sfoglia…")
        pulsante_sfoglia.clicked.connect(self._sfoglia)
        riga_cartella = QHBoxLayout()
        riga_cartella.addWidget(self.campo_cartella)
        riga_cartella.addWidget(pulsante_sfoglia)

        # Riga dei pulsanti in basso a destra.
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
        colonna.addWidget(spiegazione)
        colonna.addLayout(riga_cartella)
        colonna.addStretch()
        colonna.addLayout(riga_pulsanti)

    def _sfoglia(self) -> None:
        """Finestra di Windows per scegliere una cartella."""
        cartella = QFileDialog.getExistingDirectory(self, "Cartella dei libri", self.campo_cartella.text())
        if cartella:  # "" = annullato
            self.campo_cartella.setText(cartella)

    def _quando_salva(self) -> None:
        self.risultato = self.campo_cartella.text().strip()
        self.accept()
