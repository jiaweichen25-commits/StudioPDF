# StudioPDF

Un lettore PDF minimale per **studiare libri**, scritto in Python (PySide6 + PyMuPDF).

- **Segnalibro sulla parola**: riapri il libro esattamente dove ti eri fermato.
- **Sottolinea una frase** (anche su più righe) e scrivi la tua spiegazione: passando il mouse sulla sottolineatura la rileggi.
- **Evidenzia una frase** con un colore della tavolozza: resta colorata e con un clic apri la nota.
- **Pallini colorati nel margine** con note e sintesi; ogni colore ha un significato scelto da te.

Il PDF originale **non viene mai modificato**: le note stanno in un file JSON accanto al PDF
(`Libro.pdf` → `Libro.pdf.note.json`), leggibile e modificabile a mano. Se preferisci, tutte le note
possono stare in **una cartella a scelta** (⚙ Config → Percorsi): le note già scritte si spostano da sole.

## Come si usa

| Azione | Come |
|---|---|
| Aprire un libro | File → Apri… (`Ctrl+O`), oppure *Apri con…* di Windows: parte già dalla cartella dell'ultimo libro, con il file selezionato |
| Riaprire l'ultimo libro | l'icona del libro in alto a sinistra (passandoci sopra vedi il nome), File → Apri l'ultimo libro, oppure `Ctrl+Shift+O` |
| Sfogliare | `←` `→`, `PagSu` `PagGiù`, i pulsanti in alto, oppure le frecce ‹ › che compaiono avvicinando il mouse ai bordi |
| Zoom | `+` `-`, i pulsanti in alto, oppure `Ctrl` + rotellina |
| Sottolineare una frase | trascina il mouse con il tasto sinistro dalla prima all'ultima parola, poi «Sottolinea e spiega…» |
| Evidenziare una frase | trascina sulla frase, poi scegli il colore nel menu (o premi il suo tasto: `1`, `2`, `3`…) |
| Leggere / modificare un'evidenziatura | un clic sull'evidenziatura |
| Segnalibro | clic destro sulla parola → Segnalibro qui (anche su una parola sottolineata o evidenziata) |
| Cartella delle note | ⚙ Config → Percorsi → Cartella delle note (vuota = accanto a ogni PDF) |
| Nuovo pallino | clic sinistro nel margine, poi scegli il colore |
| Salvare la nota nel pop-up | `Invio` (per andare a capo `Shift+Invio`); il tasto si cambia in ⚙ Config → Keybinding |
| Leggere una nota | passa il mouse sopra la sottolineatura o il pallino (anteprima) |
| Modificare una nota | doppio clic sulla sottolineatura o sul pallino |
| Eliminare una nota | clic destro sulla sottolineatura o sul pallino → Elimina |

I colori dei pallini si cambiano in `config.json` (accanto al programma):

```json
{"tavolozza": [{"nome": "rosso", "colore": "#E5484D", "significato": "da ripassare"}]}
```

> Se rinomini o sposti un PDF, rinomina o sposta anche il suo `.note.json`.

## Impostazioni (⚙ Config)

Il pulsante **⚙ Config** nella barra in alto apre un menu (basta passarci sopra con il mouse):

- **Percorsi…**: la cartella dei libri, da cui parte *Apri…*.
- **Keybinding…**: i tasti di ogni azione, due per azione. Clicca su una casella e premi il tasto; la ✕ svuota la casella. I tasti doppi vengono segnalati in rosso.

  | Azione | Tasti predefiniti |
  |---|---|
  | Pagina precedente / successiva | `←` `PagSu` / `→` `PagGiù` |
  | Ingrandisci / Rimpicciolisci | `+` `Ctrl++` / `-` `Ctrl+-` |
  | Apri libro | `Ctrl+O` |
  | Chiudi programma | `Ctrl+W` |
  | Pallino di un colore | `1` `2` `3` `4`… (uno per colore della tavolozza) |

  Per il **pallino da tastiera**: porta il mouse sulla riga e premi il tasto del colore. Il pallino va nel margine più vicino.
- **Frecce laterali** e **Anteprima delle note**: interruttori per accendere o spegnere questi aiuti.

Tutto viene salvato in `config.json`, nelle sezioni `percorsi`, `tasti` e `opzioni`, che si possono anche modificare a mano.

## Sviluppo

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python main.py                 # avvia il programma
```

### Creare l'eseguibile Windows

```powershell
pyinstaller --noconfirm --windowed --name StudioPDF --add-data "assets;assets" main.py
```

Il programma si trova in `dist\StudioPDF\StudioPDF.exe`: si può copiare l'intera cartella dove si vuole.

## Struttura

```
main.py                     avvio del programma
studiopdf/
  note.py                   i tipi di dato delle note
  documento.py              lettura del PDF (PyMuPDF)
  archivio.py               il file .note.json
  tavolozza.py              i colori in config.json
  percorsi.py               dove stanno i file del programma
  posizione_note.py         dove sta il file delle note di un libro (e spostarlo)
  impostazioni.py           cartella dei libri, tasti e interruttori (in config.json)
  interfaccia/              la parte grafica (PySide6)
    finestra.py             finestra principale
    vista_pagina.py         la pagina e i clic
    selezione.py            la frase selezionata trascinando il mouse
    menu_tasti.py           menu in cui un tasto sceglie una voce
    icone.py                legge le icone da assets/
    disegno.py              sottolineature, pallini, segnalibro
    gestore_note.py         creare / modificare / eliminare note
    popup.py                la finestrella per scrivere le note
    anteprima.py            la schedina che compare passando il mouse
    frecce.py               le frecce laterali per sfogliare
    menu_config.py          il pulsante ⚙ Config e il suo menu
    dialogo_percorsi.py     la finestra «Percorsi»
    dialogo_tasti.py        la finestra «Keybinding»
    traduzioni.py           i testi di Qt in italiano
assets/                     le icone (file .svg, modificabili con un programma di grafica)
```

## Licenza

StudioPDF è distribuito con licenza **GNU AGPL-3.0** (vedi il file `LICENSE`), la stessa di [PyMuPDF](https://github.com/pymupdf/PyMuPDF), che il programma usa per leggere i PDF.
