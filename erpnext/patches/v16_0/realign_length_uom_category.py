import json
from collections import defaultdict

import frappe


def execute():
	uom_conversion_data = json.loads(
		open(
			frappe.get_app_path("erpnext", "setup", "setup_wizard", "data", "uom_conversion_data.json")
		).read()
	)

	category_uoms = defaultdict(set)
	for row in uom_conversion_data:
		category = row.get("category")
		if not category:
			continue
		category_uoms[category].update((row["from_uom"], row["to_uom"]))

	for category, uoms in category_uoms.items():
		uoms = list(uoms)

		if not frappe.db.exists("UOM Category", category):
			frappe.get_doc({"doctype": "UOM Category", "category_name": category}).insert()

		existing_categories = frappe.get_all(
			"UOM Conversion Factor",
			or_filters={"from_uom": ["in", uoms], "to_uom": ["in", uoms]},
			distinct=True,
			pluck="category",
		)
		for existing in existing_categories:
			if not existing or existing == category:
				continue

			frappe.rename_doc("UOM Category", existing, category, force=True, show_alert=False)
