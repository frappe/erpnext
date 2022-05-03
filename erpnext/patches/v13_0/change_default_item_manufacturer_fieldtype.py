import frappe


def execute():

	# Erase all default item manufacturers that dont exist.
	item = frappe.qb.DocType("Item")
	manufacturer = frappe.qb.DocType("Manufacturer")

	(
		frappe.qb.update(item)
		.set(item.default_item_manufacturer, None)
		.left_join(manufacturer)
		.on(item.default_item_manufacturer == manufacturer.name)
		.where(manufacturer.name.isnull() & item.default_item_manufacturer.isnotnull())
	).run()
