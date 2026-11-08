"""Interfaz de línea de comandos.

    normas-cli 48425 --sigla CGP                 # extraer una norma (id, URL o archivo)
    normas-cli pagina.html --id 48425            # HTML guardado desde el navegador
    normas-cli todas [--cache-dir DIR]           # regenerar todo lo del registry
    normas-cli verificar [biblioteca]            # revisar duplicados, vacíos, enlaces
    normas-cli catalogo                          # índice + paquetes para el plugin
    normas-cli comparar CGP                      # DAFP frente al Senado (informe)
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
SUBCOMANDOS = ("extraer", "todas", "verificar", "catalogo", "comparar")


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

    k = sub.add_parser("comparar", help="comparar una norma entre el DAFP y el Senado")
    k.add_argument("norma", help="sigla o carpeta de la norma registrada (CGP, «Ley 80 de 1993»…)")
    k.add_argument("--url-senado", help="URL de la norma en el Senado (si no sigue el patrón)")
    k.add_argument("--salida", help="escribir el informe en este archivo (Markdown)")
    k.add_argument("--registry", "-r", default=str(REGISTRY))
    k.add_argument("--cache-dir", default=str(CACHE_DIR / "html"))

    c = sub.add_parser("catalogo", help="generar catalogo/ (índice y paquetes para el plugin)")
    c.add_argument("--biblioteca", default=str(BIBLIOTECA))
    c.add_argument("--salida", default=str(CATALOGO))
    return p


def _entrada(reg: Registry, origen: str):
    """Entrada del registry que corresponde a ``origen`` (id, sigla, carpeta o URL)."""
    i = id_desde_url(origen) if origen.startswith("http") else origen
    return next((e for e in reg.normas
                 if i in (e.id, e.sigla, e.ruta) or origen in (e.extra.get("url"), e.extra.get("url_senado"))),
                None)


def _fuentes(ent, reg: Registry, cache_dir: str | None) -> list:
    """Descarga y parsea todas las fuentes disponibles de una norma registrada."""
    from .comparar import url_senado
    from .consolidar import Fuente

    opciones = reg.opciones(ent.id, ent.sigla)
    titulo = f"{ent.tipo} {ent.numero} de {ent.anio}"
    fuentes = []
    if ent.id:
        html, url = fetch_html(ent.id, cache_dir=cache_dir or str(CACHE_DIR / "html"))
        fuentes.append(Fuente("DAFP", url_para_id(ent.id), parse(html, url=url, id_fuente=ent.id, opciones=opciones)))
    url_s = ent.extra.get("url_senado")
    if url_s is None and ent.extra.get("fuente") == "senado":
        url_s = ent.extra.get("url")
    if url_s is None:
        url_s = url_senado(ent.sigla, ent.tipo, ent.numero, ent.anio)
    if url_s:  # url_senado: false en el registry desactiva la fuente
        try:
            html = descargar_senado(url_s, cache_dir=CACHE_DIR, titulo=titulo)
            fuentes.append(Fuente("Senado", url_s, parse(html, url=url_s, opciones=opciones),
                                  tachado_explicito=True))
        except Exception as e:  # noqa: BLE001 — sin esa fuente se sigue con las demás
            print(f"  ! Senado no disponible ({url_s}): {e}", file=sys.stderr)
    return fuentes


def _extraer(origen: str, reg: Registry, *, sigla: str | None, id_fuente: str | None,
             output: str, cache_dir: str | None, actualizar_registry: bool, forzar: bool) -> dict:
    ent = _entrada(reg, origen) if not Path(origen).exists() else None
    if ent is not None:
        # Norma registrada: se comparan TODAS sus fuentes y se consolida la más actualizada.
        from .consolidar import consolidar
        fuentes = _fuentes(ent, reg, cache_dir)
        if not fuentes:
            raise RuntimeError("ninguna fuente disponible")
        norma = consolidar(fuentes)
        norma.sigla = sigla or ent.sigla
        norma.nombre_largo = norma.nombre_largo or ent.nombre
        if not norma.id_fuente:
            norma.id_fuente = ent.id
        dafp = next((f for f in fuentes if f.nombre == "DAFP"), None)
        norma.url_fuente = dafp.url if dafp else fuentes[0].url
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
            e2 = reg.por_id(id_fuente) or reg.por_identidad(norma.tipo, norma.numero, norma.anio)
            if e2 and e2.sigla:
                norma.sigla = e2.sigla
            if e2 and e2.nombre and not norma.nombre_largo:
                norma.nombre_largo = e2.nombre
    stats = render(norma, output, reg, forzar=forzar)
    if actualizar_registry:
        reg.registrar(norma, ruta=Path(stats["raiz"]).name)
        reg.guardar()
    print(f"✓ {norma.nombre_canonico}" + (f" ({norma.sigla})" if norma.sigla else ""))
    linea = (f"  artículos: {stats['articulos']}  niveles: {stats['niveles']}  notas: {stats['notas']}"
             f"  avisos: {len(stats['avisos'])}")
    if norma.consolidacion:
        c = norma.consolidacion
        linea += (f"  | base {c['base']}; tomados {c['elegidos']}; idénticos {c['identicos']}, "
                  f"distintos {c['diferentes']}, una sola fuente {c['solo_una']}")
    print(linea)
    print(f"  salida: {stats['raiz']}")
    return stats


def _comparar(args) -> int:
    from .comparar import comparar, informe, url_senado

    reg = Registry.cargar(args.registry)
    ent = next((e for e in reg.normas if args.norma in (e.sigla, e.ruta, e.nombre_canonico)), None)
    if ent is None or not ent.id:
        print(f"✗ «{args.norma}» no es una norma del DAFP registrada", file=sys.stderr)
        return 1
    url_s = args.url_senado or ent.extra.get("url_senado") or url_senado(ent.sigla, ent.tipo, ent.numero, ent.anio)
    if not url_s:
        print("✗ no se conoce la URL del Senado; usa --url-senado", file=sys.stderr)
        return 1
    opciones = reg.opciones(ent.id)
    html_a, url_a = fetch_html(ent.id, cache_dir=args.cache_dir)
    a = parse(html_a, url=url_a, id_fuente=ent.id, opciones=opciones)
    titulo = f"{ent.tipo} {ent.numero} de {ent.anio}"
    b = parse(descargar_senado(url_s, cache_dir=CACHE_DIR, titulo=titulo),
              url=url_s, opciones={k: v for k, v in opciones.items() if k != "esquema"})
    texto = informe(comparar(a, b), f"{ent.etiqueta} ({titulo})")
    if args.salida:
        Path(args.salida).write_text(texto, encoding="utf-8")
        print(f"✓ informe en {args.salida}")
    else:
        print(texto)
    return 0


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
    if args.comando == "comparar":
        return _comparar(args)
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
        if args.solo and not {ent.sigla, ent.id, ent.ruta} & set(args.solo):
            continue
        origen = ent.id or ent.sigla or ent.ruta
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
