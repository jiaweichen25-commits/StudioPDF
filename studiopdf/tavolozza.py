"""I colori delle evidenziature, letti da config.json.

Ogni colore ha un nome, un codice esadecimale e un SIGNIFICATO scelto
dall'utente (es. rosso = "da ripassare"). Il file si può modificare a mano.

Un colore può anche avere "segna_pagina": true. Le evidenziature di quel
colore compaiono in «Segnati», in cima al pannello laterale: servono a
ritrovare i punti importanti con un clic. Di base è il viola.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

NOME_FILE_CONFIG = "config.json"


@dataclass
class Colore:
    nome: str  # es. "rosso": è ciò che viene salvato nelle note
    colore: str  # es. "#E5484D": come viene disegnato
    significato: str  # es. "da ripassare": cosa vuol dire per chi studia
    segna_pagina: bool = False  # True = le sue evidenziature vanno in «Segnati» (pannello laterale)


# I colori usati quando config.json non esiste o non si riesce a leggere.
TAVOLOZZA_BASE = [
    Colore("rosso", "#E5484D", "da ripassare"),
    Colore("blu", "#3E63DD", "sintesi"),
    Colore("verde", "#30A46C", "esempio"),
    Colore("viola", "#8E4EC6", "da ritrovare", segna_pagina=True),
]


def carica_tavolozza(cartella: Path) -> list[Colore]:
    """Legge la tavolozza da <cartella>/config.json.

    - Se il file non esiste: lo crea con TAVOLOZZA_BASE (se la cartella è
      scrivibile) e restituisce TAVOLOZZA_BASE.
    - Se il file esiste ma è illeggibile: restituisce TAVOLOZZA_BASE
      SENZA toccare il file (così l'utente può correggerlo a mano).
    """
    percorso = Path(cartella) / NOME_FILE_CONFIG

    if not percorso.exists():
        try:
            _scrivi_tavolozza(percorso, TAVOLOZZA_BASE)
        except OSError:
            pass  # cartella non scrivibile (es. Programmi): si usano i colori di base e basta
        return list(TAVOLOZZA_BASE)

    try:
        # "utf-8-sig" legge anche i file salvati "UTF-8 con BOM" (Blocco note, PowerShell).
        dati = json.loads(percorso.read_text(encoding="utf-8-sig"))
        tavolozza = [
            Colore(
                nome=str(voce["nome"]),
                colore=str(voce["colore"]),
                significato=str(voce["significato"]),
                # Facoltativo: se manca (o non è true/false) il colore non segna la pagina.
                segna_pagina=voce.get("segna_pagina") is True,
            )
            for voce in dati["tavolozza"]
        ]
    except (OSError, ValueError, KeyError, TypeError):
        # ValueError comprende anche gli errori di JSON e di codifica del testo.
        return list(TAVOLOZZA_BASE)

    # Una tavolozza vuota non servirebbe a niente: meglio quella di base.
    return tavolozza or list(TAVOLOZZA_BASE)


def trova_colore(tavolozza: list[Colore], nome: str) -> Colore | None:
    """Il colore con quel nome, oppure None se non è (più) nella tavolozza."""
    for colore in tavolozza:
        if colore.nome == nome:
            return colore
    return None


def _scrivi_tavolozza(percorso: Path, tavolozza: list[Colore]) -> None:
    dati = {"tavolozza": [_voce(colore) for colore in tavolozza]}
    percorso.write_text(json.dumps(dati, ensure_ascii=False, indent=2), encoding="utf-8")


def _voce(colore: Colore) -> dict:
    """Un colore come voce di config.json. "segna_pagina" si scrive solo se è vero,
    così le voci degli altri colori restano corte e facili da leggere."""
    voce = asdict(colore)
    if not colore.segna_pagina:
        del voce["segna_pagina"]
    return voce
