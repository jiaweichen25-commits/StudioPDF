"""La vista che mostra UNA pagina del PDF, con sopra le note, e capisce i clic.

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

Cosa NON fa questa vista: non salva e non decide niente. Quando l'utente
clicca qualcosa, emette un segnale; è gestore_note.py a decidere cosa fare.
"""

from PySide6.QtCore import QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QContextMenuEvent, QImage, QMouseEvent, QPixmap, QTransform, QWheelEvent
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView

from studiopdf.documento import Documento
from studiopdf.interfaccia import disegno
from studiopdf.note import Pallino, Segnalibro, Sottolineatura
from studiopdf.tavolozza import Colore, trova_colore

# Spazio (in pixel) lasciato ai lati della pagina con "adatta alla larghezza".
MARGINE_VISTA = 20

# Colore dello sfondo intorno alla pagina.
COLORE_SFONDO = QColor("#3A3A3A")


class VistaPagina(QGraphicsView):
    # --- Segnali ---
    # Un "segnale" Qt è un avviso a cui altri oggetti possono collegarsi
    # con .connect(funzione). Tra parentesi: il tipo dei dati che porta con sé.

    zoomRichiesto = Signal(int)  # Ctrl+rotellina: +1 ingrandisci, -1 rimpicciolisci
    menuParola = Signal(object, QPoint)  # clic destro su una parola: (Parola, posizione sullo schermo)
    clicNota = Signal(str)  # clic sinistro su una nota: id della nota
    clicMargine = Signal(str, float, QPoint)  # clic nel margine: (lato "sx"/"dx", y in punti PDF, posizione sullo schermo)
    messaggio = Signal(str)  # un breve messaggio per la barra di stato

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(COLORE_SFONDO)

        # Cosa stiamo mostrando (serve per capire i clic).
        self._documento: Documento | None = None
        self._pagina = 0

        # Gli elementi grafici delle note attualmente nella scena.
        self._elementi_note: list[QGraphicsItem] = []

    # =========================================================================
    # Mostrare una pagina
    # =========================================================================

    def mostra_pagina(self, documento: Documento, pagina: int, zoom: float) -> None:
        """Disegna la pagina con lo zoom indicato (1 = 1 pixel per punto PDF)."""
        self._documento = documento
        self._pagina = pagina

        scena = self.scene()
        scena.clear()  # toglie tutto, comprese le note...
        self._elementi_note = []  # ...quindi la lista riparte vuota

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
        # Qualità migliore se Qt deve ridimensionare l'immagine.
        elemento_pagina.setTransformationMode(Qt.TransformationMode.SmoothTransformation)

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

    # =========================================================================
    # Disegnare le note
    # =========================================================================

    def disegna_note(
        self,
        sottolineature: list[Sottolineatura],
        pallini: list[Pallino],
        segnalibro: Segnalibro | None,
        tavolozza: list[Colore],
        documento: Documento,
    ) -> None:
        """Toglie le note disegnate prima e disegna quelle indicate."""
        scena = self.scene()
        for elemento in self._elementi_note:
            scena.removeItem(elemento)

        nuovi: list[QGraphicsItem] = []
        for sottolineatura in sottolineature:
            nuovi += disegno.crea_sottolineatura(sottolineatura)

        posizioni = disegno.posizioni_pallini(pallini, documento)
        for pallino in pallini:
            x, y = posizioni[pallino.id]
            nuovi.append(disegno.crea_pallino(pallino, x, y, trova_colore(tavolozza, pallino.colore)))

        for elemento in nuovi:
            scena.addItem(elemento)
        self._elementi_note = nuovi

    # =========================================================================
    # Clic: la logica (separata dagli eventi, così si può provare nei test)
    # =========================================================================

    def gestisci_clic_destro(self, punto: QPointF, posizione_schermo: QPoint) -> None:
        """Clic destro nel punto (in coordinate PDF): se c'è una parola, chiede il menu."""
        if self._documento is None:
            return
        parola = self._documento.parola_in(self._pagina, punto.x(), punto.y())
        if parola is None:
            self.messaggio.emit("nessuna parola qui")
        else:
            self.menuParola.emit(parola, posizione_schermo)

    def gestisci_clic_sinistro(self, punto: QPointF, posizione_schermo: QPoint) -> bool:
        """Clic sinistro nel punto (in coordinate PDF).

        Restituisce True se il clic è stato "usato" (su una nota o nel margine).
        """
        # 1) Su una nota esistente? Allora si apre quella nota.
        id_nota = self._id_nota_in(punto)
        if id_nota is not None:
            self.clicNota.emit(id_nota)
            return True

        # 2) Nel margine della pagina? Allora si vuole un pallino nuovo.
        if self._documento is None or not self._dentro_la_pagina(punto):
            return False
        lato = self._documento.lato_margine(self._pagina, punto.x())
        if lato is not None:
            self.clicMargine.emit(lato, punto.y(), posizione_schermo)
            return True
        return False

    def _dentro_la_pagina(self, punto: QPointF) -> bool:
        larghezza, altezza = self._documento.dimensione_pagina(self._pagina)
        return 0 <= punto.x() <= larghezza and 0 <= punto.y() <= altezza

    def _id_nota_in(self, punto: QPointF) -> str | None:
        """L'id della nota che si trova nel punto, oppure None."""
        for elemento in self.scene().items(punto):  # dal più in alto al più in basso
            id_nota = elemento.data(disegno.CHIAVE_ID)
            if id_nota:
                return id_nota
        return None

    # =========================================================================
    # Eventi di Qt (mouse): convertono la posizione e chiamano la logica sopra
    # =========================================================================

    def contextMenuEvent(self, evento: QContextMenuEvent) -> None:
        self.gestisci_clic_destro(self.mapToScene(evento.pos()), evento.globalPos())

    def mousePressEvent(self, evento: QMouseEvent) -> None:
        if evento.button() == Qt.MouseButton.LeftButton:
            punto_vista = evento.position().toPoint()
            if self.gestisci_clic_sinistro(self.mapToScene(punto_vista), evento.globalPosition().toPoint()):
                evento.accept()
                return
        super().mousePressEvent(evento)

    def wheelEvent(self, evento: QWheelEvent) -> None:
        """Ctrl+rotellina = zoom; rotellina da sola = scorrimento normale."""
        if evento.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoomRichiesto.emit(+1 if evento.angleDelta().y() > 0 else -1)
            evento.accept()
        else:
            super().wheelEvent(evento)
