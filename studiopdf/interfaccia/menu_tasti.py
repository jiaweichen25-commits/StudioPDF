"""Un menu in cui alcune voci si scelgono anche premendo un tasto (es. 1, 2, 3).

Serve al menu che compare dopo aver selezionato una frase: con il menu aperto,
premere il tasto di un colore (in ⚙ Config → Keybinding: «Evidenzia <colore>»)
equivale a cliccare la voce «Evidenzia <colore>».

Come si usa
-----------
    menu = MenuConTasti(genitore)
    azione = menu.addAction("Evidenzia rosso — da ripassare")
    menu.collega_tasti(azione, ["1", ""])     # come i tasti nelle impostazioni
    scelta = menu.exec(posizione)              # premendo 1 -> scelta è "azione"
"""

from collections.abc import Sequence

from PySide6.QtCore import QKeyCombination, Qt
from PySide6.QtGui import QAction, QKeyEvent, QKeySequence
from PySide6.QtWidgets import QMenu


class MenuConTasti(QMenu):
    def __init__(self, genitore=None) -> None:
        super().__init__(genitore)
        # Coppie (tasto, voce del menu che quel tasto sceglie).
        self._tasti: list[tuple[QKeySequence, QAction]] = []

    def collega_tasti(self, azione: QAction, tasti: Sequence[str]) -> None:
        """Premendo uno di questi tasti (stringhe come "1" o "Ctrl+R") si sceglie l'azione.

        Le caselle vuote ("") non contano.
        """
        for tasto in tasti:
            if tasto.strip():
                self._tasti.append((QKeySequence(tasto), azione))

    def keyPressEvent(self, evento: QKeyEvent) -> None:
        """Ogni tasto premuto con il menu aperto passa da qui."""
        azione = self._azione_del_tasto(evento)
        if azione is None:
            super().keyPressEvent(evento)  # tasto normale: frecce, Esc... come in ogni menu
            return

        # Trucco: si rende "attiva" la voce (come se il mouse ci fosse sopra) e poi
        # si finge un Invio. Così è QMenu stesso a sceglierla, chiudersi e far
        # restituire a exec() proprio questa voce, esattamente come con un clic.
        self.setActiveAction(azione)
        invio = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        super().keyPressEvent(invio)

    def _azione_del_tasto(self, evento: QKeyEvent) -> QAction | None:
        """La voce collegata al tasto premuto, oppure None."""
        # I tasti del tastierino numerico arrivano con il modificatore "tastierino":
        # lo togliamo, così il 2 del tastierino vale come il 2 normale.
        modificatori = evento.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        premuto = QKeySequence(QKeyCombination(modificatori, Qt.Key(evento.key())))
        for tasto, azione in self._tasti:
            if tasto == premuto:
                return azione
        return None
