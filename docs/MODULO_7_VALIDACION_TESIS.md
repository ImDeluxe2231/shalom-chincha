# Módulo 7: validación, medición y cierre de Tesis II

## Finalidad

Este módulo conecta el sistema web con la operacionalización de la variable
dependiente presentada en la tesis. Su propósito es conservar evidencia real y
auditable del pretest y postest sin mezclarla con los datos demostrativos.

Solo el administrador puede ingresar al centro de validación, registrar
instrumentos o descargar la base para SPSS.

## Indicador 1: trazabilidad de los envíos

Cada ficha registra:

- fase: pretest o postest;
- fecha de observación;
- total de envíos registrados;
- envíos rastreados correctamente;
- observación y trabajador que digitalizó la ficha.

El sistema aplica exactamente la fórmula del Anexo 2:

`(envíos rastreados correctamente / total de envíos registrados) × 100`

La comparación global utiliza los totales acumulados de cada fase, evitando el
sesgo que produciría promediar porcentajes de días con volúmenes diferentes.

## Indicador 2: tiempos de respuesta

La ficha diferencia dos operaciones:

1. consulta del estado de un envío;
2. actualización del estado de un paquete.

Se registran inicio y finalización. La diferencia se calcula automáticamente en
segundos y se presenta en minutos. El centro muestra el promedio general y los
promedios separados por tipo de operación.

Cada medición se registra de forma controlada para mantener el mismo protocolo
en el pretest y el postest.

## Indicador 3: eficiencia administrativa y operativa

Los participantes se identifican mediante códigos anónimos (P01 a P15). No se
deben registrar nombres, DNI, teléfonos ni correos en este módulo.
El participante se crea automáticamente al guardar su primer cuestionario, por
lo que no existe una pantalla separada que pueda dejar registros incompletos.

El cuestionario contiene los diez ítems del Anexo 4 y utiliza la escala:

- 1: muy insatisfecho;
- 2: insatisfecho;
- 3: neutral;
- 4: satisfecho;
- 5: muy satisfecho.

El sistema calcula el promedio total, el promedio administrativo (preguntas 1
a 5), el promedio operativo (preguntas 6 a 10) y el alfa de Cronbach cuando
existen respuestas suficientes y variabilidad estadística.

## Exportación para SPSS

La descarga `shalom_validacion_tesis.zip` contiene:

- `01_trazabilidad.csv`;
- `02_tiempos_respuesta.csv`;
- `03_cuestionario_eficiencia.csv`;
- `LEEME.txt`.

Los CSV usan UTF-8 y punto y coma como delimitador. En SPSS deben importarse
como archivos separados. La descarga contiene únicamente las tres bases que
corresponden a los indicadores definidos en la tesis.

## Reglas de integridad

- No usar el comando de datos demostrativos para producir resultados de tesis.
- No inventar ni completar respuestas faltantes.
- Aplicar los instrumentos a los mismos participantes en ambas fases.
- Conservar fichas originales, consentimiento informado y archivos SPSS.
- Registrar correcciones metodológicas en una bitácora externa firmada.
- Realizar el análisis inferencial con la orientación de la asesora.
