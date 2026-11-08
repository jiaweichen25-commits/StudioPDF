"""La finestra principale di StudioPDF.

Si occupa di: aprire un libro, sfogliare le pagine, lo zoom,
la barra di stato e gli avvisi. Le note sono gestite da gestore_note.py.
"""

from pathlib import Path

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from studiopdf.documento import Documento, ErroreDocumento
from studiopdf.interfaccia.vista_pagina import VistaPagina
from studiopdf.percorsi import cartella_base

# Limiti e passo dello zoom.
ZOOM_MINIMO = 0.25
ZOOM_MASSIMO = 5.0
PASSO_ZOOM = 1.2  # ogni "scatto" ingrandisce o rimpicciolisce del 20%

TITOLO = "StudioPDF"


class FinestraPrincipale(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(TITOLO)
        self.resize(1000, 800)

        # --- Stato del programma ---
        self.documento: Documento | None = None  # il libro aperto (None = nessuno)
        self.pagina = 1  # la pagina mostrata, da 1
        self.zoom = 1.0
        # Finché l'utente non cambia lo zoom a mano, la pagina si adatta alla larghezza.
        self.zoom_manuale = False

        # --- La vista della pagina occupa tutta la finestra ---
        self.vista = VistaPagina(self)
        self.setCentralWidget(self.vista)
        self.vista.zoomRichiesto.connect(self.cambia_zoom)

        self._crea_menu()
        self._crea_scorciatoie()
        self.statusBar().showMessage("Apri un PDF con File → Apri… (Ctrl+O)")

    # =========================================================================
    # Costruzione dell'interfaccia
    # =========================================================================

    def _crea_menu(self) -> None:
        menu_file = self.menuBar().addMenu("&File")

        azione_apri = menu_file.addAction("&Apri…")
        azione_apri.setShortcut(QKeySequence.StandardKey.Open)  # Ctrl+O
        azione_apri.triggered.connect(self.scegli_e_apri)

        menu_file.addSeparator()
        azione_esci = menu_file.addAction("&Esci")
        azione_esci.triggered.connect(self.close)

    def _crea_scorciatoie(self) -> None:
        """Tasti per sfogliare e zoomare. Ogni coppia è (tasto, funzione da chiamare)."""
        scorciatoie = [
            ("Right", self.pagina_successiva),
            ("PgDown", self.pagina_successiva),
            ("Left", self.pagina_precedente),
            ("PgUp", self.pagina_precedente),
            ("+", lambda: self.cambia_zoom(+1)),
            ("-", lambda: self.cambia_zoom(-1)),
            ("Ctrl++", lambda: self.cambia_zoom(+1)),
            ("Ctrl+-", lambda: self.cambia_zoom(-1)),
        ]
        for tasto, funzione in scorciatoie:
            QShortcut(QKeySequence(tasto), self, activated=funzione)

    # =========================================================================
    # Aprire un libro
    # =========================================================================

    def scegli_e_apri(self) -> None:
        """Mostra la finestra di scelta del file e apre il PDF scelto."""
        percorso, _ = QFileDialog.getOpenFileName(self, "Apri un PDF", "", "Documenti PDF (*.pdf)")
        if percorso:  # stringa vuota = l'utente ha annullato
            self.apri(percorso)

    def apri(self, percorso: str | Path) -> None:
        """Apre il PDF indicato e mostra la prima pagina."""
        try:
            nuovo_documento = Documento(percorso)
        except ErroreDocumento as errore:
            self.avvisa("PDF non apribile", str(errore))
            return

        # Chiudiamo il libro precedente solo DOPO aver aperto il nuovo con successo.
        if self.documento is not None:
            self.documento.chiudi()

        self.documento = nuovo_documento
        self.zoom_manuale = False
        self.setWindowTitle(f"{TITOLO} — {self.documento.percorso.name}")
        self.vai_a(1)

    # =========================================================================
    # Sfogliare
    # =========================================================================

    def vai_a(self, pagina: int) -> None:
        """Mostra la pagina indicata. Se non esiste, non fa niente."""
        if self.documento is None or not 1 <= pagina <= self.documento.numero_pagine:
            return
        self.pagina = pagina
        if not self.zoom_manuale:
            self.zoom = self.vista.zoom_larghezza(self.documento, pagina)
        self.ridisegna()

    def pagina_successiva(self) -> None:
        self.vai_a(self.pagina + 1)

    def pagina_precedente(self) -> None:
        self.vai_a(self.pagina - 1)

    # =========================================================================
    # Zoom
    # =========================================================================

    def cambia_zoom(self, direzione: int) -> None:
        """direzione = +1 ingrandisce, -1 rimpicciolisce (entro i limiti)."""
        if self.documento is None:
            return
        nuovo = self.zoom * PASSO_ZOOM if direzione > 0 else self.zoom / PASSO_ZOOM
        self.zoom = min(ZOOM_MASSIMO, max(ZOOM_MINIMO, nuovo))
        self.zoom_manuale = True
        self.ridisegna()

    # =========================================================================
    # Disegno e messaggi
    # =========================================================================

    def ridisegna(self) -> None:
        """Ridisegna la pagina corrente e aggiorna la barra di stato."""
        if self.documento is None:
            return
        self.vista.mostra_pagina(self.documento, self.pagina, self.zoom)
        self.statusBar().showMessage(f"pagina {self.pagina} / {self.documento.numero_pagine}")

    def avvisa(self, titolo: str, testo: str) -> None:
        """Mostra un messaggio di avviso (finestrella con OK)."""
        QMessageBox.warning(self, titolo, testo)

    def resizeEvent(self, evento) -> None:
        """Quando la finestra cambia dimensione, la pagina si riadatta alla larghezza."""
        super().resizeEvent(evento)
        if self.documento is not None and not self.zoom_manuale:
            self.vai_a(self.pagina)
