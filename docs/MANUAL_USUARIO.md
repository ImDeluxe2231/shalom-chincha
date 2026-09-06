# Manual de usuario del sistema Shalom Chincha

## Inicio de sesión

1. Abra la dirección proporcionada por el administrador.
2. Ingrese usuario y contraseña.
3. Cambie la contraseña demostrativa antes de trabajar con datos reales.
4. Cierre la sesión al terminar, especialmente en equipos compartidos.

## Perfiles

### Administrador

Gestiona usuarios, clientes, agencias, ubicaciones, envíos, incidencias,
reportes, exportaciones y el centro de validación de tesis.

### Administrativo

Registra clientes y envíos, consulta el seguimiento y participa en la entrega.
No puede administrar usuarios, ejecutar movimientos de almacén ni acceder a la
base de investigación.

### Operativo

Consulta clientes y envíos, procesa recepción, almacén, despacho, tránsito,
llegada y entrega. No puede modificar clientes ni exportar información
administrativa.

## Flujo de trabajo

1. Registre o ubique al remitente y destinatario en `Clientes`.
2. Entre a `Envíos`, seleccione `Nuevo envío` y complete ruta, modalidad,
   paquetes, pago y costos.
3. Imprima el comprobante con QR.
4. El personal operativo abre `Seguimiento` y procesa los estados en orden.
5. Cuando el envío quede disponible, abra `Entregas`, valide identidad, código,
   pago y bultos.
6. Si ocurre un problema, utilice `Incidencias`. El administrador asigna y
   resuelve el caso antes de continuar el flujo.
7. Consulte indicadores en el panel principal y exporte reportes desde
   `Reportes` si tiene autorización.

## Consulta pública

El cliente ingresa número de orden y código privado desde `/seguimiento/`. El
código no debe publicarse ni compartirse con personas ajenas al envío.

## Centro de validación

El administrador ingresa a `Validación de tesis` y puede:

- digitalizar fichas de trazabilidad;
- digitalizar tiempos de respuesta;
- digitalizar cuestionarios Likert usando códigos anónimos P01 a P15;
- comparar pretest y postest;
- exportar las tres bases para SPSS.

No se registra al participante en una pantalla independiente: al guardar su
primer cuestionario, el sistema crea el código P01 a P15 y conserva al usuario
responsable automáticamente.

Los registros de investigación deben corresponder a observaciones reales.
