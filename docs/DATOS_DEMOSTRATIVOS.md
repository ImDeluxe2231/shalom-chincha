# Datos demostrativos realistas

## Propósito

El dashboard no obtiene información del archivo `.env`. Los indicadores y
gráficos se calculan desde `db.sqlite3` o desde la base configurada en
producción. Este comando permite preparar una demostración académica sin
registrar manualmente cientos de operaciones.

## Carga recomendada

```powershell
python manage.py cargar_datos_demo
```

La configuración predeterminada crea:

- 140 clientes naturales y empresas;
- 360 envíos en 120 días;
- rutas entre las agencias disponibles;
- transporte terrestre y aéreo cuando la ruta lo admite;
- uno o varios paquetes por envío;
- costos, seguros, descuentos y pagos pendientes o confirmados;
- eventos históricos desde el registro hasta el estado actual;
- envíos en todos los estados operativos;
- entregas conformes y con observaciones;
- incidencias bajas, medias, altas y críticas;
- casos abiertos, en revisión y resueltos.

## Seguridad

- No modifica ni elimina registros existentes.
- Marca los registros generados con `[DEMO-MASIVO-2027]`.
- Si detecta una carga anterior, se detiene sin duplicar datos.
- Toda la operación se ejecuta en una transacción: si ocurre un error, el lote
  incompleto se revierte.

## Cantidades personalizadas

```powershell
python manage.py cargar_datos_demo --clientes 80 --envios 180 --dias 90
```

Los mínimos son 20 clientes, 18 envíos y 30 días. El periodo máximo permitido
es 730 días.

Para agregar deliberadamente otro lote:

```powershell
python manage.py cargar_datos_demo --agregar
```

No se recomienda `--agregar` para una demostración normal, ya que la carga
predeterminada es suficiente para poblar los gráficos y reportes.

## Resultado esperado

Al abrir el dashboard con el filtro de los últimos 30 días deben aparecer:

- varios puntos en el gráfico de tendencia;
- diferentes estados en el gráfico circular;
- entregas distribuidas entre agencias;
- incidencias en más de un nivel de gravedad;
- indicadores de pagos, cumplimiento, ingresos y tiempos promedio.
