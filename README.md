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

## Equipo

Sergio Michell Carreón López, Xitlali Margarita Torres Salas, Emmanuel Lopez Castillo, Dominick Hammurabi Salazar Mendoza.
