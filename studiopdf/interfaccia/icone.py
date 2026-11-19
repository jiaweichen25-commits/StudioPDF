"""Le icone del programma, disegnate in SVG direttamente qui nel codice.

Perché nel codice e non in un file .svg a parte? Così l'icona finisce da sola
dentro l'exe (PyInstaller impacchetta il codice Python, mentre i file extra
andrebbero aggiunti a mano in StudioPDF.spec).

Come si legge un SVG
--------------------
È un disegno descritto a parole. viewBox="0 0 64 64" vuol dire che il foglio
è un quadrato di 64 x 64 unità (la y cresce andando verso il BASSO).
Dentro ci sono dei <path>, cioè dei tracciati:
    M x y        "muovi la penna" in (x, y) senza disegnare
    L x y        linea dritta fino a (x, y)
    Q cx cy x y  curva fino a (x, y), "tirata" verso il punto (cx, cy)
    Z            chiudi la forma tornando al punto di partenza
fill = colore di riempimento, stroke = colore del bordo.
"""

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Un libro aperto, in bianco e nero: tre strati di pagine dietro (a ventaglio),
# la pagina sinistra con tre righe di testo e la pagina destra che si alza.
SVG_ULTIMO_LIBRO = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <g fill="#FFFFFF" stroke="#000000" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round">
    <!-- Gli strati di pagine dietro: dal più grande (in fondo) al più piccolo. -->
    <path d="M3 22 L3 55 Q18 51 32 59 Q46 51 61 55 L61 22 Z"/>
    <path d="M7 17 L7 51 Q20 47 32 55 Q44 47 57 51 L57 17 Z"/>
    <!-- Pagina sinistra. -->
    <path d="M11 10 Q24 9 32 17 L32 53 Q23 45 11 46 Z"/>
    <!-- Pagina destra: più alta e piegata, come se si stesse girando. -->
    <path d="M32 17 Q37 8 51 4 L51 44 Q39 46 32 53 Z"/>
  </g>
  <!-- Tre righe di "testo" sulla pagina sinistra. -->
  <g fill="none" stroke="#000000" stroke-width="2.8" stroke-linecap="round">
    <path d="M15 19 Q22 19 27 23"/>
    <path d="M15 27 Q22 27 27 31"/>
    <path d="M15 35 Q22 35 27 39"/>
  </g>
</svg>
"""

# Le misure (in pixel) in cui si prepara l'icona: Qt sceglie quella giusta
# per la barra, i menu e gli schermi ad alta densità.
MISURE = (16, 24, 32, 48, 64)


def icona_da_svg(svg: str) -> QIcon:
    """Trasforma il testo SVG in un'icona Qt, disegnandolo in più misure."""
    disegnatore = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    icona = QIcon()
    for lato in MISURE:
        immagine = QPixmap(lato, lato)
        immagine.fill(Qt.GlobalColor.transparent)  # sfondo trasparente
        pittore = QPainter(immagine)
        pittore.setRenderHint(QPainter.RenderHint.Antialiasing)  # bordi morbidi
        disegnatore.render(pittore, QRectF(0, 0, lato, lato))
        pittore.end()
        icona.addPixmap(immagine)
    return icona


def icona_ultimo_libro() -> QIcon:
    """L'icona del pulsante «Apri l'ultimo libro»."""
    return icona_da_svg(SVG_ULTIMO_LIBRO)
