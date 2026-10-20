# Política de compromiso de entrega

## Alcance

Esta política se aplica a compromisos de entrega B2B gestionados desde el almacén `ALM-LIM`. La fecha operativa de referencia del escenario `LOG-001` es `2026-03-16`.

## Ventana estándar

La ventana estándar se calcula en días hábiles de lunes a viernes. Para la semilla `6739`, la ventana vigente es de 3 días hábiles y la capacidad normal es de 6 unidades por día. Estos valores provienen de la configuración del caso y deben mostrarse al iniciar la ejecución.

## Condiciones de una confirmación directa

Un compromiso puede confirmarse directamente cuando el cliente y el producto existen, la cantidad es válida, el stock disponible es suficiente, la fecha solicitada no es anterior a la ventana estándar y la capacidad normal de esa fecha cubre la cantidad.

## Datos que deben verificarse

Las políticas no reemplazan la consulta operacional. Antes de confirmar se debe verificar cliente, SKU, stock y reservas de capacidad en las fuentes transaccionales correspondientes.

## Información insuficiente

Si falta cliente, SKU, cantidad o fecha, el sistema debe pedir una aclaración. No debe inventar identificadores ni asumir condiciones comerciales o logísticas.
