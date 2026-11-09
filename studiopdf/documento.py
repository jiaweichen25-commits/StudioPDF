"""Tutto ciò che riguarda il file PDF: aprirlo, leggerne le parole, disegnarne le pagine.

Questo modulo è l'UNICO che usa PyMuPDF. Il resto del programma
chiede a lui le informazioni sul PDF e non sa come vengono ottenute.

Regole importanti:
- le pagine si contano da 1, come le vede una persona.
  PyMuPDF invece conta da 0: la conversione avviene solo nel metodo _pagina();
- il PDF NON viene mai modificato: si legge e basta.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from studiopdf.note import Rett


# Quando una pagina non ha testo non si sa dove sia il margine:
# si considera margine il 15% della larghezza a sinistra e a destra.
FASCIA_MARGINE_SENZA_TESTO = 0.15

# Espressione regolare per la punteggiatura all'inizio (^...) o alla fine (...$)
# di una parola. [^\w] significa "qualsiasi carattere che NON sia lettera o cifra".
_PUNTEGGIATURA_AI_BORDI = re.compile(r"^[^\w]+|[^\w]+$")


@dataclass(frozen=True)
class Parola:
    """Una parola della pagina: il suo testo e il rettangolo che occupa.

    frozen=True la rende immutabile: una volta creata non cambia più,
    e due Parola con gli stessi valori risultano uguali (==).
    """

    testo: str  # già pulito dalla punteggiatura
    rett: Rett  # posizione sulla pagina, in punti PDF
    # In quale riga del PDF si trova: (numero del blocco, numero della riga nel blocco),
    # come li numera PyMuPDF. Serve solo a capire se due parole stanno sulla stessa
    # riga (vedi rettangoli_per_riga). Ha un valore di partenza così nei test si può
    # scrivere semplicemente Parola("ciao", (0, 0, 1, 1)).
    riga: tuple[int, int] = (0, 0)


class ErroreDocumento(Exception):
    """Il PDF non si può aprire (rotto, non è un PDF, protetto da password...)."""


def pulisci(testo: str) -> str:
    """Toglie la punteggiatura all'inizio e alla fine di una parola.

    Esempi: "monotona," -> "monotona", "(serie)" -> "serie".
    L'apostrofo in mezzo resta: "l'arco" -> "l'arco".
    """
    return _PUNTEGGIATURA_AI_BORDI.sub("", testo)


def testo_frase(parole: list[Parola]) -> str:
    """Il testo di una frase: le sue parole separate da uno spazio.

    Esempio: [Parola("Una"), Parola("serie")] -> "Una serie"
    """
    return " ".join(parola.testo for parola in parole)


def rettangoli_per_riga(parole: list[Parola]) -> list[Rett]:
    """Un rettangolo per ogni riga della frase, nell'ordine di lettura.

    Le parole devono essere già in ordine di lettura (come le dà Documento.parole).
    Le parole di fila che stanno sulla stessa riga vengono "fuse" in un unico
    rettangolo che le contiene tutte: così sotto la frase si disegna una linea
    continua, senza buchi tra una parola e l'altra.
    """
    rettangoli: list[Rett] = []
    riga_precedente = None
    for parola in parole:
        x0, y0, x1, y1 = parola.rett
        if rettangoli and parola.riga == riga_precedente:
            # Stessa riga della parola prima: si allarga l'ultimo rettangolo.
            a0, b0, a1, b1 = rettangoli[-1]
            rettangoli[-1] = (min(a0, x0), min(b0, y0), max(a1, x1), max(b1, y1))
        else:
            # Riga nuova: si comincia un rettangolo nuovo.
            rettangoli.append((x0, y0, x1, y1))
        riga_precedente = parola.riga
    return rettangoli


class Documento:
    """Un PDF aperto in sola lettura."""

    def __init__(self, percorso: str | Path) -> None:
        self.percorso = Path(percorso)

        # Apertura: qualunque problema diventa un ErroreDocumento con un
        # messaggio comprensibile, così chi usa questa classe deve gestire
        # un solo tipo di errore.
        try:
            self._pdf = pymupdf.open(self.percorso)
        except Exception as errore:
            raise ErroreDocumento(f"Impossibile aprire «{self.percorso.name}»: {errore}") from errore

        if self._pdf.needs_pass:
            self._pdf.close()
            raise ErroreDocumento(f"«{self.percorso.name}» è protetto da password.")

    # --- Informazioni generali ----------------------------------------------

    @property
    def numero_pagine(self) -> int:
        return self._pdf.page_count

    def dimensione_pagina(self, pagina: int) -> tuple[float, float]:
        """Restituisce (larghezza, altezza) della pagina, in punti PDF."""
        rettangolo = self._pagina(pagina).rect
        return (rettangolo.width, rettangolo.height)

    def immagine_pagina(self, pagina: int, zoom: float) -> bytes:
        """Disegna la pagina e la restituisce come immagine PNG.

        zoom = 1 significa 1 pixel per punto PDF; zoom = 2 è il doppio, e così via.
        Si restituiscono byte PNG (e non un oggetto grafico) così questo
        modulo non dipende dalla libreria dell'interfaccia.
        """
        ingrandimento = pymupdf.Matrix(zoom, zoom)
        return self._pagina(pagina).get_pixmap(matrix=ingrandimento).tobytes("png")

    # --- Parole ----------------------------------------------------------------

    def parole(self, pagina: int) -> list[Parola]:
        """Tutte le parole della pagina, nell'ordine di lettura."""
        pagina_pdf = self._pagina(pagina)
        risultato = []
        # get_text("words") restituisce tuple: (x0, y0, x1, y1, testo, blocco, riga, n_parola)
        for x0, y0, x1, y1, testo, blocco, riga, _ in pagina_pdf.get_text("words"):
            testo_pulito = pulisci(testo)
            if not testo_pulito:  # una "parola" fatta solo di punteggiatura si scarta
                continue

            # Pagine ruotate (/Rotate 90, tipico per le tabelle in orizzontale):
            # PyMuPDF dà le coordinate della pagina "non ruotata", mentre l'immagine
            # e le dimensioni sono quelle ruotate. rotation_matrix converte dalle
            # une alle altre; normalize() rimette in ordine gli angoli del rettangolo.
            rettangolo = pymupdf.Rect(x0, y0, x1, y1) * pagina_pdf.rotation_matrix
            rettangolo.normalize()
            risultato.append(Parola(testo_pulito, tuple(rettangolo), (blocco, riga)))
        return risultato

    def parola_in(self, pagina: int, x: float, y: float) -> Parola | None:
        """La parola che si trova nel punto (x, y), oppure None se lì non c'è testo."""
        for parola in self.parole(pagina):
            x0, y0, x1, y1 = parola.rett
            if x0 <= x <= x1 and y0 <= y <= y1:
                return parola
        return None

    # --- Margini ---------------------------------------------------------------

    def limiti_testo(self, pagina: int) -> tuple[float, float] | None:
        """(x_min, x_max): dove inizia e dove finisce il testo in orizzontale.

        Restituisce None se la pagina non contiene parole.
        """
        parole = self.parole(pagina)
        if not parole:
            return None
        x_min = min(parola.rett[0] for parola in parole)
        x_max = max(parola.rett[2] for parola in parole)
        return (x_min, x_max)

    def lato_margine(self, pagina: int, x: float) -> str | None:
        """Dice se la coordinata x cade nel margine sinistro ("sx"), destro ("dx") o in nessuno dei due (None)."""
        inizio, fine = self._fasce_margine(pagina)
        if x < inizio:
            return "sx"
        if x > fine:
            return "dx"
        return None

    def centro_margine(self, pagina: int, lato: str) -> float:
        """La x a metà del margine indicato: è lì che si disegnano i pallini."""
        larghezza, _ = self.dimensione_pagina(pagina)
        inizio, fine = self._fasce_margine(pagina)
        if lato == "sx":
            return inizio / 2  # a metà tra il bordo (0) e l'inizio del testo
        return (fine + larghezza) / 2  # a metà tra la fine del testo e il bordo destro

    # --- Chiusura -------------------------------------------------------------

    def chiudi(self) -> None:
        self._pdf.close()

    # --- Metodi interni (il trattino basso iniziale vuol dire "uso interno") ---

    def _pagina(self, pagina: int) -> pymupdf.Page:
        """Converte il numero di pagina "umano" (da 1) in quello di PyMuPDF (da 0)."""
        if not 1 <= pagina <= self.numero_pagine:
            raise ValueError(f"La pagina {pagina} non esiste (il PDF ha {self.numero_pagine} pagine).")
        return self._pdf[pagina - 1]

    def _fasce_margine(self, pagina: int) -> tuple[float, float]:
        """Restituisce (inizio_testo, fine_testo): prima c'è il margine sinistro, dopo quello destro."""
        limiti = self.limiti_testo(pagina)
        if limiti is not None:
            return limiti
        # Pagina senza testo: si usano fasce fisse in proporzione alla larghezza.
        larghezza, _ = self.dimensione_pagina(pagina)
        fascia = larghezza * FASCIA_MARGINE_SENZA_TESTO
        return (fascia, larghezza - fascia)
