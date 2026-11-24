"""Crea gli elementi grafici delle note: sottolineature, evidenziature, segnalibro.

Le funzioni qui CREANO gli elementi ma non li mettono nella scena:
è VistaPagina a farlo, così sa sempre quali elementi sono "note"
e può toglierli quando ridisegna.

Tutte le coordinate sono in punti PDF (vedi vista_pagina.py).
"""

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsRectItem

from studiopdf.note import Evidenziatura, Segnalibro, Sottolineatura
from studiopdf.tavolozza import Colore

# Ogni elemento cliccabile si porta dietro l'id della sua nota,
# salvato con setData(CHIAVE_ID, id). Gli altri elementi non hanno id.
CHIAVE_ID = 0

# Le note che si aprono con un CLIC SINGOLO (e senza anteprima) hanno anche
# setData(CHIAVE_CLIC_SINGOLO, True). Oggi sono le evidenziature.
CHIAVE_CLIC_SINGOLO = 1

# --- Aspetto delle evidenziature ---
TRASPARENZA_EVIDENZIATURA = 85  # da 0 (invisibile) a 255 (pieno): il testo sotto si deve leggere

# --- Aspetto delle sottolineature ---
COLORE_SOTTOLINEATURA = QColor("#3E63DD")
SPESSORE_SOTTOLINEATURA = 2  # in pixel dello schermo (non cambia con lo zoom)
DISTANZA_SOTTOLINEATURA = 1  # punti PDF sotto il bordo inferiore della parola

# Grigio: per un colore tolto dalla tavolozza.
COLORE_SCONOSCIUTO = "#9E9E9E"

# --- Aspetto del segnalibro: un'evidenziazione gialla trasparente ---
COLORE_SEGNALIBRO = QColor(255, 220, 0, 90)  # rosso, verde, blu, trasparenza (0-255)

# Le note stanno sopra la pagina (che ha livello 0).
LIVELLO_NOTE = 2


def crea_sottolineatura(sottolineatura: Sottolineatura) -> list[QGraphicsItem]:
    """Gli elementi grafici di una frase sottolineata.

    Per OGNI riga della frase (cioè per ogni rettangolo) si creano due elementi:

    1. la LINEA visibile sotto la riga;
    2. un RETTANGOLO invisibile sopra la riga, che serve solo a "prendere"
       il clic (cliccare su una linea sottile sarebbe difficile).

    Tutti i rettangoli portano lo stesso id: passare il mouse o cliccare su
    una qualunque riga della frase vuol dire la stessa nota.
    """
    elementi: list[QGraphicsItem] = []
    for x0, y0, x1, y1 in sottolineatura.rettangoli:
        y_linea = y1 + DISTANZA_SOTTOLINEATURA

        linea = QGraphicsLineItem(QLineF(x0, y_linea, x1, y_linea))
        penna = QPen(COLORE_SOTTOLINEATURA, SPESSORE_SOTTOLINEATURA)
        penna.setCosmetic(True)  # "cosmetica" = spessore fisso sullo schermo, qualunque zoom
        linea.setPen(penna)

        area_clic = QGraphicsRectItem(QRectF(x0, y0, x1 - x0, y_linea - y0))
        area_clic.setPen(QPen(Qt.PenStyle.NoPen))  # nessun bordo
        area_clic.setBrush(QBrush(Qt.BrushStyle.NoBrush))  # nessun riempimento: invisibile
        area_clic.setData(CHIAVE_ID, sottolineatura.id)
        area_clic.setCursor(Qt.CursorShape.PointingHandCursor)  # la "manina" dice: cliccabile

        for elemento in (linea, area_clic):
            elemento.setZValue(LIVELLO_NOTE)
        elementi += [linea, area_clic]
    return elementi


def crea_evidenziatura(evidenziatura: Evidenziatura, colore: Colore | None) -> list[QGraphicsRectItem]:
    """Un rettangolo colorato e trasparente sopra ogni riga della frase.

    colore = il colore della tavolozza; None se non c'è più (allora è grigio).
    Il rettangolo stesso "prende" il clic: un clic singolo apre la nota.
    """
    codice_colore = colore.colore if colore is not None else COLORE_SCONOSCIUTO
    riempimento = QColor(codice_colore)
    riempimento.setAlpha(TRASPARENZA_EVIDENZIATURA)

    elementi = []
    for x0, y0, x1, y1 in evidenziatura.rettangoli:
        rettangolo = QGraphicsRectItem(QRectF(x0, y0, x1 - x0, y1 - y0))
        rettangolo.setPen(QPen(Qt.PenStyle.NoPen))  # nessun bordo
        rettangolo.setBrush(QBrush(riempimento))
        rettangolo.setData(CHIAVE_ID, evidenziatura.id)
        rettangolo.setData(CHIAVE_CLIC_SINGOLO, True)
        rettangolo.setCursor(Qt.CursorShape.PointingHandCursor)
        rettangolo.setZValue(LIVELLO_NOTE - 1)  # sotto le sottolineature
        elementi.append(rettangolo)
    return elementi


def crea_segnalibro(segnalibro: Segnalibro) -> QGraphicsRectItem:
    """Evidenzia in giallo la parola del segnalibro.

    Non ha un id: non è una nota da aprire, quindi cliccandolo non succede niente.
    """
    x0, y0, x1, y1 = segnalibro.rett
    evidenziatore = QGraphicsRectItem(QRectF(x0, y0, x1 - x0, y1 - y0))
    evidenziatore.setPen(QPen(Qt.PenStyle.NoPen))
    evidenziatore.setBrush(QBrush(COLORE_SEGNALIBRO))
    evidenziatore.setZValue(LIVELLO_NOTE - 1)  # sotto le sottolineature
    return evidenziatore
