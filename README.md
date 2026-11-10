# Proyecto 2 — Rutas de logística (UTNA)

Grupo 7A. Búsqueda BFS, DFS, Greedy y A* sobre un mapa de CEDIS (S a G).

## Requisitos

- Python 3 con Tkinter.
- En Mac: Tcl 8.6 o superior (el script `ejecutar_app.sh` elige el intérprete).

Si la ventana sale en blanco en Mac:

```bash
brew install python@3.10
```

## Ejecutar la interfaz

```bash
git clone https://github.com/MIKKELMIKE/Logi3B.git
cd Logi3B
chmod +x ejecutar_app.sh
./ejecutar_app.sh
```

En la ventana: inicio **S**, destino **G**, heurística **recta**.  
Pulse **Buscar ruta** para cada algoritmo (bfs, dfs, greedy, astar).

## Sin ventana (terminal)

```bash
python3 busquedas.py
python3 busquedas.py --demo
python3 busquedas.py --demo --algoritmo astar
```

## Archivos

| Archivo | Función |
|---------|---------|
| mapa.py | Nodos, costos y heurísticas |
| busquedas.py | Algoritmos y función `ejecutar()` |
| app.py | Ventana gráfica |
| ejecutar_app.sh | Arranque recomendado en Mac |

## Medición del tiempo

El tiempo que aparece en **Resultados** (y en la salida de `busquedas.py`) mide **solo la ejecución del algoritmo en la CPU**, no la animación de la ventana ni las pausas entre pasos.

En `busquedas.py`, cada algoritmo (`bfs`, `dfs`, `greedy_best_first`, `a_star`) hace lo siguiente:

1. Al iniciar: `t0 = time.perf_counter()` (módulo estándar `time`).
2. Ejecuta el bucle de búsqueda (cola, pila o frontera con prioridad).
3. Al terminar: `tiempo_segundos = time.perf_counter() - t0` y lo guarda en `ResultadoBusqueda`.

En `app.py`, el panel muestra milisegundos:

`Tiempo: {res.tiempo_segundos * 1000:.3f} ms`

En un grafo pequeño los valores suelen ser fracciones de milisegundo; lo relevante para el análisis es la **ruta**, el **costo** y los **nodos explorados**.

## Equipo

Sergio Michell Carreón López, Xitlali Margarita Torres Salas, Emmanuel Lopez Castillo, Dominick Hammurabi Salazar Mendoza.
