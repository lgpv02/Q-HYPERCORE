#!/data/data/com.termux/files/usr/bin/bash
# backup_q_hypercore.sh
# Genera backup automático del estado actual de Q-HYPERCORE.
# Incluye manifest SHA-256 para verificación de integridad.
# Uso: bash backup_q_hypercore.sh

set -e

PROJECT_ROOT=~/Q-HYPERCORE
BACKUP_DIR=~/backups_qhypercore
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="q_hypercore_backup_${TIMESTAMP}.tar.gz"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

echo "🔄 Iniciando backup de Q-HYPERCORE..."
echo "   Ubicación: $PROJECT_ROOT"
echo "   Destino:   $BACKUP_PATH"
echo ""

# Generar manifest SHA-256 de archivos principales
echo "📋 Generando manifest de integridad..."
cd "$PROJECT_ROOT"

MANIFEST_FILE="$BACKUP_DIR/manifest_${TIMESTAMP}.sha256"
{
    echo "# Manifest SHA-256 para Q-HYPERCORE"
    echo "# Generado: $(date)"
    echo "# Propósito: Verificar integridad del backup"
    echo ""
    find q_hypercore tests -type f -name "*.py" 2>/dev/null | sort | xargs sha256sum
    echo ""
    echo "# Documentación:"
    find . -maxdepth 1 -type f \( -name "*.md" -o -name "*.txt" \) 2>/dev/null | sort | xargs sha256sum
} > "$MANIFEST_FILE"

echo "✅ Manifest guardado en: $MANIFEST_FILE"
echo ""

# Crear tar.gz
echo "📦 Comprimiendo archivos..."
tar -czf "$BACKUP_PATH" \
    q_hypercore/ \
    tests/ \
    *.md \
    *.txt \
    *.sh \
    .pytest_cache/ \
    MANIFEST.sha256 \
    2>/dev/null || true

if [ ! -f "$BACKUP_PATH" ]; then
    echo "❌ Error: No se pudo crear el backup."
    exit 1
fi

# Verificar integridad del backup
BACKUP_SIZE=$(ls -lh "$BACKUP_PATH" | awk '{print $5}')
BACKUP_HASH=$(sha256sum "$BACKUP_PATH" | awk '{print $1}')

echo "✅ Backup creado exitosamente:"
echo "   Archivo:  $BACKUP_NAME"
echo "   Tamaño:   $BACKUP_SIZE"
echo "   SHA-256:  $BACKUP_HASH"
echo ""

# Generar archivo de verificación
VERIFY_FILE="$BACKUP_DIR/verify_${TIMESTAMP}.txt"
{
    echo "VERIFICACIÓN DE BACKUP"
    echo "====================="
    echo ""
    echo "Fecha:      $(date)"
    echo "Archivo:    $BACKUP_NAME"
    echo "Ruta:       $BACKUP_PATH"
    echo "Tamaño:     $BACKUP_SIZE"
    echo "SHA-256:    $BACKUP_HASH"
    echo ""
    echo "Para verificar integridad:"
    echo "  sha256sum -c $MANIFEST_FILE"
    echo ""
    echo "Para verificar tar.gz:"
    echo "  sha256sum \"$BACKUP_PATH\""
    echo "  Debe coincidir: $BACKUP_HASH"
    echo ""
    echo "Para extraer:"
    echo "  cd ~"
    echo "  tar -xzf \"$BACKUP_PATH\""
} > "$VERIFY_FILE"

echo "📄 Archivo de verificación: $VERIFY_FILE"
echo ""

# Listar contenido del backup
echo "📋 Contenido del backup:"
tar -tzf "$BACKUP_PATH" | head -20
echo "   ... (más archivos)"
echo ""

# Resumen final
echo "================================"
echo "✅ BACKUP COMPLETADO EXITOSAMENTE"
echo "================================"
echo ""
echo "Ubicación:  $BACKUP_DIR/"
echo "Archivos generados:"
echo "  - $BACKUP_NAME (backup comprimido)"
echo "  - manifest_${TIMESTAMP}.sha256 (hashes de integridad)"
echo "  - verify_${TIMESTAMP}.txt (instrucciones de verificación)"
echo ""
echo "Para futuras recuperaciones, consulte:"
echo "  ~/Q-HYPERCORE/RECONNECTION_PROTOCOL.md"
echo ""
