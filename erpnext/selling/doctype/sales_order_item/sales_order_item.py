# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.model.document import Document


class SalesOrderItem(Document):
	pass


def on_doctype_update():
	frappe.db.add_index("Sales Order Item", ["item_code", "warehouse"])
