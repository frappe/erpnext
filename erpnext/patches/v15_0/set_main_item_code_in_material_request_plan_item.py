import frappe


def execute():
	frappe.reload_doc("manufacturing", "doctype", "material_request_plan_item")

	if not frappe.db.has_column("Material Request Plan Item", "main_item_code"):
		return

	for row in get_material_request_plan_items():
		if row.main_item_code:
			continue

		main_item_code = get_main_item_code(row)
		if main_item_code:
			frappe.db.set_value(
				"Material Request Plan Item",
				row.name,
				"main_item_code",
				main_item_code,
				update_modified=False,
			)


def get_material_request_plan_items():
	return frappe.get_all(
		"Material Request Plan Item",
		fields=["name", "parent", "item_code", "sales_order", "main_item_code"],
	)


def get_main_item_code(row):
	return (
		get_main_item_code_from_sub_assembly(row)
		or get_main_item_code_from_sub_assembly_bom(row)
		or get_main_item_code_from_production_plan_bom(row)
	)


def get_main_item_code_from_sub_assembly(row):
	sub_assembly = frappe.db.get_value(
		"Production Plan Sub Assembly Item",
		get_filters(
			row,
			{
				"parent": row.parent,
				"production_item": row.item_code,
			},
		),
		"parent_item_code",
	)

	return sub_assembly


def get_main_item_code_from_sub_assembly_bom(row):
	for sub_assembly in get_sub_assembly_items(row):
		if item_exists_in_bom(row.item_code, sub_assembly.bom_no):
			return frappe.db.get_value("BOM", sub_assembly.bom_no, "item")


def get_main_item_code_from_production_plan_bom(row):
	for production_plan_item in get_production_plan_items(row):
		if item_exists_in_bom(row.item_code, production_plan_item.bom_no):
			return frappe.db.get_value("BOM", production_plan_item.bom_no, "item")


def get_sub_assembly_items(row):
	return frappe.get_all(
		"Production Plan Sub Assembly Item",
		filters=get_filters(row, {"parent": row.parent}),
		fields=["bom_no"],
	)


def get_production_plan_items(row):
	return frappe.get_all(
		"Production Plan Item",
		filters=get_filters(row, {"parent": row.parent}),
		fields=["bom_no"],
	)


def get_filters(row, filters):
	if row.sales_order:
		filters["sales_order"] = row.sales_order

	return filters


def item_exists_in_bom(item_code, bom_no):
	if not bom_no:
		return False

	return frappe.db.exists("BOM Item", {"parent": bom_no, "item_code": item_code}) or frappe.db.exists(
		"BOM Explosion Item", {"parent": bom_no, "item_code": item_code}
	)
