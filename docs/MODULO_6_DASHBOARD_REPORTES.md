# Módulo 6: dashboard, indicadores y reportes

## Objetivo

Transformar los registros generados por los módulos 1 al 5 en información útil
para supervisar la operación, detectar incidencias y sustentar decisiones de la
agencia Shalom Chincha.

## Dashboard

El panel principal está disponible para los tres perfiles y admite filtros por:

- fecha inicial y final, con un máximo de 366 días;
- agencia relacionada con la operación;
- modalidad terrestre o aérea.

Los indicadores se calculan directamente desde la base de datos, sin duplicar
información en tablas auxiliares.

| Indicador | Criterio |
| --- | --- |
| Envíos registrados | Órdenes creadas dentro del periodo |
| Entregas completadas | Constancias emitidas dentro del periodo |
| Envíos en operación | Órdenes en estados no terminales, según agencia y transporte |
| Incidencias activas | Casos abiertos o en revisión |
| Efectividad de entrega | Envíos del periodo que terminaron entregados / envíos no anulados |
| Tasa de incidencia | Envíos del periodo afectados / envíos registrados |
| Tiempo promedio | Horas entre registro y entrega |
| Cumplimiento | Entregas efectuadas hasta la fecha estimada |
| Ingresos confirmados | Costo + seguro - descuento de órdenes pagadas |

## Gráficos

- tendencia diaria de envíos registrados;
- distribución de estados actuales;
- entregas completadas por agencia;
- incidencias agrupadas por gravedad.

Los gráficos respetan el periodo y filtros seleccionados. También se muestran
las incidencias activas y entregas más recientes para facilitar la supervisión.

## Centro de reportes

El administrador puede consultar tres reportes:

1. Envíos: orden, registro, participantes, ruta, estado, pago y total.
2. Entregas: fecha, receptor, modalidad, agencia, bultos y responsable.
3. Incidencias: código, envío, tipo, gravedad, situación y asignación.

La vista previa utiliza paginación y conserva los mismos filtros que la
exportación.

## Formatos de exportación

- CSV con codificación UTF-8 y separador compatible con Excel en español.
- Excel XLSX con encabezado visual, columnas dimensionadas, primera fila fija y autofiltro.
- PDF horizontal y paginado para archivo o impresión.

Los archivos se generan localmente en el servidor. No se envían datos a
servicios externos.

## Permisos

| Función | Administrador | Administrativo | Operativo |
| --- | --- | --- | --- |
| Consultar dashboard | Sí | Sí | Sí |
| Filtrar indicadores y gráficos | Sí | Sí | Sí |
| Ver indicador de ingresos | Sí | Sí | No |
| Abrir centro de reportes | Sí | No | No |
| Exportar CSV, Excel o PDF | Sí | No | No |
| Consultar bitácora de exportaciones | Sí | No | No |

Las rutas de reportes y exportación validan el rol dentro del servidor. Ocultar
el enlace en el menú no constituye la única medida de seguridad.

## Auditoría

Cada descarga registra automáticamente:

- tipo de reporte;
- formato generado;
- filtros aplicados;
- cantidad de filas;
- administrador solicitante;
- fecha y hora.

La bitácora no puede modificarse ni eliminarse mediante el sistema.

## Prueba manual recomendada

1. Ingresar con los tres perfiles y comprobar que todos ven el dashboard.
2. Confirmar que el operativo no visualiza ingresos ni el menú Reportes.
3. Aplicar un rango de fechas, una agencia y una modalidad.
4. Ingresar como administrador y abrir el centro de reportes.
5. Alternar entre envíos, entregas e incidencias.
6. Descargar cada reporte en CSV, Excel y PDF.
7. Abrir los archivos y comprobar los filtros aplicados.
8. Verificar que las descargas aparezcan en la bitácora.
