"""La finestra principale di StudioPDF.

Si occupa di: aprire un libro (PDF + note), sfogliare le pagine, lo zoom,
la barra di stato e gli avvisi. Cosa succede quando si clicca una nota
è deciso da gestore_note.py.
"""

from pathlib import Path

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMessageBox

from studiopdf.archivio import Archivio
from studiopdf.documento import Documento, ErroreDocumento
from studiopdf.interfaccia.gestore_note import GestoreNote
from studiopdf.interfaccia.vista_pagina import VistaPagina
from studiopdf.percorsi import cartella_base
from studiopdf.tavolozza import carica_tavolozza

# Limiti e passo dello zoom.
ZOOM_MINIMO = 0.25
ZOOM_MASSIMO = 5.0
PASSO_ZOOM = 1.2  # ogni "scatto" ingrandisce o rimpicciolisce del 20%

# Per quanto tempo restano visibili i messaggi brevi nella barra di stato.
DURATA_MESSAGGI_MS = 3000

TITOLO = "StudioPDF"


class FinestraPrincipale(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(TITOLO)
        self.resize(1000, 800)

        # --- Stato del programma ---
        self.documento: Documento | None = None  # il PDF aperto (None = nessuno)
        self.archivio: Archivio | None = None  # le note di quel PDF
        self.pagina = 1  # la pagina mostrata, da 1
        self.zoom = 1.0
        # Finché l'utente non cambia lo zoom a mano, la pagina si adatta alla larghezza.
        self.zoom_manuale = False

        # I colori dei pallini, letti una volta all'avvio da config.json.
        self.tavolozza = carica_tavolozza(cartella_base())

        # --- La vista della pagina occupa tutta la finestra ---
        self.vista = VistaPagina(self)
        self.setCentralWidget(self.vista)

        # --- Chi gestisce le note ---
        self.gestore_note = GestoreNote(self)

        self._collega_segnali()
        self._crea_menu()
        self._crea_scorciatoie()
        self._crea_barra_di_stato()

    # =========================================================================
    # Costruzione dell'interfaccia
    # =========================================================================

    def _collega_segnali(self) -> None:
        """Quando la vista emette un segnale, quale funzione deve rispondere."""
        self.vista.zoomRichiesto.connect(self.cambia_zoom)
        self.vista.menuParola.connect(self.gestore_note.quando_menu_parola)
        self.vista.clicNota.connect(self.gestore_note.apri_nota)
        self.vista.clicMargine.connect(self.gestore_note.quando_clic_margine)
        self.vista.messaggio.connect(lambda testo: self.statusBar().showMessage(testo, DURATA_MESSAGGI_MS))

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

    def _crea_barra_di_stato(self) -> None:
        # A destra, fisso: il numero di pagina. A sinistra: i messaggi brevi.
        self.etichetta_pagina = QLabel("")
        self.statusBar().addPermanentWidget(self.etichetta_pagina)
        self.statusBar().showMessage("Apri un PDF con File → Apri… (Ctrl+O)")

    # =========================================================================
    # Aprire un libro
    # =========================================================================

    def scegli_e_apri(self) -> None:
        """Mostra la finestra di scelta del file e apre il PDF scelto."""
        percorso, _ = QFileDialog.getOpenFileName(self, "Apri un PDF", "", "Documenti PDF (*.pdf)")
        if percorso:  # stringa vuota = l'utente ha annullato
            self.apri(percorso)

    def apri(self, percorso: str | Path) -> None:
        """Apre il PDF indicato insieme alle sue note."""
        try:
            nuovo_documento = Documento(percorso)
        except ErroreDocumento as errore:
            self.avvisa("PDF non apribile", str(errore))
            return

        # Chiudiamo il libro precedente solo DOPO aver aperto il nuovo con successo.
        if self.documento is not None:
            self.documento.chiudi()

        self.documento = nuovo_documento
        self.archivio = Archivio.carica(percorso)
        self._avvisa_problemi_archivio()

        self.zoom_manuale = False
        self.setWindowTitle(f"{TITOLO} — {self.documento.percorso.name}")
        self._vai_al_segnalibro()

    def _vai_al_segnalibro(self) -> None:
        """Apre il libro dove ci si era fermati (o a pagina 1 se non c'è segnalibro)."""
        pagina = self.archivio.pagina_di_partenza(self.documento.numero_pagine)
        self.vai_a(pagina)

        segnalibro = self.archivio.segnalibro
        if segnalibro is not None and segnalibro.pagina == pagina:
            self.vista.mostra_rettangolo(segnalibro.rett)  # scorre fino alla parola

    def _avvisa_problemi_archivio(self) -> None:
        """Se il file delle note aveva problemi, lo diciamo subito all'utente."""
        if self.archivio.file_rotto is not None:
            self.avvisa(
                "File delle note illeggibile",
                "Il file delle note non si poteva leggere ed è stato messo da parte come:\n"
                f"{self.archivio.file_rotto.name}\n\n"
                "Non è stato cancellato niente. Si riparte con le note vuote.",
            )
        if self.archivio.sola_lettura:
            self.avvisa(
                "Note in sola lettura",
                "Il file delle note è stato creato da una versione più nuova di StudioPDF.\n"
                "Il libro si apre, ma le note non verranno modificate.",
            )

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
        """Ridisegna la pagina corrente con le sue note e aggiorna il numero di pagina."""
        if self.documento is None:
            return
        self.vista.mostra_pagina(self.documento, self.pagina, self.zoom)

        sottolineature, pallini = self.archivio.della_pagina(self.pagina)
        segnalibro = self.archivio.segnalibro
        if segnalibro is not None and segnalibro.pagina != self.pagina:
            segnalibro = None  # il segnalibro si disegna solo sulla sua pagina
        self.vista.disegna_note(sottolineature, pallini, segnalibro, self.tavolozza, self.documento)

        self.etichetta_pagina.setText(f"pagina {self.pagina} / {self.documento.numero_pagine}")

    def avvisa(self, titolo: str, testo: str) -> None:
        """Mostra un messaggio di avviso (finestrella con OK)."""
        QMessageBox.warning(self, titolo, testo)

    def resizeEvent(self, evento) -> None:
        """Quando la finestra cambia dimensione, la pagina si riadatta alla larghezza."""
        super().resizeEvent(evento)
        if self.documento is not None and not self.zoom_manuale:
            self.vai_a(self.pagina)
