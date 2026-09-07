#!/data/data/com.termux/files/usr/bin/bash
# backup_q_hypercore.sh — Backup automático y verificable del estado de
# Q-HYPERCORE (governance + leviathan + tests + core), con manifest
# SHA-256 real para poder confirmar integridad después.
#
# No sube nada a ningún lado — solo empaqueta localmente en ~/backups_qhypercore/.
set -e

cd ~/Q-HYPERCORE

BACKUP_DIR=~/backups_qhypercore
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
ARCHIVE_NAME="q_hypercore_backup_${TIMESTAMP}.tar.gz"
MANIFEST_NAME="q_hypercore_manifest_${TIMESTAMP}.sha256"

mkdir -p "$BACKUP_DIR"

echo "=== 1. Generando manifest SHA-256 de todos los .py (pre-backup) ==="
find q_hypercore tests -type f -name "*.py" 2>/dev/null | sort | xargs sha256sum > "$BACKUP_DIR/$MANIFEST_NAME"
cat "$BACKUP_DIR/$MANIFEST_NAME"

echo ""
echo "=== 2. Empaquetando (excluye __pycache__ y .pytest_cache) ==="
tar --exclude='__pycache__' --exclude='.pytest_cache' \
    -czf "$BACKUP_DIR/$ARCHIVE_NAME" \
    q_hypercore tests evidence 2>/dev/null || \
tar --exclude='__pycache__' --exclude='.pytest_cache' \
    -czf "$BACKUP_DIR/$ARCHIVE_NAME" \
    q_hypercore tests

echo ""
echo "=== 3. Verificación del archivo generado ==="
ls -lh "$BACKUP_DIR/$ARCHIVE_NAME"
sha256sum "$BACKUP_DIR/$ARCHIVE_NAME"

echo ""
echo "=== 4. Listado de contenido del backup (confirmación) ==="
tar -tzf "$BACKUP_DIR/$ARCHIVE_NAME" | head -50

echo ""
echo "Backup completo en: $BACKUP_DIR/$ARCHIVE_NAME"
echo "Manifest en:        $BACKUP_DIR/$MANIFEST_NAME"
