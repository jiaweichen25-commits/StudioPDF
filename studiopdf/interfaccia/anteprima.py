"""La schedina di anteprima che compare passando il mouse su una nota.

Funziona come le anteprime dei collegamenti di Wikipedia: una piccola
"carta" con il titolo e il testo della nota, che sparisce appena il
mouse si allontana. Serve solo a LEGGERE: per modificare si fa doppio clic.
"""

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

# Larghezza massima della schedina, in pixel: i testi lunghi vanno a capo.
LARGHEZZA_MASSIMA = 340

# Di quanto spostare la schedina rispetto al puntatore, per non coprirlo.
DISTANZA_DAL_PUNTATORE = QPoint(14, 18)

SUGGERIMENTO = "Doppio clic per modificare · clic destro per eliminare"

# Aspetto, scritto come "foglio di stile" Qt (simile al CSS delle pagine web).
STILE = """
QFrame#schedina {
    background: #FFFFFF;
    border: 1px solid #C8C8C8;
    border-radius: 8px;
}
QLabel#titolo     { color: #1A1A1A; font-weight: bold; font-size: 11pt; }
QLabel#testo      { color: #333333; font-size: 10pt; }
QLabel#suggerimento { color: #8A8A8A; font-size: 8pt; }
"""


class AnteprimaNota(QFrame):
    def __init__(self, genitore: QWidget | None = None) -> None:
        super().__init__(genitore)
        # Qt.ToolTip = finestrella "volante", senza bordi né barra del titolo,
        # che non ruba il fuoco alla finestra principale.
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("schedina")
        self.setStyleSheet(STILE)
        self.setMaximumWidth(LARGHEZZA_MASSIMA)

        self.etichetta_titolo = QLabel()
        self.etichetta_titolo.setObjectName("titolo")
        self.etichetta_titolo.setTextFormat(Qt.TextFormat.RichText)  # il titolo può contenere un pallino colorato

        self.etichetta_testo = QLabel()
        self.etichetta_testo.setObjectName("testo")
        self.etichetta_testo.setTextFormat(Qt.TextFormat.PlainText)  # il testo della nota è mostrato così com'è
        self.etichetta_testo.setWordWrap(True)  # va a capo invece di allargarsi

        suggerimento = QLabel(SUGGERIMENTO)
        suggerimento.setObjectName("suggerimento")

        colonna = QVBoxLayout(self)
        colonna.setContentsMargins(12, 10, 12, 8)
        colonna.setSpacing(6)
        colonna.addWidget(self.etichetta_titolo)
        colonna.addWidget(self.etichetta_testo)
        colonna.addWidget(suggerimento)

    def mostra(self, titolo_html: str, testo: str, posizione_schermo: QPoint) -> None:
        """Mostra la schedina vicino alla posizione indicata (coordinate dello schermo)."""
        self.etichetta_titolo.setText(titolo_html)
        self.etichetta_testo.setText(testo)
        self.adjustSize()  # ricalcola la dimensione in base al nuovo testo
        self.move(self._posizione_dentro_lo_schermo(posizione_schermo))
        self.show()
        self.raise_()  # sopra le altre finestre

    def _posizione_dentro_lo_schermo(self, puntatore: QPoint) -> QPoint:
        """Dove mettere la schedina: in basso a destra del puntatore, ma sempre dentro lo schermo.

        Se a destra (o sotto) non c'è spazio, la schedina passa a sinistra (o sopra) del puntatore.
        """
        schermo = QGuiApplication.screenAt(puntatore) or QGuiApplication.primaryScreen()
        area = schermo.availableGeometry()  # lo schermo senza la barra delle applicazioni
        larghezza, altezza = self.width(), self.height()

        x = puntatore.x() + DISTANZA_DAL_PUNTATORE.x()
        y = puntatore.y() + DISTANZA_DAL_PUNTATORE.y()
        if x + larghezza > area.right():
            x = puntatore.x() - DISTANZA_DAL_PUNTATORE.x() - larghezza
        if y + altezza > area.bottom():
            y = puntatore.y() - DISTANZA_DAL_PUNTATORE.y() - altezza

        # Ultima sicurezza: mai fuori dai bordi.
        x = max(area.left(), min(x, area.right() - larghezza + 1))
        y = max(area.top(), min(y, area.bottom() - altezza + 1))
        return QPoint(x, y)
