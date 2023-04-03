# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class WorkOrderItem(Document):
	pass


def on_doctype_update():
	frappe.db.add_index("Work Order Item", ["item_code", "source_warehouse"])
