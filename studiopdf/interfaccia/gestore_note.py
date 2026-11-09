"""Cosa succede quando l'utente crea, apre, modifica o elimina una nota.

La vista della pagina dice SOLO "hanno cliccato qui" (con i suoi segnali);
questo modulo decide cosa fare: mostrare un menu, aprire il pop-up,
aggiornare l'archivio, salvare e ridisegnare.
"""

import html
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
from PySide6.QtWidgets import QMenu

from studiopdf.documento import Parola, rettangoli_per_riga, testo_frase
from studiopdf.impostazioni import TASTI_SALVA_NOTA
from studiopdf.interfaccia import disegno
from studiopdf.interfaccia.anteprima import AnteprimaNota
from studiopdf.interfaccia.popup import RisultatoPopup, chiedi_conferma, chiedi_nota
from studiopdf.note import Sottolineatura
from studiopdf.tavolozza import Colore, trova_colore

# TYPE_CHECKING è vero solo per gli strumenti che controllano i tipi, mai
# durante l'esecuzione: così evitiamo un import circolare con finestra.py.
if TYPE_CHECKING:
    from studiopdf.interfaccia.finestra import FinestraPrincipale

# Oltre questa lunghezza, nei titoli la frase sottolineata viene accorciata con «…».
LUNGHEZZA_MASSIMA_TITOLO = 60


def titolo_frase(testo: str) -> str:
    """Il titolo di una sottolineatura: la frase tra «», accorciata se è lunga.

    Esempi:  "serie monotona"           -> "«serie monotona»"
             (frase di 100 caratteri)   -> "«i primi 60 caratteri…»"
    """
    if len(testo) > LUNGHEZZA_MASSIMA_TITOLO:
        # rstrip() toglie l'eventuale spazio finale, così non resta "parola …".
        testo = testo[:LUNGHEZZA_MASSIMA_TITOLO].rstrip() + "…"
    return f"«{testo}»"


class GestoreNote:
    def __init__(self, finestra: "FinestraPrincipale") -> None:
        # Dalla finestra prendiamo: archivio, documento, pagina corrente, vista,
        # tavolozza, ridisegna_note(), avvisa() e la barra di stato.
        self.finestra = finestra

        # La schedina che compare passando il mouse su una nota.
        self.anteprima = AnteprimaNota(finestra)
        # Interruttore "Anteprima delle note" del menu Config.
        self.anteprima_attiva = True

    # =========================================================================
    # Anteprima (mouse sopra una nota)
    # =========================================================================

    def mostra_anteprima(self, id: str, posizione: QPoint) -> None:
        """Mostra titolo e testo della nota in una schedina vicino al mouse."""
        archivio = self.finestra.archivio
        if archivio is None or not self.anteprima_attiva:
            return
        try:
            nota = archivio.trova(id)
        except KeyError:
            return

        # html.escape evita che caratteri come < o & nel testo rompano il titolo (che è HTML).
        if isinstance(nota, Sottolineatura):
            titolo, testo = html.escape(titolo_frase(nota.testo)), nota.spiegazione
        else:
            titolo, testo = self._titolo_pallino_html(nota.colore), nota.testo
        self.anteprima.mostra(titolo, testo, posizione)

    def nascondi_anteprima(self) -> None:
        self.anteprima.hide()

    # =========================================================================
    # Menu del clic destro su una nota
    # =========================================================================

    def quando_menu_nota(self, id: str, posizione: QPoint) -> None:
        self.nascondi_anteprima()
        menu = QMenu(self.finestra)
        azione_modifica = menu.addAction("Modifica…")
        menu.addSeparator()
        azione_elimina = menu.addAction("Elimina")

        scelta = menu.exec(posizione)
        if scelta is azione_modifica:
            self.apri_nota(id)
        elif scelta is azione_elimina:
            self.elimina_nota(id)

    def elimina_nota(self, id: str) -> None:
        """Elimina una nota, dopo aver chiesto conferma."""
        if not self._modificabile():
            return
        try:
            nota = self.finestra.archivio.trova(id)
        except KeyError:
            return

        if isinstance(nota, Sottolineatura):
            domanda = f"Eliminare la sottolineatura di {titolo_frase(nota.testo)}?"
        else:
            domanda = f"Eliminare il pallino «{self._titolo_pallino(nota.colore)}»?"
        if self.conferma(domanda + "\nL'operazione non si può annullare."):
            self.finestra.archivio.elimina(id)
            self._salva_e_ridisegna()

    def conferma(self, domanda: str) -> bool:
        """Chiede sì/no all'utente. È un metodo a parte così i test possono sostituirlo."""
        return chiedi_conferma(self.finestra, "Elimina nota", domanda)

    # =========================================================================
    # Menu del clic destro su una parola
    # =========================================================================

    def quando_menu_parola(self, parola: Parola, posizione: QPoint) -> None:
        # Per sottolineare non si passa più da qui: si seleziona la frase
        # trascinando il mouse (vedi quando_selezione).
        menu = QMenu(self.finestra)
        azione_segnalibro = menu.addAction("Segnalibro qui")

        if self.mostra_menu(menu, posizione) is azione_segnalibro:
            self.metti_segnalibro(parola)

    # =========================================================================
    # Menu dopo aver selezionato una frase trascinando il mouse
    # =========================================================================

    def quando_selezione(self, parole: list[Parola], posizione: QPoint) -> None:
        """L'utente ha selezionato delle parole: gli chiediamo se vuole sottolinearle."""
        menu = QMenu(self.finestra)
        azione_sottolinea = menu.addAction("Sottolinea e spiega…")

        if self.mostra_menu(menu, posizione) is azione_sottolinea:
            self.sottolinea(parole)

    # =========================================================================
    # Segnalibro
    # =========================================================================

    def metti_segnalibro(self, parola: Parola) -> None:
        """Mette il segnalibro su questa parola (al posto di quello di prima)."""
        if not self._modificabile():
            return
        self.finestra.archivio.imposta_segnalibro(self.finestra.pagina, parola.testo, parola.rett)
        self._salva_e_ridisegna()
        self.finestra.statusBar().showMessage(f"Segnalibro messo su «{parola.testo}»", 3000)

    # =========================================================================
    # Sottolineature
    # =========================================================================

    def sottolinea(self, parole: list[Parola]) -> None:
        """Chiede la spiegazione e sottolinea la frase formata da queste parole.

        Le parole devono essere in ordine di lettura (come le dà la selezione).
        Se anche una sola è già sottolineata, avvisa e non fa niente:
        due sottolineature non devono mai stare una sopra l'altra.
        """
        if not parole or not self._modificabile():
            return
        archivio = self.finestra.archivio
        pagina = self.finestra.pagina

        if archivio.sottolineatura_sovrapposta(pagina, [parola.rett for parola in parole]) is not None:
            self.finestra.avvisa(
                "Già sottolineata",
                "Una parte di questa frase è già sottolineata.\n"
                "Per cambiarne la spiegazione fai doppio clic sulla sottolineatura.",
            )
            return

        testo = testo_frase(parole)
        risposta = self.chiedi(titolo_frase(testo))
        if risposta is not None and risposta[0] == "salva":
            # Un rettangolo per ogni riga: la linea sotto la frase sarà continua.
            archivio.aggiungi_sottolineatura(pagina, testo, rettangoli_per_riga(parole), risposta[1])
            self._salva_e_ridisegna()

    # =========================================================================
    # Pallini nel margine
    # =========================================================================

    def quando_clic_margine(self, lato: str, y: float, posizione: QPoint) -> None:
        """Clic nel margine: menu con i colori della tavolozza, poi il pop-up."""
        if not self._modificabile():
            return
        menu = QMenu(self.finestra)
        azioni = {}  # azione del menu -> colore corrispondente
        for colore in self.finestra.tavolozza:
            azione = menu.addAction(_icona_colore(colore.colore), f"{colore.nome} — {colore.significato}")
            azioni[azione] = colore

        scelta = menu.exec(posizione)
        if scelta in azioni:
            self.nuovo_pallino(lato, y, azioni[scelta])

    def pallino_da_tastiera(self, nome_colore: str) -> None:
        """Tasto del colore premuto: pallino all'altezza del mouse, nel margine più vicino."""
        if not self._modificabile():
            return
        colore = trova_colore(self.finestra.tavolozza, nome_colore)
        punto = self.finestra.vista.punto_sotto_mouse()
        if colore is None or punto is None:
            self.finestra.statusBar().showMessage("Porta il mouse sulla riga dove mettere il pallino.", 4000)
            return

        larghezza, _ = self.finestra.documento.dimensione_pagina(self.finestra.pagina)
        lato = "sx" if punto.x() < larghezza / 2 else "dx"
        self.nuovo_pallino(lato, punto.y(), colore)

    def nuovo_pallino(self, lato: str, y: float, colore: Colore) -> None:
        """Chiede il testo e mette un pallino del colore scelto all'altezza y."""
        if not self._modificabile():
            return
        risposta = self.chiedi(self._titolo_pallino(colore.nome))
        if risposta is not None and risposta[0] == "salva":
            self.finestra.archivio.aggiungi_pallino(self.finestra.pagina, y, lato, colore.nome, risposta[1])
            self._salva_e_ridisegna()

    # =========================================================================
    # Aprire una nota esistente (doppio clic, o «Modifica…» dal clic destro)
    # =========================================================================

    def apri_nota(self, id: str) -> None:
        """Mostra la nota nel pop-up; l'utente può modificarla o eliminarla."""
        self.nascondi_anteprima()
        if not self._modificabile():
            return
        archivio = self.finestra.archivio
        try:
            nota = archivio.trova(id)
        except KeyError:
            return  # nota sparita nel frattempo: non c'è niente da aprire

        if isinstance(nota, Sottolineatura):
            titolo, testo = titolo_frase(nota.testo), nota.spiegazione
        else:
            titolo, testo = self._titolo_pallino(nota.colore), nota.testo

        risposta = self.chiedi(titolo, testo, eliminabile=True)
        if risposta is None:
            return
        azione, nuovo_testo = risposta
        if azione == "salva":
            archivio.modifica(id, nuovo_testo)
        else:
            archivio.elimina(id)
        self._salva_e_ridisegna()

    # =========================================================================
    # Funzioni di aiuto
    # =========================================================================

    def chiedi(self, titolo: str, testo: str = "", eliminabile: bool = False) -> RisultatoPopup:
        """Apre il pop-up. È un metodo a parte così i test possono sostituirlo."""
        # Il tasto per salvare scelto in ⚙ Config → Keybinding (predefinito: Invio).
        tasti_salva = self.finestra.impostazioni.tasti.get("salva_nota", TASTI_SALVA_NOTA)
        return chiedi_nota(self.finestra, titolo, testo, eliminabile, tasti_salva=tasti_salva)

    def mostra_menu(self, menu: QMenu, posizione: QPoint) -> QAction | None:
        """Mostra il menu e aspetta la scelta (None = nessuna).

        È un metodo a parte così i test possono sostituirlo: un menu vero
        aspetterebbe un clic che nei test non arriva mai.
        """
        return menu.exec(posizione)

    def _titolo_pallino_html(self, nome_colore: str) -> str:
        """Come _titolo_pallino, ma con il pallino colorato (per l'anteprima, che accetta HTML)."""
        colore = trova_colore(self.finestra.tavolozza, nome_colore)
        codice = colore.colore if colore else disegno.COLORE_SCONOSCIUTO
        significato = colore.significato if colore else nome_colore
        return f'<span style="color:{codice}">●</span> {html.escape(significato)}'

    def _titolo_pallino(self, nome_colore: str) -> str:
        """Titolo del pop-up di un pallino: il SIGNIFICATO del colore (es. "● da ripassare")."""
        colore = trova_colore(self.finestra.tavolozza, nome_colore)
        return f"● {colore.significato}" if colore else f"● {nome_colore}"

    def _modificabile(self) -> bool:
        """Si possono cambiare le note? (c'è un libro aperto e non è in sola lettura)"""
        archivio = self.finestra.archivio
        if archivio is None:
            return False
        if archivio.sola_lettura:
            self.finestra.statusBar().showMessage("Note in sola lettura: le modifiche non sono possibili.", 4000)
            return False
        return True

    def _salva_e_ridisegna(self) -> None:
        """Salva su disco e ridisegna le note (la pagina e lo scorrimento non cambiano).

        Se il salvataggio non riesce avvisa, ma la nota resta in memoria.
        """
        try:
            self.finestra.archivio.salva()
        except OSError as errore:
            self.finestra.avvisa(
                "Note non salvate",
                f"Non riesco a salvare le note:\n{errore}\n\n"
                "Le modifiche restano finché il programma è aperto; "
                "al prossimo cambiamento riproverò a salvare.",
            )
        self.finestra.ridisegna_note()


def _icona_colore(codice_colore: str) -> QIcon:
    """Un quadratino pieno del colore indicato, da mostrare accanto alle voci del menu."""
    quadratino = QPixmap(16, 16)
    quadratino.fill(QColor(codice_colore))
    return QIcon(quadratino)
