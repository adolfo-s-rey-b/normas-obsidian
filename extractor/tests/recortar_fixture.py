# Utilidad de mantenimiento (no es una prueba): uso descrito en tests/README.md.
"""Crea fixtures recortados: conserva el título y tramos del contenido.

Cada tramo es (patrón_inicio, patrón_fin): se corta en el <p (o <table/<ol)
que contiene la coincidencia, buscando cada patrón después del anterior.
"""
import re, sys
from pathlib import Path
H=Path.home()/".cache/normas-obsidian/html"; F=Path("tests/fixtures")
def _inicio_p(h,pos):
    return max(h.rfind("<p",0,pos), h.rfind("<P",0,pos))
def recortar(i, tramos, salida):
    h=(H/f"{i}.html").read_text(encoding="utf-8")
    t=re.search(r'<h2 class="titulo-norma"[^>]*>.*?</h2>',h,re.S)
    d=re.search(r'<div class="descripcion-contenido"[^>]*>',h)
    fin_cont=h.index('<div class="clearfix', d.end()) if '<div class="clearfix' in h[d.end():] else len(h)
    pos=d.end(); partes=[]
    for a,b in tramos:
        ma=re.compile(a).search(h,pos)
        if ma is None: sys.exit(f"{salida}: no se halló {a!r}")
        ia=_inicio_p(h,ma.start())
        if b is None: ib=fin_cont
        else:
            mb=re.compile(b).search(h,ma.end())
            if mb is None: sys.exit(f"{salida}: no se halló {b!r}")
            ib=_inicio_p(h,mb.start())
        partes.append(h[ia:ib]); pos=ib
    out=('<html><head><meta charset="utf-8"></head><body>\n'+t.group(0)+"\n"+d.group(0)+"\n"
         +"\n".join(partes)+"\n</div></body></html>\n")
    (F/salida).write_text(out,encoding="utf-8"); print(salida,len(out))
