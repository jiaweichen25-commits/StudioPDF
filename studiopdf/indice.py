"""L'indice del libro e i «Segnati»: i calcoli dietro al pannello laterale.

L'INDICE è quello scritto dentro il PDF (i "segnalibri" del PDF, quelli che Firefox
chiama «Document outline»): un elenco di voci, ognuna con
- un LIVELLO (1 = capitolo, 2 = sezione, 3 = sottosezione…),
- un TITOLO,
- la PAGINA da cui inizia (None se la voce non porta a nessuna pagina valida).

Le voci sono in ordine di lettura, e il livello dice chi sta "dentro" chi:

    1 Cap 1         p. 1
    2   1.1         p. 2      <- dentro Cap 1
    3     1.1.1     p. 3      <- dentro 1.1
    2   1.2         p. 5
    1 Cap 2         p. 8

I SEGNATI sono le evidenziature dei colori che hanno "segna_pagina" (di base il viola).

Questo modulo non usa PySide6: si può provare senza interfaccia.
"""

from dataclasses import dataclass

from studiopdf.note import Evidenziatura
from studiopdf.tavolozza import Colore


@dataclass(frozen=True)
class VoceIndice:
    livello: int  # 1 = capitolo, 2 = sezione, ...
    titolo: str
    pagina: int | None  # da 1; None = la voce non porta a nessuna pagina


def voce_corrente(voci: list[VoceIndice], pagina: int) -> int | None:
    """La posizione (nell'elenco) della voce in cui si trova la pagina; None se nessuna.

    È l'ULTIMA voce, in ordine di lettura, già iniziata a questa pagina: così se
    si è a pagina 4 e 1.1.1 inizia a pagina 3, si è in 1.1.1 (la voce più precisa).
    """
    corrente = None
    for posizione, voce in enumerate(voci):
        if voce.pagina is not None and voce.pagina <= pagina:
            corrente = posizione
    return corrente


def fine_voce(voci: list[VoceIndice], posizione: int) -> int | None:
    """La pagina in cui la voce FINISCE (esclusa); None = fino alla fine del libro.

    Una voce finisce dove inizia la voce successiva dello stesso livello o di un
    livello più alto (più piccolo): 1.1 finisce dove inizia 1.2 oppure Cap 2.
    """
    livello = voci[posizione].livello
    for voce in voci[posizione + 1 :]:
        if voce.livello <= livello and voce.pagina is not None:
            return voce.pagina
    return None


def voci_con_segni(voci: list[VoceIndice], pagine_segnate: set[int]) -> set[int]:
    """Le posizioni delle voci che contengono almeno una pagina segnata.

    Accanto a queste voci il pannello mostra un pallino viola.
    """
    risultato = set()
    for posizione, voce in enumerate(voci):
        if voce.pagina is None:
            continue
        fine = fine_voce(voci, posizione)
        if any(pagina >= voce.pagina and (fine is None or pagina < fine) for pagina in pagine_segnate):
            risultato.add(posizione)
    return risultato


def segni(evidenziature: list[Evidenziatura], tavolozza: list[Colore]) -> list[Evidenziatura]:
    """Le evidenziature che vanno in «Segnati», in ordine di lettura.

    Sono quelle dei colori con "segna_pagina" (un colore tolto dalla tavolozza non
    segna più niente). Ordine: per pagina, e nella stessa pagina dall'alto in basso.
    """
    colori_che_segnano = {colore.nome for colore in tavolozza if colore.segna_pagina}
    scelte = [ev for ev in evidenziature if ev.colore in colori_che_segnano]
    # rettangoli[0][1] = la y del bordo superiore della prima riga della frase.
    return sorted(scelte, key=lambda ev: (ev.pagina, ev.rettangoli[0][1] if ev.rettangoli else 0))
