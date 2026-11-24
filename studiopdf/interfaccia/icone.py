"""Le icone del programma.

I disegni stanno nella cartella assets/ del progetto, come file .svg: si possono
aprire e modificare con qualsiasi programma di grafica (es. Inkscape) o anche
con il Blocco note. Questo modulo li legge e li trasforma in icone Qt.

Dove sta la cartella assets/ lo decide percorsi.cartella_assets() (cambia tra
lo sviluppo e l'exe creato con PyInstaller).
"""

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from studiopdf.percorsi import cartella_assets

# Le misure (in pixel) in cui si prepara ogni icona: Qt sceglie quella giusta
# per la barra, i menu e gli schermi ad alta densità.
MISURE = (16, 24, 32, 48, 64)


def icona_da_svg(percorso: Path) -> QIcon:
    """Legge un file .svg e lo trasforma in un'icona Qt, disegnandolo in più misure.

    Se il file manca o non è un SVG valido restituisce un'icona VUOTA: il
    programma funziona lo stesso (al posto dell'icona Qt mostra il testo).
    """
    disegnatore = QSvgRenderer(str(percorso))
    if not disegnatore.isValid():
        return QIcon()

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
    """L'icona del pulsante «Apri l'ultimo libro» (assets/ultimo_libro.svg)."""
    return icona_da_svg(cartella_assets() / "ultimo_libro.svg")


def icona_pannello() -> QIcon:
    """L'icona del pulsante che mostra/nasconde il pannello laterale (assets/pannello.svg)."""
    return icona_da_svg(cartella_assets() / "pannello.svg")
