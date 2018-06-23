# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.stock.stock_balance import update_bin_qty, get_reserved_qty

def execute():
	""" Set the Serial Numbers in Sales Invoice Item from Delivery Note Item """

	frappe.reload_doc("stock", "doctype", "serial_no")

	frappe.db.sql(""" update `tabSales Invoice Item` sii inner join 
		`tabDelivery Note Item` dni on sii.dn_detail=dni.name and  sii.qty=dni.qty
		set sii.serial_no=dni.serial_no where sii.parent IN (select si.name 
			from `tabSales Invoice` si where si.update_stock=0 and si.docstatus=1)""")

	items = frappe.db.sql(""" select  sii.parent, sii.serial_no from  `tabSales Invoice Item` sii
		left join `tabSales Invoice` si on sii.parent=si.name
		where si.docstatus=1 and si.update_stock=0""", as_dict=True)

	for item in items:
		sales_invoice = item.get("parent", None)
		serial_nos = item.get("serial_no", "")

		if not sales_invoice or not serial_nos:
			continue

		serial_nos = ["'%s'"%frappe.db.escape(no) for no in serial_nos.split("\n")]

		frappe.db.sql("""
			UPDATE 
				`tabSerial No`
			SET 
				sales_invoice='{sales_invoice}'
			WHERE
				name in ({serial_nos})
			""".format(
				sales_invoice=frappe.db.escape(sales_invoice),
				serial_nos=",".join(serial_nos)
			)
		)