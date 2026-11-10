# =============================================================================
# busquedas.py — ALGORITMOS DE BÚSQUEDA (BFS, DFS, Greedy, A*)
# =============================================================================
#
# Aquí está la lógica del proyecto. La ventana NO repite estos algoritmos:
# solo llama a la función ejecutar() y recibe un objeto ResultadoBusqueda.
#
# --- Cómo se conecta con app.py (exposición en vivo) ---
#
#   1) El usuario pulsa "Buscar ruta" en app.py
#   2) app._buscar() lee los combos (self.var_algo, var_inicio, var_destino, var_heur)
#   3) Llama:  res = ejecutar(algo, inicio, destino, heuristica_id)
#   4) Con "res" la app anima el mapa y escribe la consola negra
#
#   Botón "Comparar los 4" → app._comparar() → ejecutar_comparacion()
#
# --- Qué trae mapa.py ---
#
#   from mapa import GRAFO, HEURISTICAS, DEFAULT_INICIO, DEFAULT_DESTINO
#   GRAFO.vecinos_transitables(nodo) = a quién puedo ir y cuánto cuesta
#
# =============================================================================

from __future__ import annotations

import heapq
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

from mapa import DEFAULT_DESTINO, DEFAULT_INICIO, GRAFO, HeuristicaFn, HEURISTICAS, distancia_euclidiana

AlgoritmoId = str


# =============================================================================
# PasoBusqueda — un "fotograma" de la búsqueda (para la consola negra)
# =============================================================================
#
# Cada vez que un algoritmo expande un nodo, llamamos _registrar_paso()
# y guardamos un PasoBusqueda en la lista res.pasos.
#
# En app.py:
#   self._mostrar_paso_consola(paso) toma estos campos y los escribe en txt_consola
#   (expandir, Expandidos, Cola/Pila, ¿Es G?, etc.)

@dataclass
class PasoBusqueda:
    actual: str              # Nodo que acabamos de sacar de cola/pila (ej. "C")
    expandidos: list[str]    # Lista de nodos ya visitados en orden
    expandidos_txt: str      # Mismo texto compacto para la consola
    frontera_nombre: str     # "Cola" en BFS, "Pila" en DFS, "Frontera" en Greedy/A*
    frontera: list[str]      # Qué nodos faltan por revisar
    camino_arbol: list[str]
    camino_arbol_txt: str    # Camino desde S hasta el nodo actual en el árbol
    en_meta: bool            # True si actual == G (terminamos)


# =============================================================================
# ResultadoBusqueda — lo que devuelve ejecutar() a la ventana
# =============================================================================
#
# app.py usa este objeto así:
#   res.nodos_explorados  →  self._explorados_visibles (animación en el mapa)
#   res.ruta              →  self._dibujar_mapa (línea naranja al final)
#   res.pasos[i]          →  consola en el paso i de la animación
#   res.costo_total, res.explicacion  →  cuadro blanco "Resultados" (self.txt)

@dataclass
class ResultadoBusqueda:
    algoritmo: str
    inicio: str
    destino: str
    ruta: list[str]
    nodos_explorados: list[str]
    costo_total: int | None
    tiempo_segundos: float
    heuristica_id: str
    explicacion: str
    encontro_meta: bool
    padre: dict[str, str]
    aristas_descubrimiento: list[tuple[str, str]]
    nivel: dict[str, int]
    pasos: list[PasoBusqueda]

    @property
    def num_explorados(self) -> int:
        return len(self.nodos_explorados)

    def arista_padre(self, codigo: str) -> tuple[str, str] | None:
        if codigo not in self.padre:
            return None
        u = self.padre[codigo]
        return (u, codigo)


# =============================================================================
# Funciones de ayuda (las usan los 4 algoritmos, la app no las llama directo)
# =============================================================================

def _reconstruir_ruta(padre: dict[str, str], inicio: str, destino: str) -> list[str]:
    """
    Durante la búsqueda guardamos padre[v] = de qué nodo llegamos a v.
    Al terminar, subimos desde G con padre[] hasta S y armamos la ruta final.
    Esa lista va en ResultadoBusqueda.ruta → app la dibuja en naranja.
    """
    if destino not in padre and destino != inicio:
        return []
    actual = destino
    ruta = [actual]
    vistos: set[str] = set()
    while actual != inicio:
        if actual in vistos or actual not in padre:
            return []
        vistos.add(actual)
        actual = padre[actual]
        ruta.append(actual)
    return list(reversed(ruta))


def _camino_arbol(padre: dict[str, str], inicio: str, nodo: str) -> list[str]:
    """Camino S → nodo actual; se muestra en consola como 'Camino activo'."""
    if nodo == inicio:
        return [inicio]
    camino = [nodo]
    actual = nodo
    visitados: set[str] = set()
    while actual != inicio:
        if actual in visitados or actual not in padre:
            return [inicio, nodo]
        visitados.add(actual)
        actual = padre[actual]
        camino.append(actual)
    return list(reversed(camino))


def _registrar_paso(
    pasos: list[PasoBusqueda],
    *,
    actual: str,
    expandidos: list[str],
    frontera_nombre: str,
    frontera: list[str],
    padre: dict[str, str],
    inicio: str,
    destino: str,
) -> None:
    # Crea un PasoBusqueda y lo agrega a la lista pasos (luego app muestra cada uno).
    camino = _camino_arbol(padre, inicio, actual)
    pasos.append(
        PasoBusqueda(
            actual=actual,
            expandidos=list(expandidos),
            expandidos_txt="[" + "".join(expandidos) + "]",
            frontera_nombre=frontera_nombre,
            frontera=list(frontera),
            camino_arbol=camino,
            camino_arbol_txt=" → ".join(camino),
            en_meta=actual == destino,
        )
    )


def _costo_si_ruta(ruta: list[str]) -> int | None:
    if len(ruta) < 2:
        if len(ruta) == 1:
            return 0
        return None
    try:
        return GRAFO.costo_ruta(ruta)
    except ValueError:
        return None


# =============================================================================
# BFS — busca por capas (usa COLA: el primero que entra, primero en salir)
# =============================================================================
#
# Parámetros inicio y destino = lo que eligió el usuario en app (ej. S y G).
# Si el nodo sacado de la cola es destino, paramos.
# Cada vuelta del while llama _registrar_paso → llena res.pasos para la consola.

def bfs(inicio: str, destino: str) -> ResultadoBusqueda:
    t0 = time.perf_counter()
    cola: deque[str] = deque([inicio])
    padre: dict[str, str] = {}
    visitados: set[str] = {inicio}
    explorados: list[str] = []
    aristas_descubrimiento: list[tuple[str, str]] = []
    nivel: dict[str, int] = {inicio: 0}
    pasos: list[PasoBusqueda] = []

    # Sacamos de la cola; si u == destino terminamos; si no, metemos vecinos con GRAFO.vecinos_transitables.
    while cola:
        u = cola.popleft()
        explorados.append(u)
        if u == destino:
            _registrar_paso(
                pasos,
                actual=u,
                expandidos=explorados,
                frontera_nombre="Cola",
                frontera=list(cola),
                padre=padre,
                inicio=inicio,
                destino=destino,
            )
            break
        for v, _ in GRAFO.vecinos_transitables(u):
            if v not in visitados:
                visitados.add(v)
                padre[v] = u
                nivel[v] = nivel[u] + 1
                aristas_descubrimiento.append((u, v))
                cola.append(v)
        _registrar_paso(
            pasos,
            actual=u,
            expandidos=explorados,
            frontera_nombre="Cola",
            frontera=list(cola),
            padre=padre,
            inicio=inicio,
            destino=destino,
        )

    ruta = _reconstruir_ruta(padre, inicio, destino)
    if not ruta and inicio == destino:
        ruta = [inicio]
    costo = _costo_si_ruta(ruta)
    explicacion = (
        "BFS usa una cola y expande por capas. Con costos uniformes busca la ruta "
        "con el menor número de aristas, no necesariamente el menor costo económico."
    )
    return ResultadoBusqueda(
        algoritmo="BFS",
        inicio=inicio,
        destino=destino,
        ruta=ruta,
        nodos_explorados=explorados,
        costo_total=costo,
        tiempo_segundos=time.perf_counter() - t0,
        heuristica_id="—",
        explicacion=explicacion,
        encontro_meta=bool(ruta and ruta[-1] == destino),
        padre=padre,
        aristas_descubrimiento=aristas_descubrimiento,
        nivel=nivel,
        pasos=pasos,
    )


# =============================================================================
# DFS — profundiza en un camino (usa PILA: el último que entra, primero en salir)
# =============================================================================

def dfs(inicio: str, destino: str) -> ResultadoBusqueda:
    t0 = time.perf_counter()
    pila: list[str] = [inicio]
    padre: dict[str, str] = {}
    visitados: set[str] = set()
    explorados: list[str] = []
    aristas_descubrimiento: list[tuple[str, str]] = []
    nivel: dict[str, int] = {inicio: 0}
    pasos: list[PasoBusqueda] = []

    while pila:
        u = pila.pop()
        if u in visitados:
            continue
        visitados.add(u)
        explorados.append(u)
        if u == destino:
            _registrar_paso(
                pasos,
                actual=u,
                expandidos=explorados,
                frontera_nombre="Pila",
                frontera=list(reversed(pila)),
                padre=padre,
                inicio=inicio,
                destino=destino,
            )
            break
        for v, _ in reversed(GRAFO.vecinos_transitables(u)):
            if v not in visitados:
                if v not in padre and v != inicio:
                    padre[v] = u
                    nivel[v] = nivel.get(u, 0) + 1
                    aristas_descubrimiento.append((u, v))
                pila.append(v)
        _registrar_paso(
            pasos,
            actual=u,
            expandidos=explorados,
            frontera_nombre="Pila",
            frontera=list(reversed(pila)),
            padre=padre,
            inicio=inicio,
            destino=destino,
        )

    ruta = _reconstruir_ruta(padre, inicio, destino)
    if not ruta and inicio == destino:
        ruta = [inicio]
    costo = _costo_si_ruta(ruta)
    explicacion = (
        "DFS usa una pila: sigue un ramal en profundidad antes de retroceder. "
        "La ruta depende del orden de los vecinos; no garantiza mínimo costo ni mínimos saltos."
    )
    return ResultadoBusqueda(
        algoritmo="DFS",
        inicio=inicio,
        destino=destino,
        ruta=ruta,
        nodos_explorados=explorados,
        costo_total=costo,
        tiempo_segundos=time.perf_counter() - t0,
        heuristica_id="—",
        explicacion=explicacion,
        encontro_meta=bool(ruta and ruta[-1] == destino),
        padre=padre,
        aristas_descubrimiento=aristas_descubrimiento,
        nivel=nivel,
        pasos=pasos,
    )


# =============================================================================
# Greedy — siempre abre el nodo que parece más cerca de G (solo h(n), sin sumar costo)
# =============================================================================

def greedy_best_first(
    inicio: str,
    destino: str,
    heuristica: HeuristicaFn | None = None,
    heuristica_id: str = "recta",
) -> ResultadoBusqueda:
    h = heuristica or distancia_euclidiana
    t0 = time.perf_counter()
    frontera: list[tuple[float, str]] = [(h(inicio, destino), inicio)]
    padre: dict[str, str] = {}
    visitados: set[str] = set()
    explorados: list[str] = []
    aristas_descubrimiento: list[tuple[str, str]] = []
    nivel: dict[str, int] = {inicio: 0}
    pasos: list[PasoBusqueda] = []

    while frontera:
        _, u = heapq.heappop(frontera)
        if u in visitados:
            continue
        visitados.add(u)
        explorados.append(u)
        pendientes = sorted({n for _, n in frontera}, key=lambda c: (h(c, destino), c))
        if u == destino:
            _registrar_paso(
                pasos,
                actual=u,
                expandidos=explorados,
                frontera_nombre="Frontera",
                frontera=pendientes,
                padre=padre,
                inicio=inicio,
                destino=destino,
            )
            break
        for v, _ in GRAFO.vecinos_transitables(u):
            if v not in visitados:
                if v not in padre and v != inicio:
                    padre[v] = u
                    nivel[v] = nivel.get(u, 0) + 1
                    aristas_descubrimiento.append((u, v))
                heapq.heappush(frontera, (h(v, destino), v))
        pendientes = sorted({n for _, n in frontera}, key=lambda c: (h(c, destino), c))
        _registrar_paso(
            pasos,
            actual=u,
            expandidos=explorados,
            frontera_nombre="Frontera",
            frontera=pendientes,
            padre=padre,
            inicio=inicio,
            destino=destino,
        )

    ruta = _reconstruir_ruta(padre, inicio, destino)
    if not ruta and inicio == destino:
        ruta = [inicio]
    costo = _costo_si_ruta(ruta)
    explicacion = (
        "Greedy best-first elige siempre el nodo con menor heurística h(n), "
        "sin sumar el costo ya recorrido g(n). Puede irse por atajos costosos si la guía miente."
    )
    return ResultadoBusqueda(
        algoritmo="Greedy",
        inicio=inicio,
        destino=destino,
        ruta=ruta,
        nodos_explorados=explorados,
        costo_total=costo,
        tiempo_segundos=time.perf_counter() - t0,
        heuristica_id=heuristica_id,
        explicacion=explicacion,
        encontro_meta=bool(ruta and ruta[-1] == destino),
        padre=padre,
        aristas_descubrimiento=aristas_descubrimiento,
        nivel=nivel,
        pasos=pasos,
    )


# =============================================================================
# A* — equilibra costo recorrido g(n) + estimación h(n); suele dar menor costo en pesos
# =============================================================================

def a_star(
    inicio: str,
    destino: str,
    heuristica: HeuristicaFn | None = None,
    heuristica_id: str = "recta",
) -> ResultadoBusqueda:
    h = heuristica or distancia_euclidiana
    t0 = time.perf_counter()
    mejor_g: dict[str, float] = {inicio: 0.0}
    padre: dict[str, str] = {}
    explorados: list[str] = []
    aristas_descubrimiento: list[tuple[str, str]] = []
    nivel: dict[str, int] = {inicio: 0}
    frontera: list[tuple[float, float, str]] = [(h(inicio, destino), 0.0, inicio)]
    pasos: list[PasoBusqueda] = []

    while frontera:
        _, g_u, u = heapq.heappop(frontera)
        if g_u > mejor_g.get(u, float("inf")):
            continue
        explorados.append(u)
        pendientes = sorted({n for f, _, n in frontera}, key=lambda c: (mejor_g.get(c, 10**9) + h(c, destino), c))
        if u == destino:
            _registrar_paso(
                pasos,
                actual=u,
                expandidos=explorados,
                frontera_nombre="Frontera",
                frontera=pendientes,
                padre=padre,
                inicio=inicio,
                destino=destino,
            )
            break
        for v, costo_arista in GRAFO.vecinos_transitables(u):
            g_v = g_u + costo_arista
            # Si encontramos un camino más barato a v, actualizamos padre y frontera.
            if g_v < mejor_g.get(v, float("inf")):
                mejor_g[v] = g_v
                if v != inicio:
                    if v not in padre:
                        nivel[v] = nivel.get(u, 0) + 1
                        aristas_descubrimiento.append((u, v))
                    padre[v] = u
                heapq.heappush(frontera, (g_v + h(v, destino), g_v, v))
        pendientes = sorted({n for f, _, n in frontera}, key=lambda c: (mejor_g.get(c, 10**9) + h(c, destino), c))
        _registrar_paso(
            pasos,
            actual=u,
            expandidos=explorados,
            frontera_nombre="Frontera",
            frontera=pendientes,
            padre=padre,
            inicio=inicio,
            destino=destino,
        )

    ruta = _reconstruir_ruta(padre, inicio, destino)
    if not ruta and inicio == destino:
        ruta = [inicio]
    costo = _costo_si_ruta(ruta)
    explicacion = (
        "A* expande por f(n) = g(n) + h(n), equilibrando costo acumulado y estimación al destino. "
        "Con heurística admisible encuentra la ruta de menor costo."
    )
    return ResultadoBusqueda(
        algoritmo="A*",
        inicio=inicio,
        destino=destino,
        ruta=ruta,
        nodos_explorados=explorados,
        costo_total=costo,
        tiempo_segundos=time.perf_counter() - t0,
        heuristica_id=heuristica_id,
        explicacion=explicacion,
        encontro_meta=bool(ruta and ruta[-1] == destino),
        padre=padre,
        aristas_descubrimiento=aristas_descubrimiento,
        nivel=nivel,
        pasos=pasos,
    )


# Nombre en pantalla del combo Algoritmo (self.var_algo en app.py).
ALGORITMOS: dict[AlgoritmoId, str] = {
    "bfs": "BFS",
    "dfs": "DFS",
    "greedy": "Greedy best-first",
    "astar": "A*",
}


# =============================================================================
# ejecutar() — ENTRADA PRINCIPAL (la llama app._buscar al pulsar Buscar ruta)
# =============================================================================
#
#   algoritmo       ← self.var_algo.get()     ("bfs", "dfs", "greedy", "astar")
#   inicio          ← self.var_inicio.get()   (ej. "S")
#   destino         ← self.var_destino.get()  (ej. "G")
#   heuristica_id   ← self.var_heur.get()     (solo importa en greedy y astar)
#
# Devuelve un ResultadoBusqueda completo para animar y mostrar en pantalla.

def ejecutar(
    algoritmo: AlgoritmoId,
    inicio: str = DEFAULT_INICIO,
    destino: str = DEFAULT_DESTINO,
    heuristica_id: str = "recta",
) -> ResultadoBusqueda:
    _, fn_h = HEURISTICAS.get(heuristica_id, HEURISTICAS["recta"])
    if algoritmo == "bfs":
        return bfs(inicio, destino)
    if algoritmo == "dfs":
        return dfs(inicio, destino)
    if algoritmo == "greedy":
        return greedy_best_first(inicio, destino, fn_h, heuristica_id)
    if algoritmo == "astar":
        return a_star(inicio, destino, fn_h, heuristica_id)
    raise ValueError(f"Algoritmo desconocido: {algoritmo}")


# =============================================================================
# ejecutar_comparacion() — la llama app._comparar (botón Comparar los 4)
# =============================================================================

def ejecutar_comparacion(
    inicio: str = DEFAULT_INICIO,
    destino: str = DEFAULT_DESTINO,
    heuristica_id: str = "recta",
) -> list[ResultadoBusqueda]:
    return [
        ejecutar("bfs", inicio, destino, heuristica_id),
        ejecutar("dfs", inicio, destino, heuristica_id),
        ejecutar("greedy", inicio, destino, heuristica_id),
        ejecutar("astar", inicio, destino, heuristica_id),
    ]


# Resumen en texto; app._buscar() lo pega al final de self.txt.
def texto_comportamiento(res: ResultadoBusqueda) -> str:
    ruta_txt = GRAFO.ruta_a_codigos(res.ruta) if res.ruta else "—"
    costo_txt = str(res.costo_total) if res.costo_total is not None else "—"
    return (
        f"{res.algoritmo}: ruta {ruta_txt}; "
        f"explorados {res.num_explorados}; costo {costo_txt}; "
        f"tiempo {res.tiempo_segundos * 1000:.3f} ms. {res.explicacion}"
    )


def imprimir_pasos_estilo_curso(res: ResultadoBusqueda, destino: str) -> None:
    """Imprime en terminal cada paso (meta SÍ/NO, cola o pila)."""
    print(f"\n=== {res.algoritmo} ===")
    if not res.pasos:
        print("Sin pasos registrados.")
        return
    for i, paso in enumerate(res.pasos, start=1):
        meta = "SÍ" if paso.en_meta else "NO"
        cola_txt = "[" + ", ".join(paso.frontera) + "]" if paso.frontera else "[]"
        print(
            f"{i}  {paso.camino_arbol_txt}  {paso.actual} == {destino}  {meta}"
        )
        print(f"    Expandidos: {paso.expandidos_txt}   {paso.frontera_nombre}: {cola_txt}")
        print(f"    Camino activo: {paso.camino_arbol_txt}")
    if res.ruta:
        print("Solución:", GRAFO.ruta_a_codigos(res.ruta), f"(costo {res.costo_total})")
    else:
        print("Solución: no encontrada")


def demo_terminal(
    *,
    algoritmo: AlgoritmoId | None = None,
    inicio: str = DEFAULT_INICIO,
    destino: str = DEFAULT_DESTINO,
    heuristica_id: str = "recta",
) -> None:
    """Imprime en consola la búsqueda paso a paso (--demo)."""
    origen = GRAFO.nombre_largo(inicio)
    meta = GRAFO.nombre_largo(destino)
    print(f"Búsqueda logística: {origen} ({inicio}) → {meta} ({destino})")
    if algoritmo:
        res = ejecutar(algoritmo, inicio, destino, heuristica_id)
        imprimir_pasos_estilo_curso(res, destino)
        return
    for aid in ("bfs", "dfs", "greedy", "astar"):
        res = ejecutar(aid, inicio, destino, heuristica_id)
        imprimir_pasos_estilo_curso(res, destino)


# Respaldo en terminal (python3 busquedas.py --demo); no es la demo en vivo de la ventana.
def _main_cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Algoritmos de búsqueda sobre el mapa logístico")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Imprime paso a paso en terminal; sin --demo solo lista los cuatro algoritmos",
    )
    parser.add_argument(
        "--algoritmo",
        choices=list(ALGORITMOS.keys()),
        default=None,
        help="Con --demo: un solo algoritmo (por defecto los cuatro)",
    )
    parser.add_argument("--inicio", default=DEFAULT_INICIO)
    parser.add_argument("--destino", default=DEFAULT_DESTINO)
    parser.add_argument("--heuristica", default="recta", choices=list(HEURISTICAS.keys()))
    args = parser.parse_args()
    if args.demo:
        demo_terminal(
            algoritmo=args.algoritmo,
            inicio=args.inicio,
            destino=args.destino,
            heuristica_id=args.heuristica,
        )
        return
    for res in ejecutar_comparacion(args.inicio, args.destino, args.heuristica):
        print(texto_comportamiento(res))


if __name__ == "__main__":
    _main_cli()
