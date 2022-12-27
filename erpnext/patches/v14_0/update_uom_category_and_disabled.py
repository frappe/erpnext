import frappe
from frappe import _
import json
from erpnext.setup.setup_wizard.operations.install_fixtures import create_missing_uom_category


def execute():
	uoms = json.loads(open(frappe.get_app_path("erpnext", "setup", "setup_wizard", "data", "uom_data.json")).read())
	for d in uoms:
		uom_name = frappe.db.get_value("UOM", _(d.get("uom_name")))
		if uom_name:
			if d.get("category"):
				create_missing_uom_category(d.get("category"))

			frappe.db.set_value("UOM", uom_name, {
				"category": _(d.get("category")),
				"disabled": d.get("disabled")
			}, None)
