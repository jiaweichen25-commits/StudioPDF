"""La vista che mostra UNA pagina del PDF.

L'idea chiave di questo modulo
------------------------------
Qt disegna tutto dentro una "scena" (QGraphicsScene) che la "vista"
(QGraphicsView) mostra sullo schermo. Qui facciamo in modo che:

    coordinate della scena  ==  coordinate del PDF (in punti)

e che lo zoom sia SOLO una trasformazione della vista (un ingrandimento).

Vantaggi:
- sottolineature e pallini si disegnano usando direttamente le coordinate
  salvate nelle note, senza conti;
- quando si clicca, mapToScene() restituisce già coordinate PDF;
- cambiando zoom, tutto resta allineato da solo.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QPixmap, QTransform, QWheelEvent
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from studiopdf.documento import Documento

# Spazio (in pixel) lasciato ai lati della pagina con "adatta alla larghezza".
MARGINE_VISTA = 20

# Colore dello sfondo intorno alla pagina.
COLORE_SFONDO = QColor("#3A3A3A")


class VistaPagina(QGraphicsView):
    """Mostra una pagina; più avanti disegnerà anche le note e capirà i clic."""

    # Segnale emesso con Ctrl+rotellina: +1 = ingrandisci, -1 = rimpicciolisci.
    # (Un "segnale" Qt è un avviso a cui altri oggetti possono collegarsi.)
    zoomRichiesto = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(COLORE_SFONDO)

    # --- Mostrare una pagina ------------------------------------------------------

    def mostra_pagina(self, documento: Documento, pagina: int, zoom: float) -> None:
        """Disegna la pagina con lo zoom indicato (1 = 1 pixel per punto PDF)."""
        scena = self.scene()
        scena.clear()

        # Su schermi ad alta densità (es. 150%) un "pixel logico" contiene più
        # pixel reali: chiediamo a PyMuPDF un'immagine più grande, così è nitida.
        densita = self.devicePixelRatioF()
        immagine = QImage.fromData(documento.immagine_pagina(pagina, zoom * densita), "PNG")
        pixmap = QPixmap.fromImage(immagine)
        pixmap.setDevicePixelRatio(densita)

        # L'immagine è grande "zoom" volte la pagina: la rimpiccioliamo nella
        # scena di 1/zoom, così nella scena misura esattamente come in punti PDF...
        elemento_pagina = scena.addPixmap(pixmap)
        elemento_pagina.setScale(1 / zoom)

        # ...e poi è la VISTA a ingrandire tutto di "zoom".
        self.setTransform(QTransform.fromScale(zoom, zoom))

        larghezza, altezza = documento.dimensione_pagina(pagina)
        self.setSceneRect(0, 0, larghezza, altezza)

        # Pagina nuova: si riparte dall'alto.
        self.verticalScrollBar().setValue(self.verticalScrollBar().minimum())

    def zoom_larghezza(self, documento: Documento, pagina: int) -> float:
        """Lo zoom con cui la pagina riempie la larghezza della vista."""
        larghezza_pagina, _ = documento.dimensione_pagina(pagina)
        return (self.viewport().width() - MARGINE_VISTA) / larghezza_pagina

    # --- Rotellina del mouse --------------------------------------------------------

    def wheelEvent(self, evento: QWheelEvent) -> None:
        """Ctrl+rotellina = zoom; rotellina da sola = scorrimento normale."""
        if evento.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoomRichiesto.emit(+1 if evento.angleDelta().y() > 0 else -1)
            evento.accept()
        else:
            super().wheelEvent(evento)
