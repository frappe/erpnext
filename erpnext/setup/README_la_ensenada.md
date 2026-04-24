# Implementación ERP para Centro Recreativo La Ensenada

## Contexto levantado en línea

Referencias públicas indican que **Centro Recreativo La Ensenada (Estelí)** opera con enfoque familiar y de eventos, incluyendo área de piscinas y restaurante; también se describe oferta de eventos y ambiente campestre.

## Alcance de la personalización

Este repositorio incluye el script `erpnext.setup.la_ensenada.setup_la_ensenada` para dejar una base lista para operar:

1. **Estructura comercial enfocada al negocio**
   - Grupos para `Piscinas`, `Restaurante` y `Eventos`.
   - Subgrupos de menú: `Sopas`, `Asados`, `Fritanga Nicaragüense`, `Bebidas Alcohólicas`, `Bebidas No Alcohólicas`.

2. **Catálogo inicial de ventas**
   - Ítems de comida y bebida.
   - Servicios de entradas de piscina.
   - Servicio de alquiler de salón para eventos.

3. **Mesas de restaurante**
   - Crea **15 mesas** automáticamente cuando existe el DocType de mesas de restaurante en la instalación.

4. **Reducción de ruido operativo**
   - Deshabilita plantillas de SLA activas para minimizar elementos que no aplican al flujo operativo típico del centro recreativo.

## Ejecución

```bash
bench --site <tu_sitio> execute erpnext.setup.la_ensenada.setup_la_ensenada
```

Parámetro opcional:

```bash
bench --site <tu_sitio> execute erpnext.setup.la_ensenada.setup_la_ensenada --kwargs "{'company':'Centro Recreativo La Ensenada'}"
```

## Nota

Este setup no elimina datos históricos. Si necesitas una limpieza más agresiva (módulos, workflows, reportes), conviene hacerlo como fase 2 con respaldo previo de base de datos.
