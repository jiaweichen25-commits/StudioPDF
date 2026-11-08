"""Traduzione italiana dei testi "di serie" di Qt.

Alcune scritte non le scriviamo noi ma Qt stesso: i pulsanti «Yes / No»
delle domande di conferma, il testo grigio «Press shortcut» delle caselle
dei tasti, ecc. PySide6 contiene già le loro traduzioni (file qtbase_it.qm):
basta caricarle all'avvio.
"""

from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtWidgets import QApplication


def installa_traduzioni_italiane(app: QApplication) -> bool:
    """Carica la traduzione italiana di Qt. Restituisce False se il file non c'è (si resta in inglese)."""
    cartella = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    traduttore = QTranslator(app)  # "app" come genitore: resta vivo finché vive il programma
    if not traduttore.load("qtbase_it", cartella):
        return False
    app.installTranslator(traduttore)
    return True
