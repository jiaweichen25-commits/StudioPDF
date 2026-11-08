"""La finestrella (pop-up) per leggere, scrivere, modificare o eliminare una nota."""

from typing import Literal

from PySide6.QtGui import QFont
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

# Cosa ha deciso l'utente:
#   ("salva", "testo scritto")   -> salvare questo testo
#   ("elimina", "")              -> eliminare la nota
#   None                         -> ha annullato (o chiuso la finestrella)
RisultatoPopup = tuple[Literal["salva", "elimina"], str] | None


def chiedi_nota(genitore: QWidget | None, titolo: str, testo: str = "", eliminabile: bool = False) -> RisultatoPopup:
    """Mostra il pop-up, aspetta che l'utente scelga e restituisce la sua scelta."""
    popup = FinestraNota(genitore, titolo, testo, eliminabile)
    popup.exec()  # exec() blocca qui finché il pop-up non viene chiuso
    return popup.risultato


class FinestraNota(QDialog):
    """Il pop-up vero e proprio: un titolo, un'area di testo e tre pulsanti."""

    def __init__(self, genitore: QWidget | None, titolo: str, testo: str = "", eliminabile: bool = False) -> None:
        super().__init__(genitore)
        self.setWindowTitle("Nota")
        self.resize(380, 240)
        self.risultato: RisultatoPopup = None  # resta None se si annulla

        # --- Titolo (es. «monotona» oppure ● da ripassare) ---
        etichetta = QLabel(titolo)
        carattere = QFont(etichetta.font())
        carattere.setBold(True)
        carattere.setPointSizeF(carattere.pointSizeF() * 1.2)
        etichetta.setFont(carattere)

        # --- Area di testo ---
        self.area_testo = QPlainTextEdit(testo)
        self.area_testo.setPlaceholderText("Scrivi qui la tua nota…")

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
        riga_pulsanti.addStretch()  # spazio elastico: spinge gli altri due a destra
        riga_pulsanti.addWidget(self.pulsante_annulla)
        riga_pulsanti.addWidget(self.pulsante_salva)

        colonna = QVBoxLayout(self)
        colonna.addWidget(etichetta)
        colonna.addWidget(self.area_testo)
        colonna.addLayout(riga_pulsanti)

        self._aggiorna_pulsante_salva()
        self.area_testo.setFocus()

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
        risposta = QMessageBox.question(
            self, "Elimina nota", "Eliminare questa nota?\nL'operazione non si può annullare."
        )
        return risposta == QMessageBox.StandardButton.Yes
