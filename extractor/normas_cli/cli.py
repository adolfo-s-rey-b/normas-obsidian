"""Interfaz de línea de comandos.

    normas-cli 48425 --sigla CGP                 # extraer una norma (id, URL o archivo)
    normas-cli pagina.html --id 48425            # HTML guardado desde el navegador
    normas-cli todas [--cache-dir DIR]           # regenerar todo lo del registry
    normas-cli verificar [biblioteca]            # revisar duplicados, vacíos, enlaces
    normas-cli catalogo                          # índice + paquetes para el plugin
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .fetch import CACHE_DIR, fetch_html, id_desde_url, url_para_id
from .parse import parse
from .registry import Registry
from .render import render
from .senado import descargar_norma as descargar_senado

AQUI = Path(__file__).resolve().parent.parent  # carpeta extractor/
REPO = AQUI.parent
BIBLIOTECA = REPO / "biblioteca"
CATALOGO = REPO / "catalogo"
REGISTRY = AQUI / "registry.yaml"
SUBCOMANDOS = ("extraer", "todas", "verificar", "catalogo")


def _comunes(p: argparse.ArgumentParser) -> None:
    p.add_argument("--output", "-o", default=str(BIBLIOTECA),
                   help="carpeta de salida (por defecto: biblioteca/ del repo)")
    p.add_argument("--registry", "-r", default=str(REGISTRY), help="ruta del registry.yaml")
    p.add_argument("--cache-dir", help="guardar/reutilizar el HTML descargado en esta carpeta")
    p.add_argument("--forzar", action="store_true",
                   help="reemplazar la carpeta de salida aunque no parezca generada por normas-cli")


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="normas-cli",
        description="Convierte normativa colombiana (Función Pública) a notas de Obsidian.",
    )
    sub = p.add_subparsers(dest="comando")

    e = sub.add_parser("extraer", help="extraer una norma (comando por defecto)")
    e.add_argument("origen", help="id de norma.php?i=, URL completa o archivo HTML local")
    e.add_argument("--sigla", help="sigla corta para la norma (CGP, CCo, CST…)")
    e.add_argument("--id", dest="id_fuente",
                   help="id del DAFP cuando el origen es un archivo local (para la fuente y el registry)")
    e.add_argument("--no-update-registry", action="store_true",
                   help="no escribir la norma en el registry")
    _comunes(e)

    t = sub.add_parser("todas", help="regenerar todas las normas del registry")
    t.add_argument("--solo", nargs="*", help="limitar a estas siglas o ids")
    _comunes(t)
    t.set_defaults(cache_dir=str(CACHE_DIR / "html"))

    v = sub.add_parser("verificar", help="revisar la biblioteca generada")
    v.add_argument("biblioteca", nargs="?", default=str(BIBLIOTECA))
    v.add_argument("--estricto", action="store_true",
                   help="fallar también por enlaces internos rotos y artículos vacíos")

    c = sub.add_parser("catalogo", help="generar catalogo/ (índice y paquetes para el plugin)")
    c.add_argument("--biblioteca", default=str(BIBLIOTECA))
    c.add_argument("--salida", default=str(CATALOGO))
    return p


def _extraer(origen: str, reg: Registry, *, sigla: str | None, id_fuente: str | None,
             output: str, cache_dir: str | None, actualizar_registry: bool, forzar: bool) -> dict:
    ent_senado = next((e for e in reg.normas if e.extra.get("fuente") == "senado"
                       and origen in (e.extra.get("url"), e.sigla)), None)
    if ent_senado is not None:
        # Normas que el DAFP no publica: Secretaría del Senado (ver senado.py).
        html = descargar_senado(ent_senado.extra["url"], cache_dir=cache_dir or CACHE_DIR,
                                titulo=f"{ent_senado.tipo} {ent_senado.numero} de {ent_senado.anio}")
        url = ent_senado.extra["url"]
        sigla = sigla or ent_senado.sigla
    else:
        html, url = fetch_html(origen, cache_dir=cache_dir)
        id_fuente = id_fuente or id_desde_url(url) or (origen if origen.isdigit() else None)
        if not url.startswith("http"):
            url = url_para_id(id_fuente) if id_fuente else None
    opciones = reg.opciones(id_fuente, sigla)
    norma = parse(html, url=url, id_fuente=id_fuente, opciones=opciones)
    if sigla:
        norma.sigla = sigla
    else:
        ent = reg.por_id(id_fuente) or reg.por_identidad(norma.tipo, norma.numero, norma.anio)
        if ent and ent.sigla:
            norma.sigla = ent.sigla
        if ent and ent.nombre and not norma.nombre_largo:
            norma.nombre_largo = ent.nombre
    stats = render(norma, output, reg, forzar=forzar)
    if actualizar_registry:
        reg.registrar(norma, ruta=Path(stats["raiz"]).name)
        reg.guardar()
    print(f"✓ {norma.nombre_canonico}" + (f" ({norma.sigla})" if norma.sigla else ""))
    print(f"  artículos: {stats['articulos']}  niveles: {stats['niveles']}  notas: {stats['notas']}"
          f"  avisos: {len(stats['avisos'])}")
    print(f"  salida: {stats['raiz']}")
    return stats


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Compatibilidad: `normas-cli 48425 --sigla CGP` equivale a `normas-cli extraer …`.
    if argv and argv[0] not in SUBCOMANDOS and argv[0] not in ("-h", "--help"):
        argv.insert(0, "extraer")
    args = construir_parser().parse_args(argv)

    if args.comando == "verificar":
        from .verificar import verificar
        return verificar(Path(args.biblioteca), estricto=args.estricto)
    if args.comando == "catalogo":
        from .catalogo import generar_catalogo
        generar_catalogo(Path(args.biblioteca), Path(args.salida))
        return 0
    if args.comando is None:
        construir_parser().print_help()
        return 1

    reg = Registry.cargar(args.registry)
    if args.comando == "extraer":
        _extraer(args.origen, reg, sigla=args.sigla, id_fuente=args.id_fuente, output=args.output,
                 cache_dir=args.cache_dir, actualizar_registry=not args.no_update_registry,
                 forzar=args.forzar)
        return 0

    # todas
    errores = 0
    for ent in reg.normas:
        if args.solo and ent.sigla not in args.solo and ent.id not in args.solo:
            continue
        origen = ent.id or (ent.extra.get("url") if ent.extra.get("fuente") == "senado" else None)
        if not origen:
            print(f"✗ {ent.etiqueta}: sin id ni fuente en el registry", file=sys.stderr)
            continue
        try:
            _extraer(origen, reg, sigla=ent.sigla, id_fuente=ent.id, output=args.output,
                     cache_dir=args.cache_dir, actualizar_registry=True, forzar=args.forzar)
        except Exception as e:  # noqa: BLE001 — se informa y se sigue con las demás
            errores += 1
            print(f"✗ {ent.etiqueta}: {e}", file=sys.stderr)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
