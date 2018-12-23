# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import today
from erpnext.accounting.utils import get_fiscal_year
from erpnext.stock.stock_ledger import update_entries_after

def execute():
	try:
		year_start_date = get_fiscal_year(today())[1]
	except:
		return

	if year_start_date:
		items = frappe.db.sql("""select distinct item_code, warehouse from `tabStock Ledger Entry`
			where ifnull(serial_no, '') != '' and actual_qty > 0 and incoming_rate=0""", as_dict=1)

		for d in items:
			try:
				update_entries_after({
					"item_code": d.item_code,
					"warehouse": d.warehouse,
					"posting_date": year_start_date
				}, allow_zero_rate=True)
			except:
				pass