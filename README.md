# StudioPDF

Un lettore PDF minimale per **studiare libri**, scritto in Python (PySide6 + PyMuPDF).

- **Segnalibro sulla parola**: riapri il libro esattamente dove ti eri fermato.
- **Sottolinea una frase** (anche su più righe) e scrivi la tua spiegazione: passando il mouse sulla sottolineatura la rileggi.
- **Evidenzia una frase** con un colore della tavolozza: resta colorata e con un clic apri la nota.
- **Pallini colorati nel margine** con note e sintesi; ogni colore ha un significato scelto da te.
- **Riapri l'ultimo libro** con un clic sull'icona in alto a sinistra.
- **Tasti personalizzabili** per ogni azione.

Il PDF originale **non viene mai modificato**: le note stanno in un file JSON accanto al PDF
(`Libro.pdf` → `Libro.pdf.note.json`), leggibile e modificabile a mano. Se preferisci, tutte le note
possono stare in **una cartella a scelta** (⚙ Config → Percorsi): le note già scritte si spostano da sole.

## Scaricare (Windows)

1. Dalla pagina [Releases](https://github.com/jiaweichen25-commits/StudioPDF/releases) scarica lo zip
   `StudioPDF-…-windows.zip` (in *Assets*).
2. Estrai lo zip dove vuoi e avvia `StudioPDF\StudioPDF.exe`. Non serve installare Python.

Windows potrebbe mostrare «Windows ha protetto il PC», perché il programma non è firmato digitalmente:
clicca **Ulteriori informazioni → Esegui comunque**.

## Come si usa

| Azione | Come |
|---|---|
| Aprire un libro | File → Apri… (`Ctrl+O`): parte già dalla cartella dell'ultimo libro, con il file selezionato. Oppure *Apri con…* di Windows |
| Riaprire l'ultimo libro | l'icona del libro in alto a sinistra (passandoci sopra vedi il nome), File → Apri l'ultimo libro, oppure `Ctrl+Shift+O` |
| Sfogliare | `←` `→`, `PagSu` `PagGiù`, i pulsanti in alto, oppure le frecce ‹ › che compaiono avvicinando il mouse ai bordi |
| Zoom | `+` `-`, i pulsanti in alto, oppure `Ctrl` + rotellina |
| Sottolineare una frase | trascina il mouse con il tasto sinistro dalla prima all'ultima parola, poi «Sottolinea e spiega…» |
| Evidenziare una frase | trascina sulla frase, poi scegli il colore nel menu (o premi il suo tasto: `1`, `2`, `3`…) |
| Nuovo pallino | clic sinistro nel margine, poi scegli il colore (oppure mouse sulla riga e tasto del colore) |
| Salvare la nota nel pop-up | `Invio` (per andare a capo `Shift+Invio`) |
| Leggere una nota | passa il mouse sopra la sottolineatura o il pallino (anteprima); un clic sull'evidenziatura |
| Modificare una nota | doppio clic sulla sottolineatura o sul pallino; un clic sull'evidenziatura |
| Eliminare una nota | clic destro sulla nota → Elimina |
| Segnalibro | clic destro sulla parola → Segnalibro qui (anche su una parola sottolineata o evidenziata) |

Due note non possono sovrapporsi: se selezioni una frase che tocca una sottolineatura o
un'evidenziatura esistente, il programma ti avvisa.

I colori di pallini ed evidenziature si cambiano in `config.json` (accanto al programma):

```json
{"tavolozza": [{"nome": "rosso", "colore": "#E5484D", "significato": "da ripassare"}]}
```

## Dove stanno le note

- **Accanto al PDF** (predefinito): `Libro.pdf.note.json`. Se rinomini o sposti il PDF, rinomina o sposta anche il suo `.note.json`.
- **In una cartella a scelta** (⚙ Config → Percorsi → Cartella delle note): i file si chiamano
  `Libro [3fa91c0d].note.json`. Il codice tra parentesi è un'«impronta» calcolata dal contenuto del PDF:
  così due libri con lo stesso nome non si mescolano, e se sposti o rinomini il PDF le note si ritrovano da sole.
  Se il contenuto del PDF cambia (es. una nuova edizione), per il programma è un libro nuovo.
- Cambiando la scelta, le note già scritte si **spostano da sole** la prima volta che apri ogni libro. Non si cancella mai niente.
- Se la cartella delle note non è raggiungibile (es. una chiavetta staccata), il libro si apre ma le note restano in sola lettura.

## Impostazioni (⚙ Config)

Il pulsante **⚙ Config** nella barra in alto apre un menu (basta passarci sopra con il mouse):

- **Percorsi…**: la **cartella dei libri**, da cui parte *Apri…* quando non c'è un ultimo libro, e la **cartella delle note** (vuota = accanto a ogni PDF).
- **Keybinding…**: i tasti di ogni azione, due per azione. Clicca su una casella e premi il tasto; la ✕ svuota la casella, `Esc` annulla. I tasti doppi vengono segnalati in rosso.

  | Azione | Tasti predefiniti |
  |---|---|
  | Pagina precedente / successiva | `←` `PagSu` / `→` `PagGiù` |
  | Ingrandisci / Rimpicciolisci | `+` `Ctrl++` / `-` `Ctrl+-` |
  | Apri libro | `Ctrl+O` |
  | Apri l'ultimo libro | `Ctrl+Shift+O` |
  | Chiudi programma | `Ctrl+W` |
  | Salva nota (nel pop-up) | `Invio` (anche quello del tastierino) |
  | Pallino di un colore | `1` `2` `3` `4`… (uno per colore della tavolozza) |

  Per il **pallino da tastiera**: porta il mouse sulla riga e premi il tasto del colore. Il pallino va nel margine più vicino.
  Gli stessi tasti dei colori scelgono il colore anche nel menu che compare dopo aver selezionato una frase.
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

> Ricompilando, PyInstaller cancella e ricrea `dist\StudioPDF`, compreso il `config.json` con le tue impostazioni:
> copialo da parte prima e rimettilo dopo. Chiudi StudioPDF prima di ricompilare, altrimenti i suoi file sono bloccati.

## Struttura

```
main.py                     avvio del programma
studiopdf/
  note.py                   i tipi di dato delle note
  documento.py              lettura del PDF (PyMuPDF)
  archivio.py               il file .note.json
  posizione_note.py         dove sta il file delle note di un libro (e spostarlo)
  tavolozza.py              i colori in config.json
  percorsi.py               dove stanno i file del programma
  impostazioni.py           cartelle, ultimo libro, tasti e interruttori (in config.json)
  interfaccia/              la parte grafica (PySide6)
    finestra.py             finestra principale
    vista_pagina.py         la pagina e i clic
    selezione.py            la frase selezionata trascinando il mouse
    menu_tasti.py           menu in cui un tasto sceglie una voce
    icone.py                legge le icone da assets/
    disegno.py              sottolineature, evidenziature, pallini, segnalibro
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
