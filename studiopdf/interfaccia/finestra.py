"""La finestra principale di StudioPDF.

Si occupa di: aprire un libro (PDF + note), sfogliare le pagine, lo zoom,
la barra di stato e gli avvisi. Cosa succede quando si clicca una nota
è deciso da gestore_note.py.
"""

from pathlib import Path

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMessageBox, QToolBar

from studiopdf.archivio import Archivio
from studiopdf.documento import Documento, ErroreDocumento
from studiopdf.interfaccia.gestore_note import GestoreNote
from studiopdf.impostazioni import (
    PREFISSO_PALLINO,
    ErroreImpostazioni,
    Impostazioni,
    carica_impostazioni,
    salva_impostazioni,
)
from studiopdf.interfaccia.vista_pagina import VistaPagina
from studiopdf.percorsi import cartella_base
from studiopdf.tavolozza import carica_tavolozza

# Limiti e passo dello zoom.
ZOOM_MINIMO = 0.25
ZOOM_MASSIMO = 5.0
PASSO_ZOOM = 1.2  # ogni "scatto" moltiplica (ingrandisci) o divide (rimpicciolisci) lo zoom per 1.2

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

        # I colori dei pallini e le impostazioni, letti all'avvio da config.json.
        self.tavolozza = carica_tavolozza(cartella_base())
        self.impostazioni = carica_impostazioni(cartella_base(), self.tavolozza)

        # Le scorciatoie da tastiera attive: azione -> elenco di QShortcut.
        self.scorciatoie: dict[str, list[QShortcut]] = {}

        # --- La vista della pagina occupa tutta la finestra ---
        self.vista = VistaPagina(self)
        self.setCentralWidget(self.vista)

        # --- Chi gestisce le note ---
        self.gestore_note = GestoreNote(self)

        self._collega_segnali()
        self._crea_menu()
        self._crea_barra_strumenti()
        self._crea_barra_di_stato()

        # Tasti e interruttori dalle impostazioni (senza riscriverle: sono appena state lette).
        self.applica_impostazioni(self.impostazioni, salva=False)

    # =========================================================================
    # Costruzione dell'interfaccia
    # =========================================================================

    def _collega_segnali(self) -> None:
        """Quando la vista emette un segnale, quale funzione deve rispondere."""
        self.vista.zoomRichiesto.connect(self.cambia_zoom)
        self.vista.menuParola.connect(self.gestore_note.quando_menu_parola)
        self.vista.clicNota.connect(self.gestore_note.apri_nota)
        self.vista.clicMargine.connect(self.gestore_note.quando_clic_margine)
        self.vista.menuNota.connect(self.gestore_note.quando_menu_nota)
        self.vista.notaSorvolata.connect(self.gestore_note.mostra_anteprima)
        self.vista.notaLasciata.connect(self.gestore_note.nascondi_anteprima)
        self.vista.richiestaPaginaPrecedente.connect(self.pagina_precedente)
        self.vista.richiestaPaginaSuccessiva.connect(self.pagina_successiva)
        self.vista.messaggio.connect(lambda testo: self.statusBar().showMessage(testo, DURATA_MESSAGGI_MS))

    def _crea_menu(self) -> None:
        menu_file = self.menuBar().addMenu("&File")

        # Il tasto per "Apri" non si mette qui: è una scorciatoia configurabile (vedi _applica_tasti).
        azione_apri = menu_file.addAction("&Apri…")
        azione_apri.triggered.connect(self.scegli_e_apri)

        menu_file.addSeparator()
        azione_esci = menu_file.addAction("&Esci")
        azione_esci.triggered.connect(self.close)

    def _crea_barra_strumenti(self) -> None:
        """Pulsanti per sfogliare e zoomare con il mouse."""
        barra = QToolBar("Navigazione", self)
        barra.setMovable(False)
        self.addToolBar(barra)

        self.azione_precedente = barra.addAction("◀  Indietro")
        self.azione_successiva = barra.addAction("Avanti  ▶")
        barra.addSeparator()
        self.azione_rimpicciolisci = barra.addAction("−  Zoom")
        self.azione_ingrandisci = barra.addAction("Zoom  +")

        self.azione_precedente.triggered.connect(self.pagina_precedente)
        self.azione_successiva.triggered.connect(self.pagina_successiva)
        self.azione_rimpicciolisci.triggered.connect(lambda: self.cambia_zoom(-1))
        self.azione_ingrandisci.triggered.connect(lambda: self.cambia_zoom(+1))

    def _crea_barra_di_stato(self) -> None:
        # A destra, fisso: il numero di pagina. A sinistra: i messaggi brevi.
        self.etichetta_pagina = QLabel("")
        self.statusBar().addPermanentWidget(self.etichetta_pagina)
        self.statusBar().showMessage("Apri un PDF con File → Apri…")

    # =========================================================================
    # Aprire un libro
    # =========================================================================

    def scegli_e_apri(self) -> None:
        """Mostra la finestra di scelta del file e apre il PDF scelto."""
        percorso, _ = QFileDialog.getOpenFileName(
            self, "Apri un PDF", self.cartella_iniziale_apri(), "Documenti PDF (*.pdf)"
        )
        if percorso:  # stringa vuota = l'utente ha annullato
            self.apri(percorso)

    def cartella_iniziale_apri(self) -> str:
        """La cartella da cui parte "Apri…": quella dei libri, se esiste ("" = predefinita di Windows)."""
        cartella = self.impostazioni.cartella_libri
        return cartella if cartella and Path(cartella).is_dir() else ""

    def apri(self, percorso: str | Path) -> None:
        """Apre il PDF indicato insieme alle sue note.

        PDF e note si aprono "insieme": se una delle due cose non riesce, resta
        aperto il libro di prima, così le note non finiscono mai nel file sbagliato.
        """
        try:
            nuovo_documento = Documento(percorso)
        except ErroreDocumento as errore:
            self.avvisa("PDF non apribile", str(errore))
            return

        try:
            nuovo_archivio = Archivio.carica(percorso)
        except OSError as errore:  # es. file non disponibile, permessi
            nuovo_documento.chiudi()
            self.avvisa(
                "Note non leggibili",
                f"Non riesco a leggere le note di «{nuovo_documento.percorso.name}»:\n{errore}\n\n"
                "Il libro non è stato aperto, per non rischiare di perdere le note.",
            )
            return

        # Tutto a posto: chiudiamo il libro precedente e passiamo al nuovo.
        if self.documento is not None:
            self.documento.chiudi()
        self.documento = nuovo_documento
        self.archivio = nuovo_archivio
        self._avvisa_problemi_archivio()
        self.statusBar().clearMessage()  # via il messaggio "Apri un PDF…"

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
        if self.archivio.motivo_sola_lettura == "versione_futura":
            self.avvisa(
                "Note in sola lettura",
                "Il file delle note è stato creato da una versione più nuova di StudioPDF.\n"
                "Il libro si apre, ma le note non vengono mostrate né modificate.",
            )
        elif self.archivio.motivo_sola_lettura == "file_illeggibile":
            self.avvisa(
                "Note in sola lettura",
                "Il file delle note è illeggibile e non si è potuto metterlo da parte\n"
                f"({self.archivio.percorso_note.name}).\n\n"
                "Per non rovinarlo, le note di questo libro non verranno salvate.",
            )

    # =========================================================================
    # Impostazioni: tasti e interruttori
    # =========================================================================

    def applica_impostazioni(self, nuove: Impostazioni, salva: bool = True) -> None:
        """Rende attive le impostazioni (tasti, interruttori) e, se richiesto, le salva.

        Se il salvataggio non riesce si avvisa, ma le impostazioni valgono
        comunque finché il programma resta aperto.
        """
        self.impostazioni = nuove
        self._applica_tasti()
        self.vista.frecce_attive = nuove.frecce_laterali
        self.gestore_note.anteprima_attiva = nuove.anteprima_note
        if not nuove.frecce_laterali:
            self.vista.nascondi_frecce()
        if not nuove.anteprima_note:
            self.gestore_note.nascondi_anteprima()

        if salva:
            try:
                salva_impostazioni(cartella_base(), nuove)
            except (ErroreImpostazioni, OSError) as errore:
                self.avvisa(
                    "Impostazioni non salvate",
                    f"{errore}\n\nLe impostazioni valgono finché il programma resta aperto.",
                )

    def _applica_tasti(self) -> None:
        """Toglie tutte le scorciatoie e le ricrea dai tasti delle impostazioni."""
        for elenco in self.scorciatoie.values():
            for scorciatoia in elenco:
                scorciatoia.setEnabled(False)  # spenta subito...
                scorciatoia.deleteLater()  # ...ed eliminata appena possibile
        self.scorciatoie = {}

        for azione, tasti in self.impostazioni.tasti.items():
            funzione = self._funzione_azione(azione)
            if funzione is None:
                continue  # azione sconosciuta (es. pallino di un colore tolto)
            self.scorciatoie[azione] = [
                QShortcut(QKeySequence(tasto), self, activated=funzione) for tasto in tasti if tasto.strip()
            ]

    def _funzione_azione(self, azione: str):
        """Cosa fa ogni azione. Restituisce una funzione senza argomenti (o None)."""
        funzioni = {
            "pagina_precedente": self.pagina_precedente,
            "pagina_successiva": self.pagina_successiva,
            "ingrandisci": lambda: self.cambia_zoom(+1),
            "rimpicciolisci": lambda: self.cambia_zoom(-1),
            "apri_libro": self.scegli_e_apri,
            "chiudi_programma": self.close,
        }
        if azione in funzioni:
            return funzioni[azione]
        if azione.startswith(PREFISSO_PALLINO):
            nome_colore = azione[len(PREFISSO_PALLINO):]
            # "nome=nome_colore" fissa il valore ADESSO: senza, tutte le lambda
            # create nel ciclo userebbero l'ultimo colore.
            return lambda nome=nome_colore: self.gestore_note.pallino_da_tastiera(nome)
        return None

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
        """Ridisegna la pagina corrente (immagine + note) e aggiorna il numero di pagina."""
        if self.documento is None:
            return
        self.vista.mostra_pagina(self.documento, self.pagina, self.zoom)
        self.ridisegna_note()
        self.etichetta_pagina.setText(f"pagina {self.pagina} / {self.documento.numero_pagine}")

    def ridisegna_note(self) -> None:
        """Ridisegna solo le note della pagina corrente (più veloce: l'immagine resta)."""
        if self.documento is None:
            return
        sottolineature, pallini = self.archivio.della_pagina(self.pagina)
        segnalibro = self.archivio.segnalibro
        if segnalibro is not None and segnalibro.pagina != self.pagina:
            segnalibro = None  # il segnalibro si disegna solo sulla sua pagina
        self.vista.disegna_note(sottolineature, pallini, segnalibro, self.tavolozza, self.documento)

    def avvisa(self, titolo: str, testo: str) -> None:
        """Mostra un messaggio di avviso (finestrella con OK)."""
        QMessageBox.warning(self, titolo, testo)

    def resizeEvent(self, evento) -> None:
        """Quando la finestra cambia dimensione, la pagina si riadatta alla larghezza."""
        super().resizeEvent(evento)
        if self.documento is not None and not self.zoom_manuale:
            self.vai_a(self.pagina)
