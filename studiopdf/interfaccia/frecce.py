"""Le frecce ‹ e › ai lati della pagina, per sfogliare con il mouse.

Stanno a metà altezza, sul bordo sinistro (pagina precedente) e destro
(pagina successiva), e compaiono solo quando il mouse arriva proprio sul
bordo. Sono strette apposta: così non coprono il margine della pagina,
dove si clicca per mettere i pallini.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QWidget

# Dimensioni della freccia, in pixel.
LARGHEZZA = 22
ALTEZZA = 88

# Distanza dal bordo della vista.
DISTANZA_DAL_BORDO = 1

# Quanto vicino al bordo (in pixel) deve arrivare il mouse perché la freccia compaia.
# Poco: il margine della pagina, dove si mettono i pallini, deve restare libero.
ZONA_SENSIBILE = 24

STILE = """
QToolButton {
    background: rgba(0, 0, 0, 90);
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 20pt;
}
QToolButton:hover   { background: rgba(0, 0, 0, 160); }
QToolButton:pressed { background: rgba(0, 0, 0, 200); }
"""


class FrecciaLaterale(QToolButton):
    """Un pulsante a forma di freccia, inizialmente nascosto."""

    def __init__(self, simbolo: str, descrizione: str, genitore: QWidget) -> None:
        super().__init__(genitore)
        self.setText(simbolo)
        self.setToolTip(descrizione)
        self.setStyleSheet(STILE)
        self.setFixedSize(LARGHEZZA, ALTEZZA)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # non "ruba" i tasti freccia della tastiera
        self.hide()
