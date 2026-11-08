"""Crea gli elementi grafici delle note: sottolineature, pallini, segnalibro.

Le funzioni qui CREANO gli elementi ma non li mettono nella scena:
è VistaPagina a farlo, così sa sempre quali elementi sono "note"
e può toglierli quando ridisegna.

Tutte le coordinate sono in punti PDF (vedi vista_pagina.py).
"""

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsRectItem

from studiopdf.note import Sottolineatura

# Ogni elemento cliccabile si porta dietro l'id della sua nota,
# salvato con setData(CHIAVE_ID, id). Gli altri elementi non hanno id.
CHIAVE_ID = 0

# --- Aspetto delle sottolineature ---
COLORE_SOTTOLINEATURA = QColor("#3E63DD")
SPESSORE_SOTTOLINEATURA = 2  # in pixel dello schermo (non cambia con lo zoom)
DISTANZA_SOTTOLINEATURA = 1  # punti PDF sotto il bordo inferiore della parola

# Le note stanno sopra la pagina (che ha livello 0).
LIVELLO_NOTE = 2


def crea_sottolineatura(sottolineatura: Sottolineatura) -> list[QGraphicsItem]:
    """Una sottolineatura è fatta di due elementi:

    1. la LINEA visibile sotto la parola;
    2. un RETTANGOLO invisibile sopra la parola, che serve solo a
       "prendere" il clic (cliccare su una linea sottile sarebbe difficile).
    """
    x0, y0, x1, y1 = sottolineatura.rett
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
    area_clic.setToolTip(sottolineatura.spiegazione)  # anteprima passando col mouse

    for elemento in (linea, area_clic):
        elemento.setZValue(LIVELLO_NOTE)
    return [linea, area_clic]
