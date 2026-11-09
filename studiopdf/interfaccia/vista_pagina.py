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
from PySide6.QtGui import (
    QColor,
    QContextMenuEvent,
    QCursor,
    QImage,
    QMouseEvent,
    QPixmap,
    QResizeEvent,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import QApplication, QGraphicsItem, QGraphicsScene, QGraphicsView

from studiopdf.documento import Documento
from studiopdf.interfaccia import disegno, frecce
from studiopdf.interfaccia.selezione import Selezione
from studiopdf.note import Pallino, Rett, Segnalibro, Sottolineatura
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
    selezioneFatta = Signal(object, QPoint)  # frase selezionata trascinando: (lista di Parola, posizione sullo schermo)
    menuNota = Signal(str, QPoint)  # clic destro su una nota: (id, posizione sullo schermo)
    clicNota = Signal(str)  # DOPPIO clic su una nota: id della nota (per modificarla)
    notaSorvolata = Signal(str, QPoint)  # il mouse è appena arrivato su una nota: (id, posizione sullo schermo)
    notaLasciata = Signal()  # il mouse ha lasciato la nota
    richiestaPaginaPrecedente = Signal()  # clic sulla freccia ‹
    richiestaPaginaSuccessiva = Signal()  # clic sulla freccia ›
    clicMargine = Signal(str, float, QPoint)  # clic nel margine: (lato "sx"/"dx", y in punti PDF, posizione sullo schermo)
    messaggio = Signal(str)  # un breve messaggio per la barra di stato

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(COLORE_SFONDO)
        # Barra di scorrimento verticale sempre presente: così la larghezza utile
        # non cambia quando compare, e "adatta alla larghezza" resta preciso.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # Cosa stiamo mostrando (serve per capire i clic).
        self._documento: Documento | None = None
        self._pagina = 0

        # Gli elementi grafici delle note attualmente nella scena.
        self._elementi_note: list[QGraphicsItem] = []

        # Interruttore "Frecce laterali" del menu Config.
        self.frecce_attive = True

        # La nota su cui si trova il mouse in questo momento (None = nessuna).
        self._nota_sorvolata: str | None = None

        # La frase che si sta selezionando trascinando il mouse (vedi selezione.py).
        self._selezione = Selezione(self.scene())
        # Dove (in pixel della vista) è stato premuto il tasto sinistro...
        self._punto_pressione = QPoint()
        # ...e se da lì il mouse si è spostato abbastanza da essere un vero
        # trascinamento (e non un semplice clic con la mano che trema).
        self._trascinato = False
        # Senza "mouse tracking" Qt segnala i movimenti solo a pulsante premuto:
        # a noi servono sempre, per l'anteprima e per le frecce.
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        # Le frecce laterali (figlie della vista, quindi disegnate sopra la pagina).
        self.freccia_sinistra = frecce.FrecciaLaterale("‹", "Pagina precedente", self)
        self.freccia_destra = frecce.FrecciaLaterale("›", "Pagina successiva", self)
        self.freccia_sinistra.clicked.connect(self.richiestaPaginaPrecedente.emit)
        self.freccia_destra.clicked.connect(self.richiestaPaginaSuccessiva.emit)

    # =========================================================================
    # Mostrare una pagina
    # =========================================================================

    def mostra_pagina(self, documento: Documento, pagina: int, zoom: float) -> None:
        """Disegna la pagina con lo zoom indicato (1 = 1 pixel per punto PDF).

        Se è la STESSA pagina di prima (es. cambio di zoom o di dimensione della
        finestra) resta visibile lo stesso punto; se è una pagina nuova si parte dall'alto.
        """
        stessa_pagina = documento is self._documento and pagina == self._pagina
        # Il punto della pagina che ora sta al centro della vista (in punti PDF).
        centro_visibile = self.mapToScene(self.viewport().rect().center()) if stessa_pagina else None

        self._documento = documento
        self._pagina = pagina
        self._lascia_nota_sorvolata()  # le note stanno per essere ridisegnate

        scena = self.scene()
        scena.clear()  # toglie tutto, comprese le note e l'azzurro della selezione...
        self._elementi_note = []  # ...quindi la lista riparte vuota...
        self._selezione.dimentica()  # ...e una selezione a metà si perde (era della pagina vecchia)

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

        if centro_visibile is not None:
            self.centerOn(centro_visibile)  # stessa pagina: si torna a guardare lo stesso punto
        else:
            self.verticalScrollBar().setValue(self.verticalScrollBar().minimum())  # pagina nuova: dall'alto

        # Pagina cambiata: le frecce disponibili potrebbero essere cambiate
        # (es. arrivati all'ultima pagina, la freccia › non serve più).
        self.aggiorna_frecce(self.viewport().mapFromGlobal(QCursor.pos()))

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
        self._lascia_nota_sorvolata()
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

        if segnalibro is not None:
            nuovi.append(disegno.crea_segnalibro(segnalibro))

        for elemento in nuovi:
            scena.addItem(elemento)
        self._elementi_note = nuovi

    def mostra_rettangolo(self, rett: Rett) -> None:
        """Fa scorrere la vista in modo che il rettangolo (es. una parola) sia al centro."""
        x0, y0, x1, y1 = rett
        self.centerOn((x0 + x1) / 2, (y0 + y1) / 2)

    # =========================================================================
    # Clic: la logica (separata dagli eventi, così si può provare nei test)
    # =========================================================================

    def gestisci_clic_destro(self, punto: QPointF, posizione_schermo: QPoint) -> None:
        """Clic destro nel punto (in coordinate PDF).

        Su una nota -> menu della nota (modifica / elimina).
        Su una parola -> menu della parola (segnalibro).
        """
        if self._documento is None:
            return
        id_nota = self._id_nota_in(punto)
        if id_nota is not None:
            self.menuNota.emit(id_nota, posizione_schermo)
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
        # 1) Su una nota esistente? Il clic singolo non fa niente: per leggere
        #    c'è l'anteprima, per modificare il doppio clic.
        if self._id_nota_in(punto) is not None:
            return True

        # 2) Nel margine della pagina? Allora si vuole un pallino nuovo.
        if self._documento is None or not self._dentro_la_pagina(punto):
            return False
        lato = self._documento.lato_margine(self._pagina, punto.x())
        if lato is not None:
            self.clicMargine.emit(lato, punto.y(), posizione_schermo)
            return True
        return False

    def gestisci_doppio_clic(self, punto: QPointF) -> bool:
        """Doppio clic nel punto (in coordinate PDF): su una nota, la apre per modificarla."""
        id_nota = self._id_nota_in(punto)
        if id_nota is None:
            return False
        self._lascia_nota_sorvolata()  # l'anteprima sparisce, arriva il pop-up
        self.clicNota.emit(id_nota)
        return True

    # =========================================================================
    # Selezionare una frase trascinando il mouse
    # =========================================================================
    #
    # Le tre fasi:
    #   1. tasto sinistro premuto su una parola  -> inizia_selezione
    #   2. mouse spostato con il tasto premuto    -> continua_selezione
    #   3. tasto lasciato                         -> finisci_selezione
    #                                                (emette selezioneFatta)

    def inizia_selezione(self, punto: QPointF, posizione_vista: QPoint) -> None:
        """Tasto sinistro premuto nel punto (coordinate PDF): forse inizia una selezione.

        La selezione parte solo se sotto il mouse c'è una parola.
        """
        self._selezione.annulla()  # una selezione rimasta a metà non serve più
        self._trascinato = False
        if self._documento is None:
            return
        parola = self._documento.parola_in(self._pagina, punto.x(), punto.y())
        if parola is None:
            return
        self._selezione.inizia(self._documento.parole(self._pagina), parola)
        self._punto_pressione = posizione_vista

    def continua_selezione(self, punto: QPointF, posizione_vista: QPoint) -> None:
        """Il mouse si è spostato con il tasto premuto: la selezione arriva fin qui."""
        if not self._selezione.attiva:
            return
        if not self._trascinato:
            # È un vero trascinamento solo se il mouse si è spostato almeno della
            # distanza "standard" di Qt (pochi pixel). manhattanLength = |dx| + |dy|.
            spostamento = (posizione_vista - self._punto_pressione).manhattanLength()
            if spostamento < QApplication.startDragDistance():
                return
            self._trascinato = True
            self._lascia_nota_sorvolata()  # mentre si seleziona, niente anteprime
        # Se qui non c'è una parola (spazio vuoto) la selezione resta all'ultima toccata.
        self._selezione.estendi(self._selezione.parola_in(punto))

    def finisci_selezione(self, posizione_schermo: QPoint) -> None:
        """Tasto lasciato: se si è trascinato, avvisa quali parole sono state selezionate."""
        if self._selezione.attiva and self._trascinato:
            # Chi riceve il segnale (gestore_note.py) mostra il menu e il pop-up
            # PRIMA che emit() ritorni: intanto l'azzurro resta visibile, così
            # si vede quale frase si sta spiegando.
            self.selezioneFatta.emit(self._selezione.parole(), posizione_schermo)
        self._selezione.annulla()
        self._trascinato = False

    # =========================================================================
    # Movimento del mouse: anteprima delle note e frecce laterali
    # =========================================================================

    def gestisci_movimento(self, punto: QPointF, posizione_vista: QPoint, posizione_schermo: QPoint) -> None:
        """Il mouse si è mosso.

        punto             = dove si trova sulla pagina (coordinate PDF)
        posizione_vista   = dove si trova nella vista (pixel), per le frecce
        posizione_schermo = dove si trova sullo schermo, per posizionare l'anteprima
        """
        if self._trascinato:
            return  # si sta selezionando una frase: le anteprime darebbero solo fastidio
        id_nota = self._id_nota_in(punto)
        if id_nota != self._nota_sorvolata:  # avvisiamo solo quando CAMBIA qualcosa
            self._lascia_nota_sorvolata()
            if id_nota is not None:
                self._nota_sorvolata = id_nota
                self.notaSorvolata.emit(id_nota, posizione_schermo)
        self.aggiorna_frecce(posizione_vista)

    def aggiorna_frecce(self, posizione_vista: QPoint) -> None:
        """Mostra la freccia ‹ o › se il mouse è vicino a quel bordo e la pagina esiste."""
        # Spente dal menu Config, oppure mouse fuori dalla pagina (es. sulla barra in alto).
        if not self.frecce_attive or not self.viewport().rect().contains(posizione_vista):
            self.nascondi_frecce()
            return
        vicino_a_sinistra = posizione_vista.x() < frecce.ZONA_SENSIBILE
        vicino_a_destra = posizione_vista.x() > self.viewport().width() - frecce.ZONA_SENSIBILE

        esiste_precedente = self._documento is not None and self._pagina > 1
        esiste_successiva = self._documento is not None and self._pagina < self._documento.numero_pagine

        self.freccia_sinistra.setVisible(vicino_a_sinistra and esiste_precedente)
        self.freccia_destra.setVisible(vicino_a_destra and esiste_successiva)

    def punto_sotto_mouse(self) -> QPointF | None:
        """Dove si trova ora il mouse sulla pagina (coordinate PDF); None se non è sulla pagina."""
        if self._documento is None:
            return None
        posizione = self.viewport().mapFromGlobal(QCursor.pos())
        if not self.viewport().rect().contains(posizione):
            return None
        punto = self.mapToScene(posizione)
        return punto if self._dentro_la_pagina(punto) else None

    def nascondi_frecce(self) -> None:
        self.freccia_sinistra.hide()
        self.freccia_destra.hide()

    def _lascia_nota_sorvolata(self) -> None:
        """Se il mouse era su una nota, avvisa che non lo è più."""
        if self._nota_sorvolata is not None:
            self._nota_sorvolata = None
            self.notaLasciata.emit()

    def _posiziona_frecce(self) -> None:
        """Mette le frecce a metà altezza, sui bordi sinistro e destro dell'area della pagina."""
        area = self.viewport().geometry()  # in coordinate della vista
        y = area.center().y() - frecce.ALTEZZA // 2
        self.freccia_sinistra.move(area.left() + frecce.DISTANZA_DAL_BORDO, y)
        self.freccia_destra.move(area.right() - frecce.DISTANZA_DAL_BORDO - frecce.LARGHEZZA + 1, y)
        self.freccia_sinistra.raise_()  # sopra la pagina
        self.freccia_destra.raise_()

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

    def mouseMoveEvent(self, evento: QMouseEvent) -> None:
        punto_vista = evento.position().toPoint()
        punto = self.mapToScene(punto_vista)
        # buttons() = i tasti tenuti premuti in questo momento.
        if evento.buttons() & Qt.MouseButton.LeftButton:
            self.continua_selezione(punto, punto_vista)
        self.gestisci_movimento(punto, punto_vista, evento.globalPosition().toPoint())
        super().mouseMoveEvent(evento)

    def mouseDoubleClickEvent(self, evento: QMouseEvent) -> None:
        if evento.button() == Qt.MouseButton.LeftButton:
            if self.gestisci_doppio_clic(self.mapToScene(evento.position().toPoint())):
                evento.accept()
                return
        super().mouseDoubleClickEvent(evento)

    def leaveEvent(self, evento) -> None:
        """Il mouse è uscito dalla vista: via anteprima e frecce."""
        self._lascia_nota_sorvolata()
        self.nascondi_frecce()
        super().leaveEvent(evento)

    def resizeEvent(self, evento: QResizeEvent) -> None:
        super().resizeEvent(evento)
        self._posiziona_frecce()

    def contextMenuEvent(self, evento: QContextMenuEvent) -> None:
        self.gestisci_clic_destro(self.mapToScene(evento.pos()), evento.globalPos())

    def mousePressEvent(self, evento: QMouseEvent) -> None:
        if evento.button() == Qt.MouseButton.LeftButton:
            punto_vista = evento.position().toPoint()
            punto = self.mapToScene(punto_vista)
            # Prima si guarda se il clic è su una nota o nel margine...
            if self.gestisci_clic_sinistro(punto, evento.globalPosition().toPoint()):
                evento.accept()
                return
            # ...altrimenti forse sta iniziando la selezione di una frase.
            self.inizia_selezione(punto, punto_vista)
        super().mousePressEvent(evento)

    def mouseReleaseEvent(self, evento: QMouseEvent) -> None:
        if evento.button() == Qt.MouseButton.LeftButton:
            self.finisci_selezione(evento.globalPosition().toPoint())
        super().mouseReleaseEvent(evento)

    def wheelEvent(self, evento: QWheelEvent) -> None:
        """Ctrl+rotellina = zoom; rotellina da sola = scorrimento normale."""
        if evento.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoomRichiesto.emit(+1 if evento.angleDelta().y() > 0 else -1)
            evento.accept()
        else:
            super().wheelEvent(evento)
