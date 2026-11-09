"""Le note di un libro e il loro file su disco.

Per ogni PDF le note stanno in un file accanto, con lo stesso nome più
".note.json":  Analisi1.pdf  ->  Analisi1.pdf.note.json

Il file è testo JSON leggibile (e modificabile a mano). Questo modulo:
- lo legge (Archivio.carica) e lo scrive (Archivio.salva);
- offre le operazioni sulle note: aggiungi, modifica, elimina, cerca;
- protegge i dati: un file illeggibile non viene mai sovrascritto, e il
  salvataggio passa da un file temporaneo per non lasciare file a metà.
"""

import json
import os
import uuid
from dataclasses import asdict
from datetime import date
from pathlib import Path

from studiopdf.note import Nota, Pallino, Rett, Segnalibro, Sottolineatura

# Versione del formato del file. Se un giorno il formato cambia, si alza
# questo numero: un programma vecchio riconoscerà un file "dal futuro".
#   1 = una sottolineatura è UNA parola:  "parola" + "rett"
#   2 = una sottolineatura è una FRASE:   "testo" + "rettangoli" (uno per riga)
# I file della versione 1 si leggono ancora; si salva sempre nella versione 2.
VERSIONE = 2

ESTENSIONE_NOTE = ".note.json"


class Archivio:
    """Tutte le note di un libro, più il percorso del file in cui stanno."""

    def __init__(self, percorso_note: Path) -> None:
        # Di solito non si crea un Archivio così, ma con Archivio.carica(pdf).
        self.percorso_note = percorso_note
        self.segnalibro: Segnalibro | None = None
        self.sottolineature: list[Sottolineatura] = []
        self.pallini: list[Pallino] = []

        # Se True non si salva mai, per non rovinare dati sul disco. Succede se:
        #   "versione_futura"  -> il file è di una versione più nuova del programma;
        #   "file_illeggibile" -> il file è rotto ma non si è riusciti a spostarlo.
        self.sola_lettura = False
        self.motivo_sola_lettura: str | None = None

        # Se il file era illeggibile, qui c'è il nuovo nome con cui è stato messo da parte.
        self.file_rotto: Path | None = None

    # =========================================================================
    # Lettura
    # =========================================================================

    @classmethod
    def carica(cls, percorso_pdf: str | Path) -> "Archivio":
        """Carica le note del PDF indicato (o un archivio vuoto se non ce ne sono)."""
        archivio = cls(Path(str(percorso_pdf) + ESTENSIONE_NOTE))

        if not archivio.percorso_note.exists():
            return archivio  # libro senza note: archivio vuoto

        try:
            # "utf-8-sig" legge anche i file salvati "UTF-8 con BOM" (Blocco note, PowerShell).
            dati = json.loads(archivio.percorso_note.read_text(encoding="utf-8-sig"))
            versione = dati["versione"]
            if not isinstance(versione, int):
                raise ValueError("versione non valida")

            if versione > VERSIONE:
                # File scritto da un programma più nuovo: non lo tocchiamo.
                archivio.sola_lettura = True
                archivio.motivo_sola_lettura = "versione_futura"
                return archivio

            archivio._leggi_dati(dati, versione)
        except (ValueError, KeyError, TypeError):
            # ValueError comprende JSON non valido e testo non UTF-8.
            # Il file non si capisce: lo mettiamo da parte e ripartiamo vuoti.
            archivio._ripristina_vuoto()
            try:
                archivio.file_rotto = archivio._metti_da_parte_file_rotto()
            except OSError:
                # Non si riesce nemmeno a spostarlo (cartella protetta...): allora
                # non si salva niente, così il file rotto resta com'è.
                archivio.sola_lettura = True
                archivio.motivo_sola_lettura = "file_illeggibile"

        return archivio

    def _leggi_dati(self, dati: dict, versione: int) -> None:
        """Converte il dizionario letto dal JSON in oggetti Python.

        I costruttori int(), float(), str() sollevano un errore se un valore
        è del tipo sbagliato: così un file "strano" viene riconosciuto come rotto.
        """
        segnalibro = dati["segnalibro"]
        if segnalibro is not None:
            self.segnalibro = Segnalibro(
                pagina=int(segnalibro["pagina"]),
                parola=str(segnalibro["parola"]),
                rett=_leggi_rett(segnalibro["rett"]),
            )

        self.sottolineature = [_leggi_sottolineatura(voce, versione) for voce in dati["sottolineature"]]

        self.pallini = [
            Pallino(
                id=str(voce["id"]),
                pagina=int(voce["pagina"]),
                y=float(voce["y"]),
                lato=_leggi_lato(voce["lato"]),
                colore=str(voce["colore"]),
                testo=str(voce["testo"]),
            )
            for voce in dati["pallini"]
        ]

    def _ripristina_vuoto(self) -> None:
        """Svuota tutto (serve se la lettura si è interrotta a metà)."""
        self.segnalibro = None
        self.sottolineature = []
        self.pallini = []

    def _metti_da_parte_file_rotto(self) -> Path:
        """Rinomina il file illeggibile in "<nome>.rotto-AAAA-MM-GG" (o -2, -3... se esiste già).

        Il file viene SPOSTATO, non copiato: così il nome originale si libera
        e il contenuto vecchio non rischia mai di essere sovrascritto.
        """
        base = f"{self.percorso_note}.rotto-{date.today().isoformat()}"
        destinazione = Path(base)
        numero = 2
        while destinazione.exists():
            destinazione = Path(f"{base}-{numero}")
            numero += 1
        self.percorso_note.rename(destinazione)
        return destinazione

    # =========================================================================
    # Scrittura
    # =========================================================================

    def salva(self) -> None:
        """Scrive le note su disco.

        - In sola lettura non scrive niente.
        - Se non ci sono note e il file non esiste ancora, non lo crea.
        - Scrive prima "<file>.tmp" e poi lo mette al posto dell'originale con
          os.replace: se il PC si spegne a metà, l'originale resta intatto.
        Può sollevare OSError (disco pieno, cartella protetta...): chi chiama
        decide come avvisare l'utente.
        """
        if self.sola_lettura:
            return
        if not self.percorso_note.exists() and self._e_vuoto():
            return

        dati = {
            "versione": VERSIONE,
            "segnalibro": asdict(self.segnalibro) if self.segnalibro else None,
            "sottolineature": [asdict(s) for s in self.sottolineature],
            "pallini": [asdict(p) for p in self.pallini],
        }
        # ensure_ascii=False scrive le lettere accentate così come sono ("perché"),
        # invece del codice di escape ("perch\u00e9").
        testo = json.dumps(dati, ensure_ascii=False, indent=2)

        temporaneo = Path(f"{self.percorso_note}.tmp")
        try:
            temporaneo.write_text(testo, encoding="utf-8")
            os.replace(temporaneo, self.percorso_note)
        except OSError:
            temporaneo.unlink(missing_ok=True)  # niente file temporanei lasciati in giro
            raise

    def _e_vuoto(self) -> bool:
        return self.segnalibro is None and not self.sottolineature and not self.pallini

    # =========================================================================
    # Operazioni sulle note
    # =========================================================================

    def aggiungi_sottolineatura(
        self, pagina: int, testo: str, rettangoli: list[Rett], spiegazione: str
    ) -> Sottolineatura:
        """Sottolinea una frase (rettangoli = uno per riga). Crea sempre una nota nuova.

        Non controlla le sovrapposizioni: chi chiama deve prima usare
        sottolineatura_sovrapposta() e decidere cosa fare.
        """
        nuova = Sottolineatura(_nuovo_id(), pagina, testo, list(rettangoli), spiegazione)
        self.sottolineature.append(nuova)
        return nuova

    def sottolineatura_sovrapposta(self, pagina: int, rettangoli_parole: list[Rett]) -> Sottolineatura | None:
        """La sottolineatura già esistente che contiene una di queste parole, oppure None.

        rettangoli_parole = i rettangoli delle singole parole che si vogliono sottolineare.
        Una parola "cade" in una sottolineatura se il suo CENTRO sta dentro uno dei
        rettangoli della sottolineatura. Si usa il centro, e non il bordo, perché i
        rettangoli di due righe vicine possono toccarsi di qualche decimo di punto.
        """
        for esistente in self.sottolineature:
            if esistente.pagina != pagina:
                continue
            for rett_parola in rettangoli_parole:
                if any(_centro_dentro(rett_parola, rett) for rett in esistente.rettangoli):
                    return esistente
        return None

    def aggiungi_pallino(self, pagina: int, y: float, lato: str, colore: str, testo: str) -> Pallino:
        nuovo = Pallino(_nuovo_id(), pagina, y, lato, colore, testo)
        self.pallini.append(nuovo)
        return nuovo

    def imposta_segnalibro(self, pagina: int, parola: str, rett: Rett) -> None:
        """Mette il segnalibro su una parola (sostituisce quello precedente)."""
        self.segnalibro = Segnalibro(pagina, parola, rett)

    def trova(self, id: str) -> Nota:
        """La sottolineatura o il pallino con questo id. KeyError se non esiste."""
        for nota in [*self.sottolineature, *self.pallini]:
            if nota.id == id:
                return nota
        raise KeyError(id)

    def modifica(self, id: str, testo: str) -> None:
        """Cambia il testo di una nota (la spiegazione o il testo del pallino)."""
        nota = self.trova(id)
        if isinstance(nota, Sottolineatura):
            nota.spiegazione = testo
        else:
            nota.testo = testo

    def elimina(self, id: str) -> None:
        nota = self.trova(id)  # solleva KeyError se non c'è
        if isinstance(nota, Sottolineatura):
            self.sottolineature.remove(nota)
        else:
            self.pallini.remove(nota)

    def della_pagina(self, pagina: int) -> tuple[list[Sottolineatura], list[Pallino]]:
        """Le note di una sola pagina: (sottolineature, pallini)."""
        sottolineature = [s for s in self.sottolineature if s.pagina == pagina]
        pallini = [p for p in self.pallini if p.pagina == pagina]
        return sottolineature, pallini

    def pagina_di_partenza(self, numero_pagine: int) -> int:
        """Da che pagina aprire il libro: quella del segnalibro, se esiste ancora, altrimenti la 1."""
        if self.segnalibro and 1 <= self.segnalibro.pagina <= numero_pagine:
            return self.segnalibro.pagina
        return 1


# =============================================================================
# Funzioni di aiuto (fuori dalla classe perché non usano "self")
# =============================================================================


def _nuovo_id() -> str:
    """Un identificativo casuale di 8 caratteri esadecimali, es. "a3f9c210"."""
    return uuid.uuid4().hex[:8]


def _leggi_sottolineatura(voce: dict, versione: int) -> Sottolineatura:
    """Una sottolineatura letta dal JSON, in uno dei due formati.

    Versione 1 (vecchia): una parola sola  -> {"parola": ..., "rett": [...]}
    Versione 2 (attuale): una frase        -> {"testo": ..., "rettangoli": [[...], ...]}
    Una parola della versione 1 diventa una frase di una parola, su una riga.
    """
    if versione == 1:
        testo = str(voce["parola"])
        rettangoli = [_leggi_rett(voce["rett"])]
    else:
        testo = str(voce["testo"])
        rettangoli = [_leggi_rett(rett) for rett in voce["rettangoli"]]
        if not rettangoli:
            raise ValueError("una sottolineatura deve avere almeno un rettangolo")

    return Sottolineatura(
        id=str(voce["id"]),
        pagina=int(voce["pagina"]),
        testo=testo,
        rettangoli=rettangoli,
        spiegazione=str(voce["spiegazione"]),
    )


def _centro_dentro(piccolo: Rett, grande: Rett) -> bool:
    """Il centro del rettangolo "piccolo" sta dentro il rettangolo "grande"?"""
    x0, y0, x1, y1 = piccolo
    centro_x, centro_y = (x0 + x1) / 2, (y0 + y1) / 2
    g0, h0, g1, h1 = grande
    return g0 <= centro_x <= g1 and h0 <= centro_y <= h1


def _leggi_rett(valore) -> Rett:
    """Converte la lista JSON [x0, y0, x1, y1] in una tupla di 4 numeri."""
    numeri = tuple(float(v) for v in valore)
    if len(numeri) != 4:
        raise ValueError("un rettangolo deve avere 4 numeri")
    return numeri


def _leggi_lato(valore) -> str:
    if valore not in ("sx", "dx"):
        raise ValueError(f"lato non valido: {valore!r}")
    return valore
