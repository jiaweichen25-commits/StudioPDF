"""Dove sta il file delle note di un libro, e spostarlo quando cambia la scelta.

Le note di un libro possono stare in due posti (⚙ Config → Percorsi):

    accanto al PDF                     Analisi1.pdf  ->  Analisi1.pdf.note.json
    nella «cartella delle note»        Note/Analisi1 [3fa91c0d].note.json

Nella cartella delle note il nome contiene l'«impronta» del PDF (8 caratteri
calcolati dal suo contenuto): così due libri diversi con lo stesso nome (es. due
Lezione1.pdf di corsi diversi) non si mescolano, e se il PDF viene spostato o
rinominato le sue note si ritrovano lo stesso.

Quando la scelta cambia, all'apertura del libro le note già scritte vengono
SPOSTATE nella posizione giusta (vedi trova_posizione). Non si cancella mai niente.

Questo modulo non usa PySide6: si può provare senza interfaccia.
"""

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

ESTENSIONE_NOTE = ".note.json"

# Per l'impronta si leggono solo l'inizio e la fine del PDF: è veloce anche
# con libri da centinaia di MB, e basta a distinguere due PDF diversi
# (alla fine di ogni PDF c'è un indice che cambia da file a file).
BLOCCO_IMPRONTA = 1024 * 1024  # 1 MiB
LUNGHEZZA_IMPRONTA = 8


@dataclass
class PosizioneNote:
    """Dove leggere e scrivere le note di un libro, e cosa è successo per trovarle."""

    percorso: Path  # il file delle note da usare (può non esistere ancora)
    sola_lettura: bool = False  # True se la cartella delle note non è raggiungibile
    spostate_da: Path | None = None  # se le note sono state spostate, da dove
    altre_note: Path | None = None  # un ALTRO file di note di questo libro, non usato (da segnalare)
    errore_spostamento: str | None = None  # lo spostamento non è riuscito: note usate dove sono


def impronta(pdf: Path) -> str:
    """8 caratteri esadecimali calcolati dal contenuto del PDF (non dal nome né dalla cartella).

    Si mescolano (con SHA-256) la dimensione del file, il suo primo MiB e il suo ultimo MiB.
    """
    pdf = Path(pdf)
    dimensione = pdf.stat().st_size
    mescolatore = hashlib.sha256(str(dimensione).encode("ascii"))
    with pdf.open("rb") as file:
        mescolatore.update(file.read(BLOCCO_IMPRONTA))  # l'inizio
        file.seek(max(0, dimensione - BLOCCO_IMPRONTA))
        mescolatore.update(file.read(BLOCCO_IMPRONTA))  # la fine
    return mescolatore.hexdigest()[:LUNGHEZZA_IMPRONTA]


def accanto_al_pdf(pdf: Path) -> Path:
    """Il file delle note accanto al PDF: "<nome>.pdf.note.json"."""
    return Path(str(pdf) + ESTENSIONE_NOTE)


def cerca_nella_cartella(cartella: Path, impronta_pdf: str) -> Path | None:
    """Il file delle note con questa impronta nella cartella, qualunque sia il nome del libro.

    Si confronta la FINE del nome ("[3fa91c0d].note.json") invece di usare glob(),
    perché per glob le parentesi quadre hanno un significato speciale.
    """
    finale = f"[{impronta_pdf}]{ESTENSIONE_NOTE}"
    for file in sorted(cartella.iterdir()):
        if file.is_file() and file.name.endswith(finale):
            return file
    return None


def trova_posizione(pdf: Path, cartella_note: str, cartella_precedente: str) -> PosizioneNote:
    """Decide quale file delle note usare per questo libro, spostandolo se serve.

    cartella_note       = la cartella scelta ("" = accanto al PDF)
    cartella_precedente = la cartella delle note usata prima ("" = nessuna)

    Le regole (vedi la spec v8, §4):
    1. se nella posizione giusta c'è già un file -> si usa (e si segnala un eventuale altro file);
    2. altrimenti, se c'è un file in un'altra posizione conosciuta -> lo si SPOSTA lì;
    3. altrimenti il libro non ha ancora note: si useranno nella posizione giusta.
    """
    pdf = Path(pdf)

    # --- La posizione giusta ---
    if cartella_note:
        cartella = Path(cartella_note)
        if not cartella.is_dir():
            # Chiavetta staccata, cartella cancellata...: niente spostamenti, note in sola lettura.
            return PosizioneNote(percorso=cartella / f"{pdf.stem}{ESTENSIONE_NOTE}", sola_lettura=True)
        impronta_pdf = impronta(pdf)
        giusta = cerca_nella_cartella(cartella, impronta_pdf) or cartella / f"{pdf.stem} [{impronta_pdf}]{ESTENSIONE_NOTE}"
    else:
        giusta = accanto_al_pdf(pdf)
        impronta_pdf = None  # calcolata solo se serve (vedi sotto)

    # --- Le altre posizioni in cui le note potrebbero essere rimaste ---
    altre: list[Path] = []
    if giusta != accanto_al_pdf(pdf):
        altre.append(accanto_al_pdf(pdf))
    if cartella_precedente and cartella_precedente != cartella_note and Path(cartella_precedente).is_dir():
        impronta_pdf = impronta_pdf or impronta(pdf)
        trovata = cerca_nella_cartella(Path(cartella_precedente), impronta_pdf)
        if trovata is not None:
            altre.append(trovata)
    esistenti = [percorso for percorso in altre if percorso.exists()]

    # 1. Il file è già al posto giusto.
    if giusta.exists():
        return PosizioneNote(percorso=giusta, altre_note=esistenti[0] if esistenti else None)

    # 2. Il file è rimasto in un altro posto: lo si sposta.
    if esistenti:
        origine = esistenti[0]
        try:
            # shutil.move funziona anche tra dischi diversi (copia e poi cancella l'originale).
            shutil.move(origine, giusta)
        except OSError as errore:
            return PosizioneNote(percorso=origine, errore_spostamento=str(errore))
        return PosizioneNote(percorso=giusta, spostate_da=origine)

    # 3. Nessuna nota: verranno create qui.
    return PosizioneNote(percorso=giusta)
