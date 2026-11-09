"""Crea gli elementi grafici delle note: sottolineature, pallini, segnalibro.

Le funzioni qui CREANO gli elementi ma non li mettono nella scena:
è VistaPagina a farlo, così sa sempre quali elementi sono "note"
e può toglierli quando ridisegna.

Tutte le coordinate sono in punti PDF (vedi vista_pagina.py).
"""

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem, QGraphicsRectItem

from studiopdf.documento import Documento
from studiopdf.note import Pallino, Segnalibro, Sottolineatura
from studiopdf.tavolozza import Colore

# Ogni elemento cliccabile si porta dietro l'id della sua nota,
# salvato con setData(CHIAVE_ID, id). Gli altri elementi non hanno id.
CHIAVE_ID = 0

# --- Aspetto delle sottolineature ---
COLORE_SOTTOLINEATURA = QColor("#3E63DD")
SPESSORE_SOTTOLINEATURA = 2  # in pixel dello schermo (non cambia con lo zoom)
DISTANZA_SOTTOLINEATURA = 1  # punti PDF sotto il bordo inferiore della parola

# --- Aspetto dei pallini (misure in punti PDF) ---
RAGGIO_PALLINO = 5
DISTANZA_MINIMA_PALLINI = 10  # due pallini più vicini di così in altezza si sovrapporrebbero...
SPOSTAMENTO_PALLINI = 12  # ...e allora il secondo si sposta di lato di questa quantità
COLORE_SCONOSCIUTO = "#9E9E9E"  # grigio: per un colore tolto dalla tavolozza
COLORE_BORDO_PALLINO = QColor(255, 255, 255, 200)  # bordino bianco: si vede anche su fondi scuri

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


def posizioni_pallini(pallini: list[Pallino], documento: Documento) -> dict[str, tuple[float, float]]:
    """Calcola dove disegnare ogni pallino: {id: (x, y)}.

    - La y è quella della riga accanto a cui il pallino è stato messo.
    - La x è il centro del margine (sinistro o destro).
    - Se più pallini sono quasi alla stessa altezza, quelli successivi si
      spostano di lato, verso il bordo esterno della pagina, per non coprirsi.
    """
    posizioni: dict[str, tuple[float, float]] = {}

    for lato in ("sx", "dx"):
        # Verso il bordo esterno: a sinistra le x diminuiscono, a destra aumentano.
        direzione = -1 if lato == "sx" else +1

        pallini_del_lato = sorted((p for p in pallini if p.lato == lato), key=lambda p: p.y)
        spostamento = 0.0
        y_precedente: float | None = None

        for pallino in pallini_del_lato:
            vicino_al_precedente = y_precedente is not None and pallino.y - y_precedente < DISTANZA_MINIMA_PALLINI
            spostamento = spostamento + SPOSTAMENTO_PALLINI if vicino_al_precedente else 0.0

            x = documento.centro_margine(pallino.pagina, lato) + direzione * spostamento
            larghezza_pagina, _ = documento.dimensione_pagina(pallino.pagina)
            x = min(max(x, RAGGIO_PALLINO), larghezza_pagina - RAGGIO_PALLINO)  # mai fuori dalla pagina

            posizioni[pallino.id] = (x, pallino.y)
            y_precedente = pallino.y

    return posizioni


def crea_pallino(pallino: Pallino, x: float, y: float, colore: Colore | None) -> QGraphicsEllipseItem:
    """Un cerchio pieno centrato in (x, y). Se colore è None (non più in tavolozza) è grigio."""
    codice_colore = colore.colore if colore is not None else COLORE_SCONOSCIUTO

    # Un'ellisse si descrive con il rettangolo che la contiene: angolo in alto a sinistra + lati.
    cerchio = QGraphicsEllipseItem(
        QRectF(x - RAGGIO_PALLINO, y - RAGGIO_PALLINO, 2 * RAGGIO_PALLINO, 2 * RAGGIO_PALLINO)
    )
    cerchio.setBrush(QBrush(QColor(codice_colore)))
    bordo = QPen(COLORE_BORDO_PALLINO, 1)
    bordo.setCosmetic(True)
    cerchio.setPen(bordo)

    cerchio.setData(CHIAVE_ID, pallino.id)
    cerchio.setCursor(Qt.CursorShape.PointingHandCursor)
    cerchio.setZValue(LIVELLO_NOTE + 1)  # sopra le sottolineature
    return cerchio


def crea_segnalibro(segnalibro: Segnalibro) -> QGraphicsRectItem:
    """Evidenzia in giallo la parola del segnalibro.

    Non ha un id: non è una nota da aprire, quindi cliccandolo non succede niente.
    """
    x0, y0, x1, y1 = segnalibro.rett
    evidenziatore = QGraphicsRectItem(QRectF(x0, y0, x1 - x0, y1 - y0))
    evidenziatore.setPen(QPen(Qt.PenStyle.NoPen))
    evidenziatore.setBrush(QBrush(COLORE_SEGNALIBRO))
    evidenziatore.setZValue(LIVELLO_NOTE - 1)  # sotto sottolineature e pallini
    return evidenziatore
