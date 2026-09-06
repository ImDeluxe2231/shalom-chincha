# Módulo 5: entregas, incidencias y comprobantes

## Objetivo

Cerrar el ciclo del envío con una entrega verificable y gestionar de forma
controlada cualquier incidencia que interrumpa su operación.

## Entrega

La entrega solo puede registrarse desde `Disponible para recojo` y exige:

- modalidad coherente con el servicio contratado;
- identificación de destinatario o persona autorizada;
- documento válido y relación con el destinatario cuando corresponda;
- código privado de seguimiento;
- confirmación del pago cuando estaba pendiente;
- verificación de todos los bultos y su condición;
- aceptación expresa del trabajador responsable.

Al confirmar, el sistema cambia el envío a `Entregado`, registra un evento de
trazabilidad y genera una constancia inalterable con QR y código UUID. La
verificación pública enmascara el nombre y el documento del receptor.

## Incidencias

Una incidencia puede reportarse mientras el envío no esté finalizado. El
sistema conserva el estado interrumpido y cambia temporalmente la orden a
`Con incidencia`.

Datos registrados:

- tipo y gravedad;
- agencia y descripción interna;
- mensaje prudente para el cliente;
- evidencia opcional JPG, PNG o PDF de hasta 5 MB;
- trabajador que reporta;
- responsable asignado;
- solución, administrador y fecha de resolución.

No se permite más de una incidencia activa por envío. Al resolverla, la orden
retoma exactamente el estado anterior. El historial de reporte, asignación y
resolución es inalterable.

## Permisos

| Función | Administrador | Administrativo | Operativo | Público |
| --- | --- | --- | --- | --- |
| Consultar entregas | Sí | Sí | Sí | No |
| Registrar entrega | Sí | Sí | Sí | No |
| Reportar incidencia | Sí | Sí | Sí | No |
| Asignar y resolver | Sí | No | No | No |
| Ver evidencia | Sí | Sí | Sí | No |
| Verificar constancia | Sí | Sí | Sí | Sí, con UUID |

## Prueba manual recomendada

1. Llevar una orden hasta `Disponible para recojo`.
2. Confirmar una entrega con pago pendiente y comprobar que queda pagada.
3. Imprimir la constancia y abrir el QR en una ventana privada.
4. Crear otro envío, reportar una incidencia y revisar la consulta pública.
5. Ingresar como administrador, asignar el caso y registrar la solución.
6. Comprobar que el envío retoma su estado previo y puede continuar.
