"""Il pulsante ⚙ Config nella barra in alto, con il suo menu.

Passandoci sopra con il mouse (o cliccandolo) si apre il menu:
    Percorsi…          -> finestra per la cartella dei libri
    Keybinding…        -> finestra per scegliere i tasti
    ─────────
    ☑ Frecce laterali
    ☑ Anteprima delle note

Questo modulo crea solo il pulsante e le voci: cosa succede quando
si sceglie una voce lo decide la finestra principale.
"""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu, QToolButton, QWidget

# Quanto deve restare il mouse sul pulsante prima che il menu si apra (ms):
# così passarci sopra di corsa, andando altrove, non apre niente.
ATTESA_APERTURA_MS = 250


class PulsanteConfig(QToolButton):
    def __init__(self, genitore: QWidget) -> None:
        super().__init__(genitore)
        self.setText("⚙  Config")

        menu = QMenu(self)
        self.azione_percorsi = menu.addAction("Percorsi…")
        self.azione_tasti = menu.addAction("Keybinding…")
        menu.addSeparator()

        # Voci "spuntabili": il segno di spunta dice se l'aiuto è attivo.
        self.azione_frecce = menu.addAction("Frecce laterali")
        self.azione_frecce.setCheckable(True)
        self.azione_anteprima = menu.addAction("Anteprima delle note")
        self.azione_anteprima.setCheckable(True)

        self.setMenu(menu)
        # InstantPopup = il menu si apre subito al clic (senza la freccetta a lato).
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        # Timer per l'apertura "al passaggio del mouse", con un piccolo ritardo.
        self.attesa_apertura = QTimer(self)
        self.attesa_apertura.setSingleShot(True)
        self.attesa_apertura.setInterval(ATTESA_APERTURA_MS)
        self.attesa_apertura.timeout.connect(self._apri_se_ancora_sopra)

        # True se il menu è appena stato chiuso con il mouse ancora sul pulsante:
        # in quel caso NON va riaperto finché il mouse non esce e rientra.
        self._appena_chiuso = False
        menu.aboutToHide.connect(self._quando_menu_si_chiude)

    # --- Eventi del mouse ---

    def enterEvent(self, evento) -> None:
        """Il mouse è arrivato sul pulsante: dopo un attimo si apre il menu."""
        super().enterEvent(evento)
        if self._appena_chiuso or self.menu().isVisible():
            return
        self.attesa_apertura.start()

    def leaveEvent(self, evento) -> None:
        """Il mouse è uscito: niente apertura in sospeso, e la prossima volta si riapre."""
        super().leaveEvent(evento)
        self.attesa_apertura.stop()
        self._appena_chiuso = False

    # --- Funzioni di aiuto ---

    def _apri_se_ancora_sopra(self) -> None:
        if self._mouse_sopra() and not self.menu().isVisible():
            self.showMenu()

    def _quando_menu_si_chiude(self) -> None:
        self._appena_chiuso = self._mouse_sopra()

    def _mouse_sopra(self) -> bool:
        """Il puntatore è sopra il pulsante?"""
        return self.rect().contains(self.mapFromGlobal(QCursor.pos()))
