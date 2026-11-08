"""I tipi di dato condivisi da tutto il programma.

Questo modulo contiene solo "forme" di dati, nessuna logica:
chi vuole sapere com'è fatta una nota guarda qui.

Una @dataclass è una classe che serve solo a tenere dei valori:
Python scrive da solo il costruttore, il confronto (==) e la stampa.
"""

from dataclasses import dataclass

# Un rettangolo sulla pagina, in punti PDF (1 punto = 1/72 di pollice).
# L'ordine è: (x0, y0, x1, y1)
#   x0, y0 = angolo in alto a sinistra
#   x1, y1 = angolo in basso a destra
# Nei PDF (come li espone PyMuPDF) la y cresce andando verso il BASSO.
Rett = tuple[float, float, float, float]


@dataclass
class Segnalibro:
    """Il punto in cui ci si è fermati a leggere. Ce n'è al massimo uno per libro."""

    pagina: int  # da 1
    parola: str
    rett: Rett


@dataclass
class Sottolineatura:
    """Una parola sottolineata con la propria spiegazione."""

    id: str  # 8 caratteri esadecimali, es. "a3f9c210"
    pagina: int
    parola: str
    rett: Rett
    spiegazione: str


@dataclass
class Pallino:
    """Un pallino colorato nel margine, con una nota."""

    id: str
    pagina: int
    y: float  # altezza della riga accanto a cui sta, in punti PDF
    lato: str  # "sx" (margine sinistro) oppure "dx" (margine destro)
    colore: str  # il NOME del colore nella tavolozza, es. "rosso"
    testo: str


# Una nota è o una sottolineatura o un pallino.
# Il simbolo | si legge "oppure".
Nota = Sottolineatura | Pallino
