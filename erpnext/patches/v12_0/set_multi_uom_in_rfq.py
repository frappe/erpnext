# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from erpnext.stock.get_item_details import get_conversion_factor

def execute():
	frappe.reload_doc('buying', 'doctype', 'request_for_quotation_item')

	for rfq_item in frappe.db.sql("""SELECT name, item_code, uom, qty FROM `tabRequest for Quotation Item` WHERE docstatus<2""", as_dict=1):
		item_code, uom, qty = rfq_item.get("item_code"), rfq_item.get("uom"), rfq_item.get("qty")
		conversion_factor = get_conversion_factor(item_code, uom).get("conversion_factor") or 1.0

		filters = {
			"name" : rfq_item.get("name"),
			"stock_uom" : frappe.db.get_value("Item", item_code, "stock_uom"),
			"conversion_factor" : conversion_factor,
			"stock_qty" : flt(qty) * flt(conversion_factor)
		}

		frappe.db.sql("""UPDATE `tabRequest for Quotation Item`
			SET
				stock_uom= %(stock_uom)s,
				conversion_factor = %(conversion_factor)s,
				stock_qty = %(stock_qty)s
			WHERE
				name = %(name)s""", filters)