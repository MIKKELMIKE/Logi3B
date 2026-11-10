# =============================================================================
# mapa.py — DATOS DEL MAPA (no hay ventana aquí)
# =============================================================================
#
# Este archivo solo guarda la información del problema:
#   · Qué ciudades hay (nodos S, A, G, etc.)
#   · Qué caminos existen y cuánto cuestan
#   · Cómo estimar distancia al destino (heurísticas)
#
# ¿Quién lee este archivo?
#
#   busquedas.py
#       Pregunta a GRAFO qué vecinos tiene cada nodo al correr BFS, DFS, etc.
#       Usa HEURISTICAS cuando el usuario elige Greedy o A* en la app.
#
#   app.py
#       Llena los combos de Inicio/Destino con GRAFO.etiquetas().
#       Dibuja líneas y círculos usando ARISTAS y las coordenadas de NODOS.
#
# =============================================================================

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable

HeuristicaFn = Callable[[str, str], float]


# =============================================================================
# SECCIÓN 1 — Inicio y destino por defecto
# =============================================================================
#
# Cuando abres la ventana (app.py), los combos ya traen S y G.
# Esos valores vienen de aquí:
#   app.py hace:  self.var_inicio = StringVar(value=DEFAULT_INICIO)
#                 self.var_destino = StringVar(value=DEFAULT_DESTINO)
#
# El profesor puede cambiar los combos, pero el caso del reporte es S → G.

DEFAULT_INICIO = "S"
DEFAULT_DESTINO = "G"

# Lista fija: al sacar vecinos en DFS el orden importa (cambia la ruta encontrada).
ORDEN_VECINOS = ["C", "O", "P", "Q", "M", "B", "N", "A", "I", "J", "S", "G"]


@dataclass(frozen=True)
class NodoMapa:
    """
    Un punto del mapa.
    codigo = letra del combo (ej. "S")
    nombre = texto largo para el panel de resultados
    x, y   = posición para dibujar en el canvas y para calcular h(n)
    """
    codigo: str
    nombre: str
    x: float
    y: float


# =============================================================================
# SECCIÓN 2 — Tabla de nodos (12 almacenes / CEDIS)
# =============================================================================
#
# Las claves del diccionario ("S", "B", …) son las opciones del Combobox en app.py.

NODOS: dict[str, NodoMapa] = {
    "S": NodoMapa("S", "CEDIS Rincón", 0.0, 0.0),
    "B": NodoMapa("B", "Bodega Norte", 2.0, 8.0),
    "C": NodoMapa("C", "Calvillo", 0.0, 3.0),
    "O": NodoMapa("O", "Cosío", 1.0, 5.0),
    "P": NodoMapa("P", "Tepezalá", 3.0, 6.0),
    "Q": NodoMapa("Q", "Asientos", 5.0, 7.0),
    "M": NodoMapa("M", "El Llano", 8.0, 5.0),
    "N": NodoMapa("N", "Pabellón", 2.0, 4.0),
    "A": NodoMapa("A", "Encarnación", 6.0, 0.5),
    "I": NodoMapa("I", "Jesús María", 4.0, 5.0),
    "J": NodoMapa("J", "Libramiento", 8, 1.0),
    "G": NodoMapa("G", "CEDIS Aguascalientes", 10.0, 0.0),
}


# =============================================================================
# SECCIÓN 3 — Caminos y costos (pesos en la arista)
# =============================================================================
#
# Cada tupla: (nodo A, nodo B, costo en pesos).
# GrafoLogistica copia cada arista en los dos sentidos para poder caminar ida y vuelta.

ARISTAS: list[tuple[str, str, int]] = [
    ("S", "B", 9),
    ("B", "G", 40),
    ("S", "C", 4),
    ("C", "O", 3),
    ("O", "P", 3),
    ("P", "Q", 3),
    ("Q", "M", 4),
    ("M", "G", 15),
    ("S", "N", 5),
    ("N", "I", 3),
    ("I", "G", 9),
    ("S", "A", 1),
    ("A", "J", 4),
    ("J", "G", 18),
    ("A", "I", 6),
    ("N", "O", 3),
    ("P", "I", 3),
    ("Q", "I", 4),
    ("I", "M", 5),
]

# ---------------------------------------------------------------------------
# Arista Q → G: regla especial del ejercicio
# ---------------------------------------------------------------------------
#   · En app._dibujar_mapa() se pinta en ROJO (ARISTAS_SOLO_VISUAL) para que se vea.
#   · En busquedas.py NO se puede usar: GRAFO.vecinos_transitables() la salta.

ARISTAS_BLOQUEADAS: set[tuple[str, str]] = {("Q", "G")}
ARISTAS_SOLO_VISUAL: list[tuple[str, str, int]] = [
    ("Q", "G", 12),
]

_RANK_VECINO = {codigo: i for i, codigo in enumerate(ORDEN_VECINOS)}


# =============================================================================
# SECCIÓN 4 — Clase GrafoLogistica (consultas al mapa)
# =============================================================================
#
# Creamos UN solo objeto global al final: GRAFO
# Desde otros archivos hacemos:  from mapa import GRAFO

class GrafoLogistica:

    def __init__(self) -> None:
        # Convierte la lista ARISTAS en listas de adyacencia por nodo.
        self.nodos = NODOS
        self._ady: dict[str, list[tuple[str, int]]] = {c: [] for c in self.nodos}
        for a, b, costo in ARISTAS:
            self._ady[a].append((b, costo))
            self._ady[b].append((a, costo))
        for codigo in self._ady:
            self._ady[codigo].sort(key=lambda par: _RANK_VECINO.get(par[0], 99))

    def vecinos(self, codigo: str) -> list[tuple[str, int]]:
        return list(self._ady[codigo])

    def vecinos_transitables(self, codigo: str) -> list[tuple[str, int]]:
        """
        Lo usan bfs(), dfs(), greedy y a_star() en busquedas.py.
        Devuelve (vecino, costo) sin incluir aristas bloqueadas como Q→G.
        """
        bloqueadas = ARISTAS_BLOQUEADAS
        salida: list[tuple[str, int]] = []
        for vecino, costo in self._ady[codigo]:
            if (codigo, vecino) in bloqueadas or (vecino, codigo) in bloqueadas:
                continue
            salida.append((vecino, costo))
        return salida

    def etiquetas(self) -> list[str]:
        """Lista ['S','B',…] para values= en los Combobox de app.py."""
        return list(self.nodos.keys())

    def nombre_largo(self, codigo: str) -> str:
        """Ej. 'S' → 'CEDIS Rincón' en el cuadro de Resultados."""
        return self.nodos[codigo].nombre

    def coordenada(self, codigo: str) -> tuple[float, float]:
        """
        Usado en:
          · app._calcular_layout() para poner cada nodo en el canvas
          · funciones de heurística abajo (distancia al destino G)
        """
        n = self.nodos[codigo]
        return (n.x, n.y)

    def costo_arista(self, a: str, b: str) -> int | None:
        for vecino, costo in self._ady[a]:
            if vecino == b:
                return costo
        return None

    def costo_ruta(self, ruta: Iterable[str]) -> int:
        """
        Suma el costo de S→…→G.
        busquedas.py llama esto al terminar cada algoritmo (campo costo_total).
        """
        nodos = list(ruta)
        total = 0
        for u, v in zip(nodos, nodos[1:]):
            costo = self.costo_arista(u, v)
            if costo is None:
                raise ValueError(f"No hay arista entre {u} y {v}")
            total += costo
        return total

    def ruta_a_texto(self, ruta: Iterable[str]) -> str:
        """app._mostrar_resultado() muestra nombres largos en self.txt."""
        partes = [self.nombre_largo(c) for c in ruta]
        return " → ".join(partes)

    def ruta_a_codigos(self, ruta: Iterable[str]) -> str:
        """Muestra solo letras: S → A → I → G."""
        return " → ".join(ruta)


GRAFO = GrafoLogistica()


# =============================================================================
# SECCIÓN 5 — Heurísticas h(n) para Greedy y A*
# =============================================================================
#
# En app.py el combo Heurística guarda una clave ("recta", "cero", …).
# Esa clave busca aquí la función que estima qué tan cerca está un nodo de G.
#
# busquedas.ejecutar() hace:  _, fn_h = HEURISTICAS[heuristica_id]
#                             y pasa fn_h a greedy_best_first() o a_star()

def distancia_euclidiana(codigo: str, destino: str) -> float:
    x1, y1 = GRAFO.coordenada(codigo)
    x2, y2 = GRAFO.coordenada(destino)
    return math.hypot(x1 - x2, y1 - y2)


def heuristica_horizontal(codigo: str, destino: str) -> float:
    x1, _ = GRAFO.coordenada(codigo)
    x2, _ = GRAFO.coordenada(destino)
    return abs(x1 - x2)


def heuristica_hacia_bodega(codigo: str, destino: str) -> float:
    del destino
    bx, by = GRAFO.coordenada("B")
    x1, y1 = GRAFO.coordenada(codigo)
    return math.hypot(x1 - bx, y1 - by)


def heuristica_cero(codigo: str, destino: str) -> float:
    del codigo, destino
    return 0.0


HEURISTICAS: dict[str, tuple[str, HeuristicaFn]] = {
    "recta": ("Distancia en línea recta al destino (admisible)", distancia_euclidiana),
    "recta_x3": ("Línea recta × 3 (sobreestima; A* puede dejar de ser óptimo)", lambda c, d: 3.0 * distancia_euclidiana(c, d)),
    "horizontal": ("Solo distancia horizontal al destino", heuristica_horizontal),
    "a_bodega": ("Distancia a Bodega Norte (mala guía hacia CEDIS Ags)", heuristica_hacia_bodega),
    "cero": ("h = 0 (sin información)", heuristica_cero),
}
