"""I colori dei pallini, letti da config.json.

Ogni colore ha un nome, un codice esadecimale e un SIGNIFICATO scelto
dall'utente (es. rosso = "da ripassare"). Il file si può modificare a mano.
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


# I colori usati quando config.json non esiste o non si riesce a leggere.
TAVOLOZZA_BASE = [
    Colore("rosso", "#E5484D", "da ripassare"),
    Colore("blu", "#3E63DD", "sintesi"),
    Colore("verde", "#30A46C", "esempio"),
    Colore("giallo", "#F5D90A", "dubbio"),
]


def carica_tavolozza(cartella: Path) -> list[Colore]:
    """Legge la tavolozza da <cartella>/config.json.

    - Se il file non esiste: lo crea con TAVOLOZZA_BASE e la restituisce.
    - Se il file esiste ma è illeggibile: restituisce TAVOLOZZA_BASE
      SENZA toccare il file (così l'utente può correggerlo a mano).
    """
    percorso = Path(cartella) / NOME_FILE_CONFIG

    if not percorso.exists():
        _scrivi_tavolozza(percorso, TAVOLOZZA_BASE)
        return list(TAVOLOZZA_BASE)

    try:
        dati = json.loads(percorso.read_text(encoding="utf-8"))
        tavolozza = [
            Colore(nome=str(voce["nome"]), colore=str(voce["colore"]), significato=str(voce["significato"]))
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
    dati = {"tavolozza": [asdict(colore) for colore in tavolozza]}
    percorso.write_text(json.dumps(dati, ensure_ascii=False, indent=2), encoding="utf-8")
