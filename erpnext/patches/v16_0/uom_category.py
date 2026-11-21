import json

import frappe


def execute():
	uom_data = json.loads(
		# nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal -- path is inside the app
		open(frappe.get_app_path("erpnext", "setup", "setup_wizard", "data", "uom_data.json")).read()
	)
	bulk_update_dict = {uom["uom_name"]: {"category": uom["category"]} for uom in uom_data}
	frappe.db.bulk_update("UOM", bulk_update_dict)
