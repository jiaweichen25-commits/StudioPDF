"""Cosa succede quando l'utente crea, apre, modifica o elimina una nota.

La vista della pagina dice SOLO "hanno cliccato qui" (con i suoi segnali);
questo modulo decide cosa fare: mostrare un menu, aprire il pop-up,
aggiornare l'archivio, salvare e ridisegnare.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QMenu

from studiopdf.documento import Parola
from studiopdf.interfaccia.popup import RisultatoPopup, chiedi_nota
from studiopdf.note import Sottolineatura
from studiopdf.tavolozza import Colore, trova_colore

# TYPE_CHECKING è vero solo per gli strumenti che controllano i tipi, mai
# durante l'esecuzione: così evitiamo un import circolare con finestra.py.
if TYPE_CHECKING:
    from studiopdf.interfaccia.finestra import FinestraPrincipale


class GestoreNote:
    def __init__(self, finestra: "FinestraPrincipale") -> None:
        # Dalla finestra prendiamo: archivio, documento, pagina corrente,
        # ridisegna(), avvisa() e la barra di stato.
        self.finestra = finestra

    # =========================================================================
    # Menu del clic destro su una parola
    # =========================================================================

    def quando_menu_parola(self, parola: Parola, posizione: QPoint) -> None:
        menu = QMenu(self.finestra)
        azione_sottolinea = menu.addAction("Sottolinea e spiega…")
        azione_segnalibro = menu.addAction("Segnalibro qui")
        azione_segnalibro.setEnabled(False)  # arriva più avanti

        scelta = menu.exec(posizione)  # mostra il menu e aspetta la scelta (None = nessuna)
        if scelta is azione_sottolinea:
            self.sottolinea(parola)

    # =========================================================================
    # Sottolineature
    # =========================================================================

    def sottolinea(self, parola: Parola) -> None:
        """Chiede la spiegazione e sottolinea la parola."""
        if not self._modificabile():
            return
        archivio = self.finestra.archivio
        pagina = self.finestra.pagina

        # Se la parola è già sottolineata, il pop-up parte con la spiegazione esistente.
        esistente = next(
            (s for s in archivio.della_pagina(pagina)[0] if s.rett == parola.rett),
            None,
        )
        testo_iniziale = esistente.spiegazione if esistente else ""

        risposta = self.chiedi(f"«{parola.testo}»", testo_iniziale)
        if risposta is not None and risposta[0] == "salva":
            archivio.aggiungi_sottolineatura(pagina, parola.testo, parola.rett, risposta[1])
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

    def nuovo_pallino(self, lato: str, y: float, colore: Colore) -> None:
        """Chiede il testo e mette un pallino del colore scelto all'altezza y."""
        if not self._modificabile():
            return
        risposta = self.chiedi(self._titolo_pallino(colore.nome))
        if risposta is not None and risposta[0] == "salva":
            self.finestra.archivio.aggiungi_pallino(self.finestra.pagina, y, lato, colore.nome, risposta[1])
            self._salva_e_ridisegna()

    # =========================================================================
    # Aprire una nota esistente (clic sinistro su sottolineatura o pallino)
    # =========================================================================

    def apri_nota(self, id: str) -> None:
        """Mostra la nota nel pop-up; l'utente può modificarla o eliminarla."""
        if not self._modificabile():
            return
        archivio = self.finestra.archivio
        try:
            nota = archivio.trova(id)
        except KeyError:
            return  # nota sparita nel frattempo: non c'è niente da aprire

        if isinstance(nota, Sottolineatura):
            titolo, testo = f"«{nota.parola}»", nota.spiegazione
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
        return chiedi_nota(self.finestra, titolo, testo, eliminabile)

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
        """Salva su disco; se non ci riesce avvisa, ma la nota resta in memoria."""
        try:
            self.finestra.archivio.salva()
        except OSError as errore:
            self.finestra.avvisa(
                "Note non salvate",
                f"Non riesco a salvare le note:\n{errore}\n\n"
                "Le modifiche restano finché il programma è aperto; "
                "al prossimo cambiamento riproverò a salvare.",
            )
        self.finestra.ridisegna()


def _icona_colore(codice_colore: str) -> QIcon:
    """Un quadratino pieno del colore indicato, da mostrare accanto alle voci del menu."""
    quadratino = QPixmap(16, 16)
    quadratino.fill(QColor(codice_colore))
    return QIcon(quadratino)
