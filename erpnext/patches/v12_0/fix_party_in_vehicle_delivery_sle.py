from __future__ import unicode_literals
import frappe, os
from frappe import _

def execute():
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_delivery')

	frappe.db.sql("""
		update `tabStock Ledger Entry` sle
		inner join `tabVehicle Delivery` t on sle.voucher_type='Vehicle Delivery' and sle.voucher_no=t.name
		set sle.party_type = 'Customer', sle.party = t.customer
	""")
