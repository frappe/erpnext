import json

import frappe


def execute():
	uom_data = json.loads(
		open(frappe.get_app_path("erpnext", "setup", "setup_wizard", "data", "uom_data.json")).read()
	)
	bulk_update_dict = {uom["uom_name"]: {"category": uom["category"]} for uom in uom_data}
	frappe.db.bulk_update("UOM", bulk_update_dict)
