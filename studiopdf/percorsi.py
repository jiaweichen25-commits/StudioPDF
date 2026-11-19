"""Dove stanno i file del programma."""

import sys
from pathlib import Path


def cartella_base() -> Path:
    """La cartella del programma: è lì che sta config.json.

    - Eseguibile creato con PyInstaller: la cartella di StudioPDF.exe.
      (PyInstaller aggiunge l'attributo sys.frozen = True.)
    - Durante lo sviluppo: la cartella del progetto, quella di main.py.
      Questo file sta in studiopdf/, quindi la cartella del progetto è
      la "nonna": parent (studiopdf) -> parent (StudioPDF).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def cartella_assets() -> Path:
    """La cartella assets/ con le icone (file .svg).

    - Eseguibile creato con PyInstaller: i file aggiunti con "datas" in
      StudioPDF.spec finiscono nella cartella interna del programma
      (dist/StudioPDF/_internal), che PyInstaller indica con sys._MEIPASS.
    - Durante lo sviluppo: la cartella assets/ del progetto.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parent.parent / "assets"
