# Q-HYPERCORE — Registro de Gobernanza y Evidencia

## MILESTONE 0 — ROUTING CORE

Estado: VERIFIED
Fecha: 2026-09-03
Entorno: Termux / Android / aarch64-linux-android
Python: 3.14.6
Pytest: 9.1.1

### Evidencia primaria
- test_quantum_routing_thresholds: PASSED
- test_classical_and_llm_routing: PASSED
- Resultado: 2 passed in 0.05s
- Routing verificado: QUANTUM_HARDWARE, QUANTUM_SIMULATOR, QUANTUM_INSPIRED, LARGE_REASONING_LLM, CPU_CLASSIC

### Reconstruccion
engine.py no estaba presente en el filesystem de este dispositivo al iniciar esta sesion. Fue reconstruido desde la especificacion de diseno discutida previamente. No debe clasificarse como recuperacion de codigo historico ni como evidencia de que dicho codigo existio y se ejecuto con anterioridad en este entorno.

### Dependencia
Pydantic v2 no es viable en este entorno (ver Platform Constraint abajo). La implementacion actual usa dataclasses de la libreria estandar.

### Riesgo metodologico
Los reportes de estado pueden adelantarse al estado fisico real del filesystem. Un mismo componente puede aparecer como confirmado en una sesion y estar completamente ausente en otro dispositivo. Este patron ya se habia detectado en TradingSystem y genome-runtime-lite; Q-HYPERCORE confirma que es un riesgo recurrente del proyecto Tiburon en su conjunto, no un incidente aislado.

### Pendiente
- Estado 5: benchmarks comparativos de la funcion objetivo.
- Estado 6: integracion de adaptadores externos (quantum/, llm/, compression/).
- Estado 7: pruebas de estres y manejo de fallos simulados.

---

## PLATFORM CONSTRAINT: TERMUX / AARCH64

Las dependencias que requieran toolchains nativos no disponibles en el entorno objetivo no deben introducirse como requisito obligatorio sin validacion previa de instalacion y compilacion real.

En particular, Pydantic v2 no debe considerarse una dependencia disponible por defecto en Termux/aarch64. Cuando su instalacion requiera maturin/Rust y falle en el entorno objetivo, debera utilizarse una alternativa compatible (por ejemplo dataclasses), o trasladarse explicitamente el componente a un entorno de ejecucion compatible (servidor remoto, contenedor con glibc x86_64, etc.).

Esta restriccion es local a Q-HYPERCORE por ahora. No se extiende automaticamente a otros modulos de Corporacion Perdomo (Tiburon, AI Trading Operator) hasta que se tome una decision explicita en el Documento de Arquitectura Maestra.

La compatibilidad de cualquier dependencia debe verificarse mediante ejecucion real en el entorno destino, nunca mediante documentacion o instalacion reportada desde otro dispositivo.

### Definicion operativa de VERIFIED

Un componente solo puede marcarse VERIFIED cuando existe evidencia reproducible generada en el dispositivo/entorno actual: archivo presente en filesystem (confirmado con find/ls), tests ejecutados con salida de consola capturada, y ausencia de dependencias no resueltas. Documentacion, informes de otras sesiones, o instalaciones reportadas sin ejecucion local no constituyen evidencia suficiente.

---

## PLATFORM CONSTRAINT: TERMUX / AARCH64

Las dependencias que requieran toolchains nativos no disponibles en el entorno objetivo no deben introducirse como requisito obligatorio sin validacion previa de instalacion y compilacion real.

En particular, Pydantic v2 no debe considerarse una dependencia disponible por defecto en Termux/aarch64. Cuando su instalacion requiera maturin/Rust y falle en el entorno objetivo, debera utilizarse una alternativa compatible (por ejemplo dataclasses), o trasladarse explicitamente el componente a un entorno de ejecucion compatible (servidor remoto, contenedor con glibc x86_64, etc.).

Esta restriccion es local a Q-HYPERCORE por ahora. No se extiende automaticamente a otros modulos de Corporacion Perdomo (Tiburon, AI Trading Operator) hasta que se tome una decision explicita en el Documento de Arquitectura Maestra.

La compatibilidad de cualquier dependencia debe verificarse mediante ejecucion real en el entorno destino, nunca mediante documentacion o instalacion reportada desde otro dispositivo.

### Definicion operativa de VERIFIED

Un componente solo puede marcarse VERIFIED cuando existe evidencia reproducible generada en el dispositivo/entorno actual: archivo presente en filesystem (confirmado con find/ls), tests ejecutados con salida de consola capturada, y ausencia de dependencias no resueltas. Documentacion, informes de otras sesiones, o instalaciones reportadas sin ejecucion local no constituyen evidencia suficiente.
