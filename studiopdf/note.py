"""I tipi di dato condivisi da tutto il programma.

Questo modulo contiene solo "forme" di dati, nessuna logica:
chi vuole sapere com'è fatta una nota guarda qui.
"""

# Un rettangolo sulla pagina, in punti PDF (1 punto = 1/72 di pollice).
# L'ordine è: (x0, y0, x1, y1)
#   x0, y0 = angolo in alto a sinistra
#   x1, y1 = angolo in basso a destra
# Nei PDF (come li espone PyMuPDF) la y cresce andando verso il BASSO.
Rett = tuple[float, float, float, float]
