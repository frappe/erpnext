# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from erpnext.stock.get_item_details import get_conversion_factor

def execute():
	frappe.reload_doc('buying', 'doctype', 'request_for_quotation_item')

	frappe.db.sql("""UPDATE `tabRequest for Quotation Item`
			SET
				stock_uom = uom,
				conversion_factor = 1,
				stock_qty = qty""")