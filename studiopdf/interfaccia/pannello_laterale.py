"""Il pannello a sinistra della pagina, con due sezioni ad albero:

    ▾ Segnati                        <- le frasi evidenziate con un colore che "segna la pagina"
        p. 45  «Il grafo LangGraph…»    (di base il viola): un clic porta alla frase
    ▾ Indice                         <- l'indice scritto dentro il PDF
        ▸ 1. Introduction  ●            un clic porta al capitolo; il pallino viola
        ▾ 2. Foundation Models          dice che lì dentro c'è un segno
            Training Data

Mentre si sfoglia, la voce dell'indice in cui ci si trova resta evidenziata.

Il pannello è una QDockWidget: Qt la mette di lato alla finestra, con un bordo
che si trascina per allargarla. Si mostra e si nasconde dalla finestra principale
(pulsante nella barra in alto, tasto F4).

Il pannello NON cambia pagina da solo: emette il segnale vaiA(pagina, rettangolo)
e la finestra decide cosa fare. Tutti i calcoli stanno in studiopdf/indice.py.
"""

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QDockWidget, QTreeWidget, QTreeWidgetItem, QWidget

from studiopdf.indice import VoceIndice, voce_corrente, voci_con_segni
from studiopdf.interfaccia.gestore_note import titolo_frase
from studiopdf.note import Evidenziatura
from studiopdf.tavolozza import Colore

# I testi che compaiono quando una sezione non ha niente da mostrare.
NESSUN_INDICE = "Questo PDF non ha un indice"
NESSUN_SEGNO = "Nessuna pagina segnata"

# Larghezza iniziale del pannello, in pixel (poi l'utente la cambia trascinando il bordo).
# La imposta la finestra principale con resizeDocks().
LARGHEZZA_INIZIALE = 260

# Il colore del pallino accanto ai capitoli che contengono segni, se nella
# tavolozza non c'è nessun colore che segna la pagina.
COLORE_SEGNO_PREDEFINITO = "#8E4EC6"

# Ogni voce cliccabile si porta dietro DOVE porta: (pagina, rettangolo oppure None).
# Le voci senza destinazione (intestazioni, messaggi, voci senza pagina) non hanno niente.
RUOLO_DESTINAZIONE = Qt.ItemDataRole.UserRole


class PannelloLaterale(QDockWidget):
    # Clic su una voce: (pagina da 1, rettangolo della frase da mostrare oppure None).
    vaiA = Signal(int, object)

    def __init__(self, genitore: QWidget | None = None) -> None:
        super().__init__("Pannello", genitore)
        # Il nome serve a Qt per riconoscere il pannello (es. per ricordarne la posizione).
        self.setObjectName("pannello_laterale")
        # Niente barra del titolo né pulsanti «chiudi» / «stacca»: il pannello sta
        # sempre a sinistra e si mostra/nasconde solo dal pulsante nella barra in alto.
        self.setTitleBarWidget(QWidget(self))
        self.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)

        self.albero = QTreeWidget(self)
        self.albero.setHeaderHidden(True)  # una sola colonna: l'intestazione non serve
        self.albero.setMinimumWidth(120)
        self.setWidget(self.albero)

        # Le due sezioni, sempre presenti, in grassetto.
        self.voce_segnati = self._intestazione("Segnati")
        self.voce_indice = self._intestazione("Indice")

        # L'indice del libro aperto e, per ogni voce, la riga dell'albero che la mostra.
        self._voci: list[VoceIndice] = []
        self._righe_indice: list[QTreeWidgetItem] = []

        # Metodo legato (non una lambda): vedi la lezione sui crash di PySide in uscita.
        self.albero.itemClicked.connect(self._quando_clic)

    # =========================================================================
    # Riempire il pannello
    # =========================================================================

    def mostra_libro(self, voci: list[VoceIndice]) -> None:
        """Un libro nuovo: ricostruisce l'indice e svuota i Segnati (li riempie mostra_segni)."""
        self.svuota()
        self._voci = list(voci)

        if not voci:
            self._messaggio(self.voce_indice, NESSUN_INDICE)
        # Le voci sono in ordine di lettura: il livello dice dentro chi va ognuna.
        # "aperte" = le voci che possono ancora ricevere figli: (livello, riga).
        aperte: list[tuple[int, QTreeWidgetItem]] = []
        for voce in voci:
            while aperte and aperte[-1][0] >= voce.livello:
                aperte.pop()  # quella voce è finita: la nuova è sua "sorella" o di un livello più alto
            genitore = aperte[-1][1] if aperte else self.voce_indice
            riga = QTreeWidgetItem(genitore, [voce.titolo])
            riga.setToolTip(0, voce.titolo)  # i titoli lunghi si leggono passando il mouse
            if voce.pagina is not None:
                riga.setData(0, RUOLO_DESTINAZIONE, (voce.pagina, None))
            self._righe_indice.append(riga)
            aperte.append((voce.livello, riga))

        self._messaggio(self.voce_segnati, NESSUN_SEGNO)
        self.voce_segnati.setExpanded(True)
        self.voce_indice.setExpanded(True)

    def mostra_segni(self, segni: list[Evidenziatura], tavolozza: list[Colore]) -> None:
        """Riempie «Segnati» e mette il pallino viola accanto ai capitoli con un segno.

        segni = le evidenziature da mostrare, già in ordine (vedi indice.segni).
        """
        self._togli_figli(self.voce_segnati)
        colori = {colore.nome: colore.colore for colore in tavolozza}
        for segno in segni:
            testo = f"p. {segno.pagina}  {titolo_frase(segno.testo)}"
            riga = QTreeWidgetItem(self.voce_segnati, [testo])
            riga.setToolTip(0, segno.testo)
            riga.setIcon(0, _pallino(colori.get(segno.colore, COLORE_SEGNO_PREDEFINITO)))
            rett = segno.rettangoli[0] if segno.rettangoli else None
            riga.setData(0, RUOLO_DESTINAZIONE, (segno.pagina, rett))
        if not segni:
            self._messaggio(self.voce_segnati, NESSUN_SEGNO)
        self.voce_segnati.setExpanded(True)

        # Il pallino accanto alle voci dell'indice che contengono una pagina segnata.
        colore_segno = next((c.colore for c in tavolozza if c.segna_pagina), COLORE_SEGNO_PREDEFINITO)
        con_segni = voci_con_segni(self._voci, {segno.pagina for segno in segni})
        for posizione, riga in enumerate(self._righe_indice):
            riga.setIcon(0, _pallino(colore_segno) if posizione in con_segni else QIcon())

    def segui_pagina(self, pagina: int) -> None:
        """Evidenzia la voce dell'indice in cui si trova la pagina (senza cambiare pagina)."""
        posizione = voce_corrente(self._voci, pagina)
        if posizione is None:
            self.albero.setCurrentItem(None)
            return
        riga = self._righe_indice[posizione]
        # setCurrentItem non emette itemClicked, quindi non si torna a cambiare pagina:
        # il pannello segue la pagina, non la comanda.
        self.albero.setCurrentItem(riga)
        self.albero.scrollToItem(riga)  # se serve apre i rami e scorre fino alla voce

    def svuota(self) -> None:
        """Nessun libro aperto: le due sezioni restano, vuote."""
        self._togli_figli(self.voce_segnati)
        self._togli_figli(self.voce_indice)
        self._voci = []
        self._righe_indice = []

    # =========================================================================
    # Clic
    # =========================================================================

    def _quando_clic(self, riga: QTreeWidgetItem, _colonna: int) -> None:
        destinazione = riga.data(0, RUOLO_DESTINAZIONE)
        if destinazione is None:
            return  # intestazione, messaggio o voce senza pagina: non porta da nessuna parte
        pagina, rett = destinazione
        self.vaiA.emit(pagina, rett)

    # =========================================================================
    # Funzioni di aiuto
    # =========================================================================

    def _intestazione(self, testo: str) -> QTreeWidgetItem:
        riga = QTreeWidgetItem(self.albero, [testo])
        carattere = riga.font(0)
        carattere.setBold(True)
        riga.setFont(0, carattere)
        riga.setFlags(Qt.ItemFlag.ItemIsEnabled)  # si apre e si chiude, ma non si seleziona
        return riga

    def _messaggio(self, sezione: QTreeWidgetItem, testo: str) -> None:
        """Una riga grigia, non cliccabile, es. «Nessuna pagina segnata»."""
        riga = QTreeWidgetItem(sezione, [testo])
        riga.setFlags(Qt.ItemFlag.NoItemFlags)  # spenta: Qt la mostra in grigio
        carattere = riga.font(0)
        carattere.setItalic(True)
        riga.setFont(0, carattere)

    def _togli_figli(self, sezione: QTreeWidgetItem) -> None:
        sezione.takeChildren()  # li stacca dall'albero: senza più riferimenti, Python li libera


def _pallino(codice_colore: str) -> QIcon:
    """Un pallino pieno del colore indicato, da mettere accanto a una voce."""
    lato = 16
    immagine = QPixmap(lato, lato)
    immagine.fill(Qt.GlobalColor.transparent)
    pittore = QPainter(immagine)
    pittore.setRenderHint(QPainter.RenderHint.Antialiasing)
    pittore.setPen(Qt.PenStyle.NoPen)
    pittore.setBrush(QBrush(QColor(codice_colore)))
    pittore.drawEllipse(QRectF(4, 4, 8, 8))  # piccolo, al centro dell'icona
    pittore.end()
    return QIcon(immagine)
