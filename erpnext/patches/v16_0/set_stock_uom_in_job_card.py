import frappe


def execute():
	job_cards = frappe.get_all(
		"Job Card",
		filters={"stock_uom": ("is", "not set")},
		fields=["name", "finished_good", "production_item"],
	)

	if not job_cards:
		return

	item_codes = {code for row in job_cards if (code := row.finished_good or row.production_item)}
	if not item_codes:
		return

	stock_uoms = dict(
		frappe.get_all(
			"Item",
			filters={"name": ("in", list(item_codes))},
			fields=["name", "stock_uom"],
			as_list=True,
		)
	)

	updates = {}
	for row in job_cards:
		stock_uom = stock_uoms.get(row.finished_good or row.production_item)
		if stock_uom:
			updates[row.name] = {"stock_uom": stock_uom}

	if not updates:
		return

	frappe.db.bulk_update("Job Card", updates)
