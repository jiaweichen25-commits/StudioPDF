# StudioPDF

Un lettore PDF minimale per **studiare libri**, scritto in Python (PySide6 + PyMuPDF).

- **Segnalibro sulla parola**: riapri il libro esattamente dove ti eri fermato.
- **Sottolinea una parola** e scrivi la tua spiegazione: cliccando la sottolineatura la rileggi.
- **Pallini colorati nel margine** con note e sintesi; ogni colore ha un significato scelto da te.

Il PDF originale **non viene mai modificato**: le note stanno in un file JSON accanto al PDF
(`Libro.pdf` → `Libro.pdf.note.json`), leggibile e modificabile a mano.

## Come si usa

| Azione | Come |
|---|---|
| Aprire un libro | File → Apri… (`Ctrl+O`), oppure *Apri con…* di Windows |
| Sfogliare | `←` `→` oppure `PagSu` `PagGiù` |
| Zoom | `+` `-` oppure `Ctrl` + rotellina |
| Sottolineare una parola / segnalibro | clic destro sulla parola |
| Nuovo pallino | clic sinistro nel margine, poi scegli il colore |
| Leggere / modificare / eliminare una nota | clic sinistro sulla sottolineatura o sul pallino |

I colori dei pallini si cambiano in `config.json` (accanto al programma):

```json
{"tavolozza": [{"nome": "rosso", "colore": "#E5484D", "significato": "da ripassare"}]}
```

> Se rinomini o sposti un PDF, rinomina o sposta anche il suo `.note.json`.

## Sviluppo

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python main.py                 # avvia il programma
python -m pytest               # lancia i test
```

### Creare l'eseguibile Windows

```powershell
pyinstaller --noconfirm --windowed --name StudioPDF main.py
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
  percorsi.py               dove stanno i file
  interfaccia/              la parte grafica (PySide6)
    finestra.py             finestra principale
    vista_pagina.py         la pagina e i clic
    disegno.py              sottolineature, pallini, segnalibro
    gestore_note.py         creare / modificare / eliminare note
    popup.py                la finestrella delle note
tests/                      test automatici (pytest)
docs/                       design e piano di implementazione
```
