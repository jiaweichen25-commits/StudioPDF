"""Le impostazioni del programma: cartella dei libri, tasti e interruttori.

Stanno in config.json (lo stesso file della tavolozza), in tre sezioni:

    "percorsi": {"cartella_libri": "C:/Libri", "ultimo_libro": "C:/Libri/Analisi1.pdf",
                 "cartella_note": "", "cartella_note_precedente": ""}
    "tasti":    {"pagina_successiva": ["Right", "PgDown"], ...}
    "opzioni":  {"frecce_laterali": true, "anteprima_note": true, "pannello_laterale": true}

Regole importanti:
- un valore mancante o sbagliato prende quello predefinito (così un
  config.json vecchio, con solo i colori, funziona);
- salvando si aggiornano SOLO queste tre sezioni: la tavolozza e qualsiasi
  altra cosa scritta a mano restano identiche;
- un config.json illeggibile non viene mai sovrascritto.

Questo modulo non usa PySide6: i tasti sono semplici stringhe nel formato di
Qt (es. "Ctrl+O", "PgDown", "D"); "" significa "nessun tasto".
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from studiopdf.tavolozza import NOME_FILE_CONFIG, Colore

# Ogni azione ha DUE caselle per i tasti (come negli emulatori tipo melonDS).
TASTI_PER_AZIONE = 2

# Le azioni che esistono sempre: (chiave, descrizione mostrata all'utente).
AZIONI_FISSE: list[tuple[str, str]] = [
    ("pagina_precedente", "Pagina precedente"),
    ("pagina_successiva", "Pagina successiva"),
    ("ingrandisci", "Ingrandisci"),
    ("rimpicciolisci", "Rimpicciolisci"),
    ("apri_libro", "Apri libro"),
    ("apri_ultimo_libro", "Apri l'ultimo libro"),
    ("chiudi_programma", "Chiudi programma"),
    ("pannello_laterale", "Mostra/nascondi il pannello laterale"),
    # Questa vale solo DENTRO il pop-up della nota (vedi interfaccia/popup.py),
    # non nella finestra principale.
    ("salva_nota", "Salva nota (nel pop-up)"),
]

# Il tasto per salvare la nota nel pop-up: Invio, sia quello grande ("Return")
# sia quello del tastierino numerico ("Enter"). Con Shift+Invio si va a capo.
TASTI_SALVA_NOTA = ["Return", "Enter"]

# I tasti predefiniti delle azioni fisse.
_TASTI_FISSI: dict[str, list[str]] = {
    "pagina_precedente": ["Left", "PgUp"],
    "pagina_successiva": ["Right", "PgDown"],
    "ingrandisci": ["+", "Ctrl++"],
    "rimpicciolisci": ["-", "Ctrl+-"],
    "apri_libro": ["Ctrl+O", ""],
    "apri_ultimo_libro": ["Ctrl+Shift+O", ""],  # vicino a Ctrl+O, che apre un libro qualsiasi
    "chiudi_programma": ["Ctrl+W", ""],
    "pannello_laterale": ["F4", ""],  # come in Firefox
    "salva_nota": TASTI_SALVA_NOTA,
}

# Per ogni colore della tavolozza c'è l'azione "colore_<nome>": il suo tasto
# sceglie quel colore nel menu che compare dopo aver selezionato una frase.
PREFISSO_COLORE = "colore_"

# Prima della v9 c'erano i pallini nel margine e le azioni si chiamavano
# "pallino_<nome>": i tasti salvati con quel nome vengono ancora letti.
PREFISSO_VECCHIO_PALLINO = "pallino_"

# Ai primi nove colori vanno i tasti da 1 a 9.
MASSIMO_TASTI_NUMERICI = 9


class ErroreImpostazioni(Exception):
    """config.json esiste ma non si riesce a leggere: per non rovinarlo non lo si sovrascrive."""


@dataclass
class Impostazioni:
    cartella_libri: str = ""  # da dove parte "Apri…" ("" = posizione predefinita di Windows)
    ultimo_libro: str = ""  # percorso dell'ultimo PDF aperto ("" = nessuno ancora)
    cartella_note: str = ""  # dove salvare le note ("" = accanto a ogni PDF)
    # La cartella delle note usata PRIMA dell'ultima modifica: serve per ritrovare
    # (e spostare) le note rimaste lì. Vedi posizione_note.trova_posizione.
    cartella_note_precedente: str = ""
    tasti: dict[str, list[str]] = field(default_factory=dict)  # azione -> [tasto 1, tasto 2]
    frecce_laterali: bool = True  # frecce ‹ › ai lati della pagina
    anteprima_note: bool = True  # schedina passando il mouse su una nota
    pannello_laterale: bool = True  # pannello a sinistra con «Segnati» e l'indice


# =============================================================================
# Azioni e tasti predefiniti
# =============================================================================


def azioni(tavolozza: list[Colore]) -> list[tuple[str, str]]:
    """Tutte le azioni a cui si può dare un tasto: quelle fisse più una per colore."""
    colori = [
        (PREFISSO_COLORE + colore.nome, f"Evidenzia {colore.nome} — {colore.significato}")
        for colore in tavolozza
    ]
    return AZIONI_FISSE + colori


def tasti_predefiniti(tavolozza: list[Colore]) -> dict[str, list[str]]:
    """I tasti di partenza per ogni azione (una copia nuova a ogni chiamata)."""
    tasti = {azione: list(coppia) for azione, coppia in _TASTI_FISSI.items()}
    for posizione, colore in enumerate(tavolozza):
        numero = str(posizione + 1) if posizione < MASSIMO_TASTI_NUMERICI else ""
        tasti[PREFISSO_COLORE + colore.nome] = [numero, ""]
    return tasti


# =============================================================================
# Lettura
# =============================================================================


def carica_impostazioni(cartella: Path, tavolozza: list[Colore]) -> Impostazioni:
    """Legge le impostazioni da <cartella>/config.json, completandole con i valori predefiniti."""
    dati = _leggi_config(Path(cartella) / NOME_FILE_CONFIG)
    if dati is None:  # file mancante o illeggibile
        dati = {}

    percorsi = _sezione(dati, "percorsi")
    tasti_salvati = _sezione(dati, "tasti")
    opzioni = _sezione(dati, "opzioni")

    # Tasti, in due passaggi:
    # 1) quelli salvati (se validi) hanno la precedenza;
    predefiniti = tasti_predefiniti(tavolozza)
    tasti: dict[str, list[str]] = {}
    for azione in predefiniti:
        valore = tasti_salvati.get(azione)
        if valore is None and azione.startswith(PREFISSO_COLORE):
            # config.json di prima della v9: "pallino_rosso" invece di "colore_rosso".
            valore = tasti_salvati.get(PREFISSO_VECCHIO_PALLINO + azione[len(PREFISSO_COLORE):])
        if _tasti_validi(valore):
            # Completa fino a due caselle: ["D"] -> ["D", ""]
            tasti[azione] = (list(valore) + [""] * TASTI_PER_AZIONE)[:TASTI_PER_AZIONE]

    # 2) le azioni senza tasti salvati (es. un colore appena aggiunto alla tavolozza)
    #    ricevono i predefiniti, ma SOLO se quei tasti sono ancora liberi: altrimenti
    #    due azioni avrebbero lo stesso tasto e nessuna delle due funzionerebbe.
    occupati = {tasto.upper() for coppia in tasti.values() for tasto in coppia if tasto.strip()}
    for azione, coppia in predefiniti.items():
        if azione in tasti:
            continue
        liberi = [tasto if tasto and tasto.upper() not in occupati else "" for tasto in coppia]
        occupati.update(tasto.upper() for tasto in liberi if tasto)
        tasti[azione] = liberi

    tasti = {azione: tasti[azione] for azione in predefiniti}  # stesso ordine delle azioni

    return Impostazioni(
        cartella_libri=_testo_o(percorsi.get("cartella_libri"), ""),
        ultimo_libro=_testo_o(percorsi.get("ultimo_libro"), ""),
        cartella_note=_testo_o(percorsi.get("cartella_note"), ""),
        cartella_note_precedente=_testo_o(percorsi.get("cartella_note_precedente"), ""),
        tasti=tasti,
        frecce_laterali=_vero_falso_o(opzioni.get("frecce_laterali"), True),
        anteprima_note=_vero_falso_o(opzioni.get("anteprima_note"), True),
        pannello_laterale=_vero_falso_o(opzioni.get("pannello_laterale"), True),
    )


def _leggi_config(percorso: Path) -> dict | None:
    """Il contenuto di config.json come dizionario; None se manca o è illeggibile."""
    if not percorso.exists():
        return None
    try:
        # "utf-8-sig" legge anche i file salvati "UTF-8 con BOM" (Blocco note, PowerShell).
        dati = json.loads(percorso.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return dati if isinstance(dati, dict) else None


def _sezione(dati: dict, nome: str) -> dict:
    """Una sezione del file (es. "tasti"); un dizionario vuoto se manca o non è un dizionario."""
    valore = dati.get(nome)
    return valore if isinstance(valore, dict) else {}


def _tasti_validi(valore) -> bool:
    """Una lista di 1 o 2 stringhe, es. ["D"] o ["Right", "PgDown"]."""
    return (
        isinstance(valore, list)
        and 1 <= len(valore) <= TASTI_PER_AZIONE
        and all(isinstance(tasto, str) for tasto in valore)
    )


def _testo_o(valore, predefinito: str) -> str:
    return valore if isinstance(valore, str) else predefinito


def _vero_falso_o(valore, predefinito: bool) -> bool:
    return valore if isinstance(valore, bool) else predefinito


# =============================================================================
# Scrittura
# =============================================================================


def salva_impostazioni(cartella: Path, impostazioni: Impostazioni) -> None:
    """Scrive le impostazioni in config.json, lasciando intatto tutto il resto del file.

    Solleva ErroreImpostazioni se config.json esiste ma è illeggibile (per non
    sovrascriverlo) e OSError se non si riesce a scrivere.
    """
    percorso = Path(cartella) / NOME_FILE_CONFIG

    dati = _leggi_config(percorso)
    if dati is None:
        if percorso.exists():
            raise ErroreImpostazioni(
                f"{percorso.name} non si riesce a leggere: correggilo (o cancellalo) prima di salvare le impostazioni."
            )
        dati = {}

    # Si aggiornano solo le nostre tre sezioni.
    dati["percorsi"] = {
        "cartella_libri": impostazioni.cartella_libri,
        "ultimo_libro": impostazioni.ultimo_libro,
        "cartella_note": impostazioni.cartella_note,
        "cartella_note_precedente": impostazioni.cartella_note_precedente,
    }
    dati["tasti"] = impostazioni.tasti
    dati["opzioni"] = {
        "frecce_laterali": impostazioni.frecce_laterali,
        "anteprima_note": impostazioni.anteprima_note,
        "pannello_laterale": impostazioni.pannello_laterale,
    }

    # Come per le note: prima un file temporaneo, poi la sostituzione in un colpo solo.
    temporaneo = Path(f"{percorso}.tmp")
    try:
        temporaneo.write_text(json.dumps(dati, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporaneo, percorso)
    except OSError:
        temporaneo.unlink(missing_ok=True)
        raise


# =============================================================================
# Conflitti
# =============================================================================


def trova_conflitti(tasti: dict[str, list[str]]) -> dict[str, list[str]]:
    """I tasti usati più di una volta: {TASTO: [azioni che lo usano]}.

    Conta anche lo stesso tasto messo in entrambe le caselle di un'azione
    (in quel caso l'azione compare due volte nell'elenco).

    Il confronto ignora maiuscole e minuscole ("d" e "D" sono lo stesso tasto).
    Le caselle vuote non contano.
    """
    usi: dict[str, list[str]] = {}
    for azione, coppia in tasti.items():
        for tasto in coppia:
            if tasto.strip():
                usi.setdefault(tasto.strip().upper(), []).append(azione)
    return {tasto: elenco for tasto, elenco in usi.items() if len(elenco) > 1}
