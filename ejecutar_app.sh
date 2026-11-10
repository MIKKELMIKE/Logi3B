#!/bin/sh
# =============================================================================
# ejecutar_app.sh — Cómo abrimos el programa frente al docente
# =============================================================================
#
# Desde la carpeta entrega (o proyecto-2):
#
#   ./ejecutar_app.sh
#
# Qué hace este script:
#
#   1) Se coloca en la misma carpeta donde están mapa.py, busquedas.py y app.py
#   2) Busca un Python que tenga Tkinter Y Tcl versión 8.6 o mayor
#      (si usa el Python del Mac viejo, la ventana sale en blanco)
#   3) Ejecuta:  python app.py
#      → eso crea la clase AppRutas y abre la ventana con el mapa
#
# En clase: elegir bfs, dfs, greedy, astar y pulsar "Buscar ruta" en la ventana.
#
# =============================================================================

cd "$(dirname "$0")"
export TK_SILENCE_DEPRECATION=1

_version_tcl() {
  "$1" -c '
import tkinter as tk
r = tk.Tk()
r.withdraw()
p = r.tk.call("info", "patchlevel")
r.destroy()
parts = p.split(".")
print(int(parts[0]) * 100 + int(parts[1]))
' 2>/dev/null
}

_candidatos="
/opt/homebrew/opt/python@3.10/bin/python3.10
/opt/homebrew/bin/python3.10
/opt/homebrew/opt/python@3.12/bin/python3.12
/opt/homebrew/bin/python3.12
/opt/homebrew/opt/python@3.11/bin/python3.11
/opt/homebrew/bin/python3.11
/usr/local/opt/python@3.12/bin/python3.12
/usr/local/bin/python3.12
/usr/bin/python3
python3
"

mejor=""
mejor_ver=0
for candidato in $_candidatos; do
  [ -x "$candidato" ] || continue
  ver=$(_version_tcl "$candidato") || continue
  if [ "$ver" -gt "$mejor_ver" ]; then
    mejor_ver=$ver
    mejor=$candidato
  fi
done

if [ -z "$mejor" ] || [ "$mejor_ver" -lt 806 ]; then
  echo "Error: hace falta Python con Tcl 8.6+ (Tkinter)." >&2
  echo "En Mac el /usr/bin/python3 (Tcl 8.5) deja la ventana en blanco." >&2
  echo "Instala: brew install python@3.10" >&2
  exit 1
fi

tcl=$("$mejor" -c 'import tkinter as tk; r=tk.Tk(); r.withdraw(); print(r.tk.call("info","patchlevel")); r.destroy()')
echo "Usando $mejor (Tcl/Tk $tcl)"
exec "$mejor" app.py "$@"
