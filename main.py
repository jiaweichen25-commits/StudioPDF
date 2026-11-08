"""Punto di avvio di StudioPDF.

Uso:
    python main.py                  apre la finestra vuota
    python main.py "libro.pdf"      apre direttamente un libro

Lo stesso vale per l'eseguibile: StudioPDF.exe "libro.pdf"
(è così che funziona "Apri con…" di Windows).
"""

import sys

from PySide6.QtWidgets import QApplication

from studiopdf.interfaccia.finestra import FinestraPrincipale


def main() -> None:
    app = QApplication(sys.argv)

    finestra = FinestraPrincipale()
    finestra.show()  # prima si mostra, così la finestra conosce le sue dimensioni

    # sys.argv[0] è il nome del programma; sys.argv[1], se c'è, è il PDF da aprire.
    if len(sys.argv) > 1:
        finestra.apri(sys.argv[1])

    # Da qui in poi Qt aspetta i clic e i tasti, finché la finestra non si chiude.
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
