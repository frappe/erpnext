"""Configuración inicial para Centro Recreativo La Ensenada.

Este script crea una base operativa para un centro recreativo con:
- Piscinas
- Restaurante (~15 mesas)
- Alquiler de local para eventos
"""

from __future__ import annotations

import frappe
from frappe import _

from erpnext import get_default_company


ITEM_GROUP_TREE = {
	"Piscinas": [
		"Entrada Adulto",
		"Entrada Niño",
		"Day Pass Familiar",
	],
	"Restaurante": [
		"Sopas",
		"Asados",
		"Fritanga Nicaragüense",
		"Bebidas Alcohólicas",
		"Bebidas No Alcohólicas",
	],
	"Eventos": [
		"Alquiler de Local",
		"Alquiler de Mobiliario",
		"Decoración",
	],
}

MENU_ITEMS = [
	("Sopa de Res", "Sopas", 6.5),
	("Sopa de Gallina India", "Sopas", 7.0),
	("Asado de Res", "Asados", 9.5),
	("Pollo Asado", "Asados", 8.0),
	("Vigorón", "Fritanga Nicaragüense", 5.5),
	("Nacatamal", "Fritanga Nicaragüense", 4.0),
	("Cerveza Nacional", "Bebidas Alcohólicas", 2.5),
	("Ron con Cola", "Bebidas Alcohólicas", 3.5),
	("Limonada", "Bebidas No Alcohólicas", 2.0),
	("Refresco Natural", "Bebidas No Alcohólicas", 2.2),
	("Entrada Piscina Adulto", "Entrada Adulto", 3.0),
	("Entrada Piscina Niño", "Entrada Niño", 2.0),
	("Alquiler Salón de Eventos (8h)", "Alquiler de Local", 150.0),
]

SERVICE_ITEMS = {
	"Alquiler Salón de Eventos (8h)",
	"Entrada Piscina Adulto",
	"Entrada Piscina Niño",
}


@frappe.whitelist()
def setup_la_ensenada(company: str | None = None) -> dict[str, int]:
	"""Configura catálogo y estructura básica para La Ensenada.

	Se puede ejecutar con:
		bench --site <sitio> execute erpnext.setup.la_ensenada.setup_la_ensenada
	"""
	company = company or get_default_company()
	if not company:
		frappe.throw(_("No se encontró una compañía por defecto. Crea una Company primero."))

	created = {
		"item_groups": 0,
		"items": 0,
		"restaurant_tables": 0,
		"service_templates": 0,
	}

	all_root = _ensure_item_group("All Item Groups", "", is_group=1)
	for group_name, subgroups in ITEM_GROUP_TREE.items():
		created["item_groups"] += _ensure_item_group(group_name, all_root, is_group=1)
		for subgroup in subgroups:
			created["item_groups"] += _ensure_item_group(subgroup, group_name, is_group=0)

	for item_name, item_group, price in MENU_ITEMS:
		created["items"] += _ensure_item(item_name, item_group, price, is_service=item_name in SERVICE_ITEMS)

	created["restaurant_tables"] += _ensure_restaurant_tables(count=15)
	created["service_templates"] += _disable_irrelevant_service_templates(company)

	frappe.db.commit()
	return created


def _ensure_item_group(name: str, parent_item_group: str, is_group: int = 0) -> int:
	if frappe.db.exists("Item Group", name):
		return 0

	frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": name,
			"parent_item_group": parent_item_group,
			"is_group": is_group,
		}
	).insert(ignore_permissions=True)
	return 1


def _ensure_item(item_name: str, item_group: str, rate: float, is_service: bool = False) -> int:
	if frappe.db.exists("Item", item_name):
		return 0

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_name,
			"item_name": item_name,
			"item_group": item_group,
			"stock_uom": "Nos",
			"is_stock_item": 0 if is_service else 1,
			"include_item_in_manufacturing": 0,
		}
	)
	item.insert(ignore_permissions=True)

	if frappe.db.exists("Item Price", {"item_code": item_name, "price_list": "Standard Selling"}):
		return 1

	frappe.get_doc(
		{
			"doctype": "Item Price",
			"price_list": "Standard Selling",
			"item_code": item_name,
			"price_list_rate": rate,
		}
	).insert(ignore_permissions=True)
	return 1


def _ensure_restaurant_tables(count: int = 15) -> int:
	"""Crea mesas si existe el DocType de mesas del módulo de restaurante."""
	table_doctype = _detect_restaurant_table_doctype()
	if not table_doctype:
		return 0

	created = 0
	for idx in range(1, count + 1):
		table_name = f"Mesa-{idx:02d}"
		if frappe.db.exists(table_doctype, table_name):
			continue

		doc = frappe.new_doc(table_doctype)
		if doc.meta.has_field("table_name"):
			doc.table_name = table_name
		if doc.meta.has_field("no_of_seats"):
			doc.no_of_seats = 4
		doc.insert(ignore_permissions=True)
		created += 1

	return created


def _detect_restaurant_table_doctype() -> str | None:
	candidates = ("Restaurant Table", "Table")
	for dt in candidates:
		if frappe.db.exists("DocType", dt):
			return dt
	return None


def _disable_irrelevant_service_templates(company: str) -> int:
	"""Desactiva plantillas que no aplican para un centro recreativo.

	No borra datos; únicamente deshabilita para reducir ruido operativo.
	"""
	if not frappe.db.exists("DocType", "Service Level Agreement"):
		return 0

	to_disable = frappe.get_all(
		"Service Level Agreement",
		filters={"enabled": 1, "company": ["in", [company, ""]]},
		pluck="name",
	)
	for name in to_disable:
		frappe.db.set_value("Service Level Agreement", name, "enabled", 0)
	return len(to_disable)
