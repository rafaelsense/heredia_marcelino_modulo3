# Política de despacho extraordinario

## Definición

Un despacho extraordinario es una operación excepcional para atender una fecha incompatible con la capacidad o ventana normal. No es una modalidad automática ni elimina las validaciones de stock y datos maestros.

## Elegibilidad

El despacho extraordinario puede evaluarse desde el siguiente día hábil. Para `LOG-001`, duplica la capacidad diaria configurada, descuenta las reservas existentes y tiene un costo de USD 400. Si ni la capacidad extraordinaria cubre la cantidad, la solicitud se rechaza.

## Aprobación obligatoria

El supervisor de logística debe aprobar explícitamente la excepción antes de confirmar o registrar el compromiso. El sistema debe pausar el proceso, conservar el estado y reanudar con el mismo identificador de hilo.

## Rechazo de negocio

Stock insuficiente, cliente o SKU inexistente, fecha pasada, entrega el mismo día y capacidad extraordinaria insuficiente son resultados de negocio. No corresponde reintentarlos con los mismos datos.

## Registro y trazabilidad

La respuesta debe indicar motivo, costo, fuentes consultadas y decisión humana. El costo no se confirma mientras la aprobación esté pendiente o haya sido rechazada.
