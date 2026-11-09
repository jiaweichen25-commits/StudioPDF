"""La frase che l'utente sta selezionando trascinando il mouse.

Cosa fa questo modulo
---------------------
Ricorda la parola da cui è partita la selezione e quella a cui è arrivata,
sa dire quali parole stanno in mezzo (nell'ordine di lettura) e le colora
di azzurro trasparente sulla pagina.

Cosa NON fa: non sa niente del mouse (lo segue vista_pagina.py) e niente
delle note (le crea gestore_note.py). Così resta piccolo e facile da capire.

Come si usa
-----------
    selezione = Selezione(scena)
    selezione.inizia(parole_della_pagina, parola_sotto_il_mouse)
    selezione.estendi(altra_parola)      # mentre si trascina (anche più volte)
    parole = selezione.parole()          # le parole selezionate, in ordine
    selezione.annulla()                  # toglie l'azzurro e ricomincia da zero
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsScene

from studiopdf.documento import Parola, rettangoli_per_riga
from studiopdf.interfaccia import disegno

# Azzurro trasparente, come la selezione del testo in Word o nel browser.
# (rosso, verde, blu, trasparenza da 0 = invisibile a 255 = pieno)
COLORE_SELEZIONE = QColor(62, 99, 221, 70)

# Sotto le sottolineature (LIVELLO_NOTE) ma sopra la pagina (livello 0).
LIVELLO_SELEZIONE = disegno.LIVELLO_NOTE - 0.5


class Selezione:
    def __init__(self, scena: QGraphicsScene) -> None:
        self._scena = scena

        # Tutte le parole della pagina, nell'ordine di lettura. Si leggono UNA
        # volta all'inizio della selezione: chiederle al PDF a ogni movimento
        # del mouse sarebbe lento.
        self._parole_pagina: list[Parola] = []

        # Posizione (nella lista qui sopra) della parola di partenza e di
        # quella di arrivo. None = nessuna selezione in corso.
        self._inizio: int | None = None
        self._fine: int | None = None

        # I rettangoli azzurri attualmente nella scena.
        self._evidenziazioni: list[QGraphicsRectItem] = []

    # =========================================================================
    # Stato
    # =========================================================================

    @property
    def attiva(self) -> bool:
        """C'è una selezione in corso?"""
        return self._inizio is not None

    def parole(self) -> list[Parola]:
        """Le parole selezionate, nell'ordine di lettura (lista vuota se non c'è selezione).

        Non importa se si è trascinato in avanti o all'indietro: si prende
        sempre il tratto dalla parola che viene prima a quella che viene dopo.
        """
        if self._inizio is None or self._fine is None:
            return []
        prima, ultima = sorted((self._inizio, self._fine))
        return self._parole_pagina[prima : ultima + 1]  # +1: anche l'ultima è compresa

    def parola_in(self, punto: QPointF) -> Parola | None:
        """La parola della pagina che si trova nel punto (coordinate PDF), oppure None."""
        for parola in self._parole_pagina:
            x0, y0, x1, y1 = parola.rett
            if x0 <= punto.x() <= x1 and y0 <= punto.y() <= y1:
                return parola
        return None

    # =========================================================================
    # Cambiare la selezione
    # =========================================================================

    def inizia(self, parole_pagina: list[Parola], parola: Parola) -> None:
        """Comincia una selezione nuova dalla parola indicata.

        L'azzurro non compare ancora: potrebbe essere solo un clic.
        Lo fa comparire la prima chiamata a estendi().
        """
        self.annulla()
        self._parole_pagina = parole_pagina
        self._inizio = self._fine = parole_pagina.index(parola)

    def estendi(self, parola: Parola | None) -> None:
        """Sposta la fine della selezione su questa parola e ridisegna l'azzurro.

        Con None (il mouse è su uno spazio vuoto) la fine resta dov'era,
        ma l'azzurro viene comunque disegnato.
        """
        if not self.attiva:
            return
        if parola is not None and parola in self._parole_pagina:
            self._fine = self._parole_pagina.index(parola)
        self._ridisegna()

    def annulla(self) -> None:
        """Toglie l'azzurro dalla pagina e dimentica la selezione."""
        for elemento in self._evidenziazioni:
            self._scena.removeItem(elemento)
        self._ricomincia()

    def dimentica(self) -> None:
        """Come annulla(), ma da usare DOPO che la scena è stata svuotata (scena.clear()).

        In quel caso gli elementi azzurri sono già stati distrutti insieme a tutto
        il resto: provare a toglierli di nuovo farebbe un errore.
        """
        self._ricomincia()

    # =========================================================================
    # Uso interno
    # =========================================================================

    def _ricomincia(self) -> None:
        self._evidenziazioni = []
        self._parole_pagina = []
        self._inizio = self._fine = None

    def _ridisegna(self) -> None:
        """Toglie l'azzurro vecchio e colora le parole selezionate ora (un rettangolo per riga)."""
        for elemento in self._evidenziazioni:
            self._scena.removeItem(elemento)
        self._evidenziazioni = []

        for x0, y0, x1, y1 in rettangoli_per_riga(self.parole()):
            rettangolo = QGraphicsRectItem(QRectF(x0, y0, x1 - x0, y1 - y0))
            rettangolo.setPen(QPen(Qt.PenStyle.NoPen))  # niente bordo
            rettangolo.setBrush(QBrush(COLORE_SELEZIONE))
            rettangolo.setZValue(LIVELLO_SELEZIONE)
            self._scena.addItem(rettangolo)
            self._evidenziazioni.append(rettangolo)
