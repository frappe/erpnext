# Implementation Strategy

Antes de que empieces a manejar todas tus operaciones en ERPNext, primero
deberías estar familiarizado con el sistema y los términos que utiliza.
	Por esa razón recomendamos que la implementación pase en dos fases.

  * La **Fase de Prueba**, donde introduces información de prueba que representan sus transacciones del día a día y la **Fase de Producción**, donde comenzamos a introducir información real.

### Fase de Prueba

  * Leer el manual
  * Crea una cuenta gratis en [https://erpnext.com](https://erpnext.com) (La forma más facíl de experimental).
  * Crea su primer Cliente, Suplidor y Producto. Agrega varios de estos para que se familiarice con ellos.
  * Crea un Grupo de Clientes, Grupo de Productos, Almacenes, Grupo de Suplidores, para que puedas clasificar sus productos.
  * Completar un ciclo estandar de ventas - Iniciativa > Oportunidad > Cotización > Orden de Venta > Nota de Entrega > Factura de Venta > Pago (Entrada de diario)
  * Completa un ciclo estandar de compra - Solicitud de Material > Orden de Compra > Recibo de Compra > Pagos (Entrada de diario).
  * Completar un ciclo de manofactura (si aplica) - BOM > Herramienta de Planificación de Producción > Orden de Producción > Problema de material
  * Replicar un escenario de su día a día dentro del sistema.
  * Crea un custom fields, formato de impresión, etc como sea requerido.

### Fase de Producción

Una vez ya estes falimiliarizado con ERPNext, inicia introduciendo la información real!

  * Borra toda la información de prueba de la cuenta o inicia con una nueva instalación.
  * Si solo quieres borrar las transacciones y no las demás informaciones sobre Productos, Clientes, Suplidores, BOM etc, puedes dar click en Eliminar Transacciones de su compañia y inicia desde cero. Para hacerlo, abre el registro de la compañia via Setup > Masters > Company y eliminar las transacciones de su compañia clickeando en el botón **Eliminar las transacciones de la compañia** al final del formulario de la compañia.
  * También puedes configurar una nueva cuenta en [https://erpnext.com](https://erpnext.com), y usa los 30 días gratis. [Encuentra mas formas de usar ERPNext](/introduction/getting-started-with-erpnext)
  * Configura todos los módulos con Grupos de Clientes, Grupos de Productos, Almacenes, BOMs etc.
  * Importar Clientes, Suplidores, Productos, Contactos y Direcciones usando la Herramienta de Importación de Data.
  * Importar el inventario de apertura usando la Herramienta de Reconciliación de Inventario.
  * Crear la entrada de apertura de cuenta usando la Entrada de Diario y crea facturas de ventas pendientes y facturas de compra.
  * Si necesitas ayuda, [puedes pagar por soporte](https://erpnext.com/pricing) o [preguntar en el foro de la comunidad](https://discuss.erpnext.com).

{next}
