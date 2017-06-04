# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.modules import scrub, get_doctype_module

def execute():
	for dt in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
		frappe.reload_doc(get_doctype_module(dt), "doctype", scrub(dt))
		frappe.db.sql("""update `tab{0}` set base_discount_amount=discount_amount,
			discount_amount=discount_amount/conversion_rate""".format(dt))
