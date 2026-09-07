#!/data/data/com.termux/files/usr/bin/bash
# install_leviathan.sh — mueve el subsistema Leviathan (ya verificado en
# ~/leviathan_check, 14/14 tests reales) a su ubicación definitiva dentro
# de Q-HYPERCORE, como subpaquete separado de governance/.
#
# No recrea archivos desde cero: los COPIA tal cual del árbol ya probado,
# para no arriesgar una transcripción distinta al original verificado.
set -e

SRC=~/leviathan_check
DEST=~/Q-HYPERCORE/q_hypercore/leviathan

if [ ! -d "$SRC" ]; then
    echo "ERROR: no existe $SRC — corre primero la extracción del zip de Leviathan."
    exit 1
fi

mkdir -p "$DEST"

for f in __init__.py historical_clock.py look_ahead_detector.py base_collector.py \
         test_historical_clock.py test_look_ahead_detector.py; do
    if [ -f "$SRC/$f" ]; then
        cp "$SRC/$f" "$DEST/$f"
        echo "copiado: $f"
    else
        echo "AVISO: $SRC/$f no existe, se omite"
    fi
done

echo ""
echo "=== Archivos en q_hypercore/leviathan/ ==="
find "$DEST" -maxdepth 1 -type f

echo ""
echo "=== Corriendo tests dentro de q_hypercore/leviathan/ (imports locales, como en leviathan_check) ==="
cd "$DEST"
python3 -m pytest test_historical_clock.py test_look_ahead_detector.py -v
