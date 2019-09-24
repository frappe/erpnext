from __future__ import unicode_literals
import frappe
from frappe.utils import getdate

def execute():
	domain_settings = frappe.get_doc('Domain Settings')
	active_domains = [d.domain for d in domain_settings.active_domains]

	if "Healthcare" not in active_domains:
		items = ["TTT", "MCH", "LDL", "GTT", "HDL", "BILT", "BILD", "BP", "BS"]
		for item_code in items:
			try:
				item = frappe.db.get_value("Item", {"item_code": item_code}, ["name", "creation"], as_dict=1)
				if item and getdate(item.creation) >= getdate("2017-11-10"):
					frappe.delete_doc("Item", item.name)
			except:
				pass