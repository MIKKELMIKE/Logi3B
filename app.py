#!/usr/bin/env python3
# =============================================================================
# app.py — VENTANA GRÁFICA (Tkinter)
# =============================================================================
#
# Este archivo NO calcula BFS/DFS/Greedy/A*.
# Solo muestra el mapa, los botones y llama a busquedas.py.
#
# --- Archivos que importamos ---
#
#   mapa.py     →  GRAFO (nombres, aristas), DEFAULT_INICIO/G, HEURISTICAS
#   busquedas.py →  ejecutar(), ejecutar_comparacion(), PasoBusqueda, ResultadoBusqueda
#
# --- Qué decirle al profe (flujo al pulsar "Buscar ruta") ---
#
#   Paso 1:  Usuario elige algoritmo, inicio S, destino G en los combos
#   Paso 2:  self._buscar() lee self.var_algo, var_inicio, var_destino, var_heur
#   Paso 3:  res = ejecutar(...)  en busquedas.py  (ahí corre el algoritmo)
#   Paso 4:  self._animar_exploracion(res) va nodo por nodo:
#              · self._dibujar_mapa() pinta visitados en el canvas (izquierda)
#              · self._mostrar_paso_consola(res.pasos[i]) escribe la caja negra
#   Paso 5:  self._aplicar_resultado(res) muestra ruta final y costo en self.txt
#
# La clase AppRutas hereda de tk.Tk: "self" es la ventana y todo lo que guardamos.

from __future__ import annotations

import os

os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

import argparse
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

from busquedas import (
    ALGORITMOS,
    PasoBusqueda,
    ejecutar,
    ejecutar_comparacion,
    ResultadoBusqueda,
    texto_comportamiento,
)
from mapa import (
    ARISTAS,
    ARISTAS_BLOQUEADAS,
    ARISTAS_SOLO_VISUAL,
    DEFAULT_DESTINO,
    DEFAULT_INICIO,
    GRAFO,
    HEURISTICAS,
)

# Tamaño del mapa (self.canvas a la izquierda de la ventana).
CANVAS_W = 620
CANVAS_H = 420
PAD = 28

# Milisegundos entre pasos en self._animar_exploracion (solo animación al buscar).
DEMO_MS_NODO = 1100
DEMO_MS_RESULTADO = 3200
DEMO_MS_INTRO = 2800
DEMO_MS_CIERRE = 4500
DEMO_SECUENCIA = ["bfs", "dfs", "greedy", "astar"]


class AppRutas(tk.Tk):
    """
    Ventana principal del proyecto.
    Todo lo que necesitamos después (canvas, combos, consola) lo guardamos en self.
    """

    # =========================================================================
    # __init__ — Construye la ventana: mapa + controles + resultados + consola
    # =========================================================================

    def __init__(
        self,
        *,
        modo_demo: bool = False,
        export_frames: Path | None = None,
        on_demo_completo: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()

        # ----- Variables de estado (self = esta ventana) -----
        #
        # self._explorados_visibles  →  qué nodos pintar gris/amarillo al animar
        # self._ruta_resaltada       →  lista S→G en naranja cuando termina
        # self._layout               →  posición en píxeles de cada letra en el canvas
        # self._animacion_activa     →  True = no dejar pulsar Buscar otra vez

        self._modo_demo = modo_demo          # automático: no usar en clase
        self._export_frames = export_frames
        self._on_demo_completo = on_demo_completo
        self._frame_idx = 0
        self._explorados_visibles: list[str] = []
        self._ruta_resaltada: list[str] = []
        self._layout: dict[str, tuple[float, float]] = {}
        self._animacion_activa = False

        self.title("Proyecto 2 — Rutas de logística (UTNA)")
        self.geometry("1000x720")
        self.minsize(900, 640)
        self._configurar_estilos_tk()

        self.var_demo_banner = tk.StringVar(value="")
        self._barra_demo = ttk.Label(
            self,
            textvariable=self.var_demo_banner,
            font=("Helvetica", 12, "bold"),
            anchor="center",
            padding=8,
            relief="solid",
        )
        if modo_demo:
            self._barra_demo.pack(fill=tk.X, side=tk.TOP)

        self._calcular_layout()

        # =================================================================
        # PARTE VISUAL — Izquierda: mapa (self.canvas). Derecha: panel.
        # =================================================================

        self._marco = tk.Frame(self, bg="#e8e8e8", padx=8, pady=8)
        self._marco.pack(fill=tk.BOTH, expand=True)
        marco = self._marco

        # self.canvas: el profe ve el grafo aquí. self._dibujar_mapa() redibuja líneas y nodos.
        self.canvas = tk.Canvas(
            marco,
            width=CANVAS_W,
            height=CANVAS_H,
            bg="#f4f6f8",
            highlightthickness=1,
            highlightbackground="#90a4ae",
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.NONE, padx=(0, 12))

        panel = tk.Frame(marco, bg="#e8e8e8")
        panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # -----------------------------------------------------------------
        # COMBOS (lo que el usuario elige antes de Buscar)
        # -----------------------------------------------------------------
        # En Tkinter enlazamos cada Combobox con un StringVar.
        # Cuando buscamos, hacemos .get() y se lo pasamos a busquedas.ejecutar().

        ttk.Label(panel, text="Algoritmo").grid(row=0, column=0, sticky="w", pady=2)
        self.var_algo = tk.StringVar(value="bfs")
        combo_algo = ttk.Combobox(
            panel,
            textvariable=self.var_algo,
            values=list(ALGORITMOS.keys()),
            state="readonly",
            width=28,
        )
        combo_algo.grid(row=0, column=1, sticky="ew", pady=2)
        combo_algo.bind("<<ComboboxSelected>>", self._on_algo_change)

        ttk.Label(panel, text="Inicio").grid(row=1, column=0, sticky="w", pady=2)
        self.var_inicio = tk.StringVar(value=DEFAULT_INICIO)   # viene de mapa.DEFAULT_INICIO
        ttk.Combobox(
            panel,
            textvariable=self.var_inicio,
            values=GRAFO.etiquetas(),
            state="readonly",
            width=28,
        ).grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(panel, text="Destino").grid(row=2, column=0, sticky="w", pady=2)
        self.var_destino = tk.StringVar(value=DEFAULT_DESTINO)  # mapa.DEFAULT_DESTINO ("G")
        ttk.Combobox(
            panel,
            textvariable=self.var_destino,
            values=GRAFO.etiquetas(),
            state="readonly",
            width=28,
        ).grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(panel, text="Heurística").grid(row=3, column=0, sticky="w", pady=2)
        self.var_heur = tk.StringVar(value="recta")  # claves de mapa.HEURISTICAS
        self.combo_heur = ttk.Combobox(
            panel,
            textvariable=self.var_heur,
            values=list(HEURISTICAS.keys()),
            state="readonly",
            width=28,
        )
        self.combo_heur.grid(row=3, column=1, sticky="ew", pady=2)
        self._on_algo_change()

        # -----------------------------------------------------------------
        # BOTONES — command= dice qué método de ESTA clase (self) se ejecuta
        # -----------------------------------------------------------------

        botones = tk.Frame(panel, bg="#e8e8e8")
        botones.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        self.btn_buscar = ttk.Button(
            botones,
            text="Buscar ruta",
            command=self._buscar,  # ← aquí enlazamos el botón con la función _buscar
        )
        self.btn_buscar.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(botones, text="Comparar los 4", command=self._comparar).pack(side=tk.LEFT)
        if not modo_demo:
            ttk.Button(botones, text="Demo secuencial", command=self.iniciar_demo_secuencial).pack(
                side=tk.LEFT, padx=(8, 0)
            )

        # -----------------------------------------------------------------
        # self.txt — cuadro blanco "Resultados" (ruta, costo, nodos explorados)
        # -----------------------------------------------------------------

        ttk.Label(panel, text="Resultados").grid(row=5, column=0, columnspan=2, sticky="w")
        self.txt = tk.Text(panel, height=14, wrap=tk.WORD, font=("Menlo", 10))
        self.txt.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(4, 2))
        scroll = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=self.txt.yview)
        scroll.grid(row=6, column=2, sticky="ns")
        self.txt.configure(yscrollcommand=scroll.set)

        # -----------------------------------------------------------------
        # self.txt_consola — caja NEGRA: un paso de busquedas.PasoBusqueda por vez
        # -----------------------------------------------------------------

        ttk.Label(panel, text="Consola (paso a paso)").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )
        marco_consola = tk.Frame(panel, bg="#e8e8e8")
        marco_consola.grid(row=8, column=0, columnspan=2, sticky="nsew", pady=4)
        self.txt_consola = tk.Text(
            marco_consola,
            height=9,
            wrap=tk.WORD,
            font=("Menlo", 10),
            bg="#1b262c",
            fg="#e0e0e0",
            insertbackground="#e0e0e0",
            relief="solid",
            borderwidth=1,
        )
        self.txt_consola.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_consola = ttk.Scrollbar(marco_consola, orient=tk.VERTICAL, command=self.txt_consola.yview)
        scroll_consola.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_consola.configure(yscrollcommand=scroll_consola.set)
        self._configurar_tags_consola()

        panel.columnconfigure(1, weight=1)
        panel.rowconfigure(6, weight=1)
        panel.rowconfigure(8, weight=1)

        self._dibujar_mapa()
        self._escribir_intro()
        self._mostrar_paso_consola(None)

        if modo_demo:
            self.after(600, self.iniciar_demo_secuencial)

        self._preparar_ventana_visibilidad()

    def _configurar_estilos_tk(self) -> None:
        # Colores y tema Tk en Mac para que se vean los controles.
        self.configure(bg="#e8e8e8")
        style = ttk.Style(self)
        try:
            if sys.platform == "darwin":
                style.theme_use("clam")
            elif "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError:
            pass
        fondo = "#e8e8e8"
        style.configure("TFrame", background=fondo)
        style.configure("TLabel", background=fondo)
        style.configure("TButton", padding=4)

    def _preparar_ventana_visibilidad(self) -> None:
        self.update_idletasks()
        self.update()
        self.canvas.update_idletasks()
        self._dibujar_mapa()
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(350, lambda: self.attributes("-topmost", False))
        self.focus_force()

    # =========================================================================
    # DIBUJO DEL MAPA (usa mapa.GRAFO y se pinta en self.canvas)
    # =========================================================================

    def _calcular_layout(self) -> None:
        # Convierte coordenadas (x,y) de mapa.py a píxeles → self._layout["S"], etc.
        xs = [n.x for n in GRAFO.nodos.values()]
        ys = [n.y for n in GRAFO.nodos.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        rango_x = max(max_x - min_x, 1e-6)
        rango_y = max(max_y - min_y, 1e-6)
        for codigo, nodo in GRAFO.nodos.items():
            px = PAD + (nodo.x - min_x) / rango_x * (CANVAS_W - 2 * PAD)
            py = CANVAS_H - PAD - (nodo.y - min_y) / rango_y * (CANVAS_H - 2 * PAD)
            self._layout[codigo] = (px, py)

    def _on_algo_change(self, *_args: object) -> None:
        # Al cambiar el combo algoritmo, activamos heurística solo en Greedy/A*.
        heuristica = self.var_algo.get() in ("greedy", "astar")
        self.combo_heur.configure(state="readonly" if heuristica else "disabled")

    def _dibujar_mapa(self, ruta: list[str] | None = None) -> None:
        """
        Redibuja todo el canvas.
        Lee self._explorados_visibles (animación) y la lista ruta (naranja al final).
        Lee mapa.ARISTAS para líneas y costos; ARISTAS_SOLO_VISUAL para Q→G rojo.
        """
        self.canvas.delete("all")
        ruta = ruta or []
        explorados = set(self._explorados_visibles)
        aristas_ruta = set(zip(ruta, ruta[1:]))

        todas_aristas = list(ARISTAS) + list(ARISTAS_SOLO_VISUAL)
        for a, b, costo in todas_aristas:
            xa, ya = self._layout[a]
            xb, yb = self._layout[b]
            bloqueada = (a, b) in ARISTAS_BLOQUEADAS or (b, a) in ARISTAS_BLOQUEADAS
            en_ruta = (a, b) in aristas_ruta or (b, a) in aristas_ruta
            color = "#c62828" if bloqueada else ("#1565c0" if en_ruta else "#90a4ae")
            dash = (4, 4) if bloqueada else ()
            width = 4 if en_ruta else 2
            self.canvas.create_line(xa, ya, xb, yb, fill=color, width=width, dash=dash)
            mx, my = (xa + xb) / 2, (ya + yb) / 2
            etiqueta = f"{costo}" + (" ✕" if bloqueada else "")
            self.canvas.create_text(mx, my - 8, text=etiqueta, fill="#546e7a", font=("Helvetica", 8))

        ultimo_explorado = self._explorados_visibles[-1] if self._explorados_visibles else None
        for codigo, nodo in GRAFO.nodos.items():
            x, y = self._layout[codigo]
            en_ruta = codigo in ruta
            explorado = codigo in explorados
            if en_ruta:
                fill = "#ff8f00"
                radio = 18
            elif explorado:
                fill = "#fff59d" if codigo == ultimo_explorado else "#e0e0e0"
                radio = 16
            else:
                fill = "#eceff1"
                radio = 14
            self.canvas.create_oval(x - radio, y - radio, x + radio, y + radio, fill=fill, outline="#37474f", width=2)
            self.canvas.create_text(x, y, text=codigo, font=("Helvetica", 10, "bold"))
            self.canvas.create_text(x, y + radio + 10, text=nodo.nombre, font=("Helvetica", 8))

    def _escribir_intro(self) -> None:
        self.txt.delete("1.0", tk.END)
        self.txt.insert(
            tk.END,
            "Mapa con 12 nodos y costos en cada tramo.\n"
            "El camino Q → G está bloqueado (línea roja).\n\n"
            "Elija algoritmo, inicio (S) y destino (G) y pulse Buscar ruta.\n"
            "La consola negra muestra cola o pila en cada paso.\n"
            "Comparar los 4 ejecuta los cuatro algoritmos seguidos.\n",
        )

    def _configurar_tags_consola(self) -> None:
        self.txt_consola.tag_configure("titulo", foreground="#90caf9")
        self.txt_consola.tag_configure("prompt", foreground="#fff59d")
        self.txt_consola.tag_configure("frontera", foreground="#b2dfdb")
        self.txt_consola.tag_configure("arbol", foreground="#c5e1a5")
        self.txt_consola.tag_configure("meta_si", foreground="#69f0ae")
        self.txt_consola.tag_configure("meta_no", foreground="#ffab91")

    def _mostrar_paso_consola(self, paso: PasoBusqueda | None) -> None:
        """
        Toma un PasoBusqueda (viene de res.pasos en busquedas.py)
        y lo escribe en self.txt_consola (consola negra).
        La animación llama esto en cada paso.
        """
        self.txt_consola.delete("1.0", tk.END)
        if paso is None:
            self.txt_consola.insert(tk.END, "Pulse Buscar ruta para ver el avance paso a paso.\n")
            return
        self.txt_consola.insert(tk.END, "Consola (estado de búsqueda)\n", "titulo")
        cola_txt = "[" + ", ".join(paso.frontera) + "]" if paso.frontera else "[]"
        self.txt_consola.insert(tk.END, f"> expandir({paso.actual})\n", "prompt")
        self.txt_consola.insert(tk.END, f"Expandidos: {paso.expandidos_txt}\n")
        self.txt_consola.insert(tk.END, f"{paso.frontera_nombre}: {cola_txt}\n", "frontera")
        self.txt_consola.insert(tk.END, f"Camino activo: {paso.camino_arbol_txt}\n", "arbol")
        if paso.en_meta:
            self.txt_consola.insert(tk.END, "¿Es G?  SÍ — fin.\n", "meta_si")
        else:
            self.txt_consola.insert(
                tk.END,
                f"¿Es G?  no ({paso.actual} ≠ G) → sigue.\n",
                "meta_no",
            )

    def _paso_en_indice(self, res: ResultadoBusqueda, indice: int) -> PasoBusqueda | None:
        # res.pasos[i] alinea con res.nodos_explorados[i] en la animación.
        if indice < 0 or indice >= len(res.pasos):
            return None
        return res.pasos[indice]

    def _set_animacion_activa(self, activa: bool) -> None:
        self._animacion_activa = activa
        estado = "disabled" if activa else "normal"
        self.btn_buscar.configure(state=estado)

    def _capturar_frame(self) -> None:
        # Modo automático: no usamos en exposición en vivo.
        if not self._export_frames:
            return
        self._export_frames.mkdir(parents=True, exist_ok=True)
        self.update_idletasks()
        try:
            from PIL import ImageGrab
        except ImportError:
            return
        x = self.winfo_rootx()
        y = self.winfo_rooty()
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            return
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        path = self._export_frames / f"frame_{self._frame_idx:05d}.png"
        img.save(path)
        self._frame_idx += 1

    def _validar_par(self) -> tuple[str, str] | None:
        """
        Lee los combos Inicio y Destino (self.var_inicio, self.var_destino).
        Devuelve el par de letras para pasarlo a busquedas.ejecutar().
        """
        inicio = self.var_inicio.get()
        destino = self.var_destino.get()
        if inicio == destino:
            if not self._modo_demo:
                messagebox.showinfo("Aviso", "Inicio y destino deben ser distintos para buscar una ruta.")
            return None
        return inicio, destino

    def _mostrar_resultado(self, res: ResultadoBusqueda, encabezado: str = "", append: bool = False) -> None:
        """
        Escribe en self.txt (panel Resultados) los datos del ResultadoBusqueda.
        Usa GRAFO.ruta_a_texto() para nombres largos de la ruta.
        """
        if not append:
            self.txt.delete("1.0", tk.END)
        if encabezado:
            self.txt.insert(tk.END, encabezado + "\n")
        self.txt.insert(tk.END, f"Algoritmo: {res.algoritmo}\n")
        if res.heuristica_id != "—":
            desc, _ = HEURISTICAS.get(res.heuristica_id, ("", None))
            self.txt.insert(tk.END, f"Heurística: {res.heuristica_id} — {desc}\n")
        ruta_larga = GRAFO.ruta_a_texto(res.ruta) if res.ruta else "No se encontró ruta"
        self.txt.insert(tk.END, f"Ruta: {ruta_larga}\n")
        self.txt.insert(tk.END, f"Códigos: {GRAFO.ruta_a_codigos(res.ruta) if res.ruta else '—'}\n")
        self.txt.insert(tk.END, f"Nodos explorados ({res.num_explorados}): {', '.join(res.nodos_explorados)}\n")
        costo = res.costo_total if res.costo_total is not None else "—"
        self.txt.insert(tk.END, f"Costo total: {costo}\n")
        self.txt.insert(tk.END, f"Tiempo: {res.tiempo_segundos * 1000:.3f} ms\n")
        self.txt.insert(tk.END, f"Comportamiento: {res.explicacion}\n\n")

    def _aplicar_resultado(self, res: ResultadoBusqueda, *, limpiar_panel: bool = True) -> None:
        """
        Cuando ya terminó la búsqueda: guarda res.ruta, pinta el mapa final
        y llama _mostrar_resultado para llenar self.txt.
        """
        self._ruta_resaltada = res.ruta
        self._explorados_visibles = list(res.nodos_explorados)
        self._dibujar_mapa(res.ruta)
        self._mostrar_resultado(res, append=not limpiar_panel)
        self._capturar_frame()

    def _animar_exploracion(
        self,
        res: ResultadoBusqueda,
        indice: int,
        al_terminar: Callable[[], None],
    ) -> None:
        """
        res viene de busquedas.ejecutar().
        indice recorre res.nodos_explorados[0], [1], …
        En cada paso:
          · actualiza self._explorados_visibles
          · self._mostrar_paso_consola(res.pasos[indice])
          · self._dibujar_mapa()
        self.after(DEMO_MS_NODO, ...) hace la pausa entre nodos.
        """
        if indice >= len(res.nodos_explorados):
            self._explorados_visibles = list(res.nodos_explorados)
            ultimo = self._paso_en_indice(res, len(res.pasos) - 1)
            self._mostrar_paso_consola(ultimo)
            self._dibujar_mapa(res.ruta)
            self._capturar_frame()
            self.after(DEMO_MS_RESULTADO, al_terminar)
            return
        self._explorados_visibles = res.nodos_explorados[: indice + 1]
        self._mostrar_paso_consola(self._paso_en_indice(res, indice))
        self._dibujar_mapa([])
        self._capturar_frame()
        self.after(DEMO_MS_NODO, lambda: self._animar_exploracion(res, indice + 1, al_terminar))

    # =========================================================================
    # _buscar — METODO PRINCIPAL DE LA EXPOSICIÓN (botón "Buscar ruta")
    # =========================================================================
    #
    #   1) self._validar_par()  lee self.var_inicio y self.var_destino
    #   2) ejecutar(algo, inicio, destino, heur)  corre el algoritmo en busquedas.py
    #   3) self._animar_exploracion(res)  muestra paso a paso mapa + consola
    #   4) self._aplicar_resultado(res)  deja ruta final en self.txt y en el mapa
    #

    def _buscar(self) -> None:
        if self._animacion_activa:
            return
        par = self._validar_par()
        if not par:
            return
        inicio, destino = par
        algo = self.var_algo.get()
        heur = self.var_heur.get()
        try:
            res = ejecutar(algo, inicio, destino, heur)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return

        self.txt.delete("1.0", tk.END)
        self.txt.insert(
            tk.END,
            f"Buscando con {res.algoritmo} ({inicio} → {destino})…\n"
            "Revise el mapa y la consola negra.\n\n",
        )
        self._ruta_resaltada = []
        self._explorados_visibles = []
        self._dibujar_mapa()
        self._mostrar_paso_consola(None)
        self._set_animacion_activa(True)

        def al_finalizar() -> None:
            self._set_animacion_activa(False)
            self._aplicar_resultado(res)
            self.txt.insert(tk.END, texto_comportamiento(res) + "\n")

        if res.nodos_explorados:
            self._animar_exploracion(res, 0, al_finalizar)
        else:
            self._set_animacion_activa(False)
            self._aplicar_resultado(res)
            self.txt.insert(tk.END, texto_comportamiento(res) + "\n")

    def _comparar(self) -> None:
        """
        Botón "Comparar los 4".
        Llama busquedas.ejecutar_comparacion() con el mismo S, G y heurística.
        Escribe cuatro bloques en self.txt y resalta la ruta más barata en el mapa.
        """
        par = self._validar_par()
        if not par:
            return
        inicio, destino = par
        heur = self.var_heur.get()
        resultados = ejecutar_comparacion(inicio, destino, heur)
        self.txt.delete("1.0", tk.END)
        self.txt.insert(tk.END, f"Comparación {GRAFO.nombre_largo(inicio)} → {GRAFO.nombre_largo(destino)}\n\n")
        for res in resultados:
            self._mostrar_resultado(res, append=True)
        mejor = min(
            (r for r in resultados if r.costo_total is not None),
            key=lambda r: r.costo_total or 0,
            default=None,
        )
        if mejor:
            self._ruta_resaltada = mejor.ruta
            self._explorados_visibles = []
            self._dibujar_mapa(mejor.ruta)
            self.txt.insert(
                tk.END,
                f"Menor costo en esta corrida: {mejor.algoritmo} (costo {mejor.costo_total}).\n"
                "La ruta resaltada en el mapa corresponde a ese resultado.\n",
            )
        self._capturar_frame()
        return resultados

    def _set_banner(self, texto: str) -> None:
        self.var_demo_banner.set(texto)
        if not texto:
            return
        try:
            self._barra_demo.pack_info()
        except tk.TclError:
            self._barra_demo.pack(fill=tk.X, side=tk.TOP, before=self._marco)

    def _mostrar_cierre_demo(self, resultados: list[ResultadoBusqueda]) -> None:
        self._set_banner("Comparativa final — resumen de los cuatro algoritmos")
        self.txt.delete("1.0", tk.END)
        self.txt.insert(
            tk.END,
            "=== COMPARACIÓN FINAL ===\n"
            f"Origen: {GRAFO.nombre_largo(DEFAULT_INICIO)}  →  "
            f"Destino: {GRAFO.nombre_largo(DEFAULT_DESTINO)}\n\n",
        )
        for res in resultados:
            self.txt.insert(
                tk.END,
                f"{res.algoritmo}: costo {res.costo_total}, "
                f"{res.num_explorados} nodos explorados, ruta {GRAFO.ruta_a_codigos(res.ruta)}\n",
            )
        mejor = min(resultados, key=lambda r: r.costo_total or 0)
        self.txt.insert(
            tk.END,
            f"\nMenor costo: {mejor.algoritmo} ({mejor.costo_total}).\n",
        )
        self._explorados_visibles = []
        self._dibujar_mapa(mejor.ruta)
        self._capturar_frame()

    def iniciar_demo_secuencial(self) -> None:
        # Modo automático: no usamos en exposición en vivo.
        par = self._validar_par()
        if not par:
            return
        inicio, destino = par
        heur = self.var_heur.get()

        self._set_banner(
            f"Demo — {GRAFO.nombre_largo(inicio)} ({inicio}) → {GRAFO.nombre_largo(destino)} ({destino})"
        )
        self.txt.delete("1.0", tk.END)
        self.txt.insert(
            tk.END,
            "Demostración secuencial: BFS → DFS → Greedy → A*\n"
            "Se animará la exploración nodo por nodo y después la ruta encontrada.\n",
        )
        self._explorados_visibles = []
        self._dibujar_mapa()
        self._capturar_frame()

        resultados_acum: list[ResultadoBusqueda] = []

        def ejecutar_paso(indice_algo: int) -> None:
            if indice_algo >= len(DEMO_SECUENCIA):
                self._mostrar_cierre_demo(resultados_acum)
                self.after(
                    DEMO_MS_CIERRE,
                    lambda: self._finalizar_demo(),
                )
                return

            algo = DEMO_SECUENCIA[indice_algo]
            etiqueta = ALGORITMOS[algo]
            self.var_algo.set(algo)
            self._on_algo_change()
            self._set_banner(f"Ejecutando {etiqueta} ({indice_algo + 1}/4)")

            res = ejecutar(algo, inicio, destino, heur)
            resultados_acum.append(res)

            self.txt.delete("1.0", tk.END)
            self.txt.insert(tk.END, f"=== {etiqueta} ===\n")
            self.txt.insert(tk.END, "Explorando nodos… (animación en el mapa)\n")
            self._explorados_visibles = []
            self._dibujar_mapa()
            self._capturar_frame()

            def tras_animacion() -> None:
                self._aplicar_resultado(res)
                self.after(DEMO_MS_RESULTADO, lambda: ejecutar_paso(indice_algo + 1))

            self._animar_exploracion(res, 0, tras_animacion)

        self.after(DEMO_MS_INTRO, lambda: ejecutar_paso(0))

    def _finalizar_demo(self) -> None:
        if self._on_demo_completo:
            self._on_demo_completo()
        else:
            self._set_banner("Demo finalizada")


def exportar_captura_reporte(ruta: Path) -> None:
    # Solo con python3 app.py --screenshot; no usamos en clase.
    from busquedas import ejecutar

    ruta.parent.mkdir(parents=True, exist_ok=True)
    app = AppRutas()
    app.update_idletasks()
    app._comparar()
    res_bfs = ejecutar("bfs", app.var_inicio.get(), app.var_destino.get(), app.var_heur.get())
    if res_bfs.pasos:
        paso = res_bfs.pasos[min(2, len(res_bfs.pasos)) - 1]
        app._mostrar_paso_consola(paso)
    app.update_idletasks()
    try:
        from PIL import ImageGrab
    except ImportError as exc:
        app.destroy()
        raise RuntimeError("Pillow necesario para --screenshot") from exc
    x = app.winfo_rootx()
    y = app.winfo_rooty()
    w = app.winfo_width()
    h = app.winfo_height()
    if w <= 1 or h <= 1:
        app.update()
        w, h = app.winfo_width(), app.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    img.save(ruta)
    app.destroy()


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulador de rutas logísticas")
    parser.add_argument("--demo", action="store_true", help="Inicia la demo secuencial al abrir")
    parser.add_argument(
        "--export-frames",
        type=Path,
        default=None,
        help="Guarda capturas PNG de la ventana para armar video",
    )
    parser.add_argument(
        "--screenshot",
        type=Path,
        default=None,
        help="Guarda una captura de la interfaz y termina (para el reporte PDF)",
    )
    return parser.parse_args(argv)


# =============================================================================
# main() — ejecutar_app.sh hace: python app.py  →  entra aquí
# =============================================================================

def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv or sys.argv[1:])
    if args.screenshot:
        exportar_captura_reporte(args.screenshot)
        print(f"Captura guardada: {args.screenshot}")
        return
    completo = False

    def al_completar() -> None:
        nonlocal completo
        completo = True
        app.quit()

    app = AppRutas(
        modo_demo=args.demo or args.export_frames is not None,
        export_frames=args.export_frames,
        on_demo_completo=al_completar if args.export_frames else None,
    )
    if sys.platform == "darwin":
        partes = str(app.tk.call("info", "patchlevel")).split(".")
        tcl_mayor, tcl_menor = int(partes[0]), int(partes[1])
        if (tcl_mayor, tcl_menor) < (8, 6):
            messagebox.showwarning(
                "Python antiguo",
                "Use ./ejecutar_app.sh (necesita Tcl 8.6).\n"
                "Si falla: brew install python@3.10",
            )
    if args.export_frames and not args.demo:
        app.after(500, app.iniciar_demo_secuencial)
    app.mainloop()
    if args.export_frames and not completo:
        sys.exit(1)


if __name__ == "__main__":
    main()
