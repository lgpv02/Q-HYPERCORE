#!/data/data/com.termux/files/usr/bin/bash
# harness/runner.sh - Auditor de evidencia para Q-HYPERCORE
# No se autocertifica. Reporta hechos crudos: exit_code, hash, ruta del log.

set -u
PROJECT_ROOT="$(pwd)"
EVIDENCE_DIR="${PROJECT_ROOT}/evidence"
mkdir -p "$EVIDENCE_DIR"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TIMESTAMP_SAFE=$(date -u +"%Y%m%d_%H%M%SZ")
MANIFEST_FILE="${EVIDENCE_DIR}/test_results.json"
LOG_FILE="${EVIDENCE_DIR}/pytest_output_${TIMESTAMP_SAFE}.log"

echo "=== [1/3] Verificación sintáctica (py_compile) ==="
SYNTAX_OK=1
find . -name "*.py" -not -path "*/.*" -print0 | xargs -0 python3 -m py_compile 2>"${EVIDENCE_DIR}/syntax_errors_${TIMESTAMP_SAFE}.log" || SYNTAX_OK=0

if [ "$SYNTAX_OK" -eq 0 ]; then
    echo "❌ Fallo de sintaxis. Ver evidence/syntax_errors_${TIMESTAMP_SAFE}.log" >&2
fi

echo "=== [2/3] Ejecución de pruebas (pytest) ==="
python3 -m pytest tests/ -v 2>&1 | tee "$LOG_FILE"
TEST_EXIT_CODE=${PIPESTATUS[0]}

echo "=== [3/3] Hash de inmutabilidad del código ==="
HASH_CODE=$(find . -maxdepth 3 -name "*.py" -type f -print0 2>/dev/null | xargs -0 sha256sum 2>/dev/null | sort | sha256sum | cut -d' ' -f1)

FINAL_EXIT=$TEST_EXIT_CODE
[ "$SYNTAX_OK" -eq 0 ] && FINAL_EXIT=1

cat <<EOF > "$MANIFEST_FILE"
{
  "timestamp": "${TIMESTAMP}",
  "project": "Q-HYPERCORE",
  "syntax_ok": $([ "$SYNTAX_OK" -eq 1 ] && echo "true" || echo "false"),
  "pytest_exit_code": ${TEST_EXIT_CODE},
  "final_exit_code": ${FINAL_EXIT},
  "code_sha256": "${HASH_CODE}",
  "log_file": "$(basename "$LOG_FILE")"
}
EOF

echo ""
echo "=== Manifest generado: ${MANIFEST_FILE} ==="
echo "=== Log crudo:         ${LOG_FILE} ==="
echo "(El nivel de evidencia se asigna después de revisar ambos, no aquí.)"

exit $FINAL_EXIT
