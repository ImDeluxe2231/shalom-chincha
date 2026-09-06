# Módulo 4: seguimiento operativo y almacén

## Objetivo

Controlar el recorrido de un envío desde su recepción física en la agencia de
origen hasta que queda disponible para recojo en destino, conservando una
trazabilidad verificable por trabajador, fecha, agencia y ubicación.

## Flujo autorizado

| Estado actual | Operación | Nuevo estado | Dato obligatorio |
| --- | --- | --- | --- |
| Registrado | Confirmar recepción | Recibido en agencia | — |
| Recibido en agencia | Ingresar a almacén | En almacén de origen | Ubicación de origen |
| En almacén de origen | Registrar despacho | Despachado | Manifiesto, vehículo o vuelo |
| Despachado | Iniciar tránsito | En tránsito | — |
| En tránsito | Confirmar llegada | Recibido en destino | Ubicación de destino |
| Recibido en destino | Preparar recojo | Disponible para recojo | — |

No se permiten saltos, retrocesos ni modificaciones de eventos históricos. El
Módulo 5 continuará desde `Disponible para recojo` y agregará entregas e
incidencias.

## Responsabilidades por perfil

- **Administrador:** supervisa, procesa movimientos y configura ubicaciones.
- **Administrativo:** consulta la trazabilidad para atención en ventanilla.
- **Operativo:** recibe, almacena, despacha y actualiza el tránsito.
- **Cliente:** consulta únicamente información logística con orden y código.

## Evidencia registrada

Cada movimiento guarda el envío, estado anterior, estado nuevo, agencia,
ubicación cuando corresponde, referencia de transporte, observación interna,
trabajador responsable y fecha/hora automática.

## Seguridad de la consulta pública

- Requiere número de orden y código privado de seis dígitos.
- Limita intentos fallidos consecutivos durante cinco minutos.
- No muestra teléfonos, documentos, nombres, costos ni contenido declarado.
- Presenta descripciones públicas del estado, no observaciones internas.

## Prueba manual recomendada

1. Registrar un envío con `ventanilla`.
2. Ingresar con `almacen` y abrir **Seguimiento**.
3. Procesar cada estado respetando los datos obligatorios.
4. Confirmar que los eventos aparezcan en orden y no puedan editarse.
5. Abrir el comprobante y escanear el QR.
6. Verificar la consulta con una combinación incorrecta y después con la correcta.
7. Ingresar con `ventanilla` y comprobar que puede consultar, pero no actualizar.
