"""Interfaz de línea de comandos.

Uso típico:

    normas-cli 48425 --sigla CGP --output ../biblioteca
    normas-cli "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=99712"
    normas-cli ruta/local.html --sigla LEY1996   # desde un archivo (fixtures)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .fetch import fetch_html, id_desde_url
from .parse import parse
from .registry import Registry
from .render import render

AQUI = Path(__file__).resolve().parent.parent  # carpeta extractor/


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="normas-cli",
        description="Convierte normativa colombiana (Función Pública) a notas de Obsidian.",
    )
    p.add_argument("origen", help="id de norma.php?i=, URL completa o archivo HTML local")
    p.add_argument("--sigla", help="sigla corta para la norma (CGP, CCo, CST…)")
    p.add_argument(
        "--output", "-o", default=str(AQUI.parent / "biblioteca"),
        help="carpeta de salida (por defecto: ../biblioteca)",
    )
    p.add_argument(
        "--registry", "-r", default=str(AQUI / "registry.yaml"),
        help="ruta del registry.yaml",
    )
    p.add_argument(
        "--no-update-registry", action="store_true",
        help="no escribir la norma en el registry",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)

    reg = Registry.cargar(args.registry)

    html, url = fetch_html(args.origen)
    id_fuente = id_desde_url(url) or (args.origen if args.origen.isdigit() else None)
    norma = parse(html, url=url if url.startswith("http") else None, id_fuente=id_fuente)

    if args.sigla:
        norma.sigla = args.sigla
    elif id_fuente:
        ent = reg.por_id(id_fuente)
        if ent and ent.sigla:
            norma.sigla = ent.sigla

    stats = render(norma, args.output, reg)

    if not args.no_update_registry:
        reg.registrar(norma, ruta=Path(stats["raiz"]).name)
        reg.guardar()

    print(f"✓ {norma.nombre_canonico}"
          + (f" ({norma.sigla})" if norma.sigla else ""))
    print(f"  artículos: {stats['articulos']}  niveles: {stats['niveles']}")
    print(f"  salida: {stats['raiz']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
