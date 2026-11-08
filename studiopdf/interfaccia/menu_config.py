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
from PySide6.QtWidgets import QMenu, QToolButton, QWidget


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

    def enterEvent(self, evento) -> None:
        """Il mouse è arrivato sopra il pulsante: apriamo il menu.

        QTimer.singleShot(0, ...) apre il menu "appena possibile", cioè dopo
        che Qt ha finito di gestire questo evento (aprirlo subito, da dentro
        l'evento, può dare problemi).
        """
        super().enterEvent(evento)
        if not self.menu().isVisible():
            QTimer.singleShot(0, self.showMenu)
