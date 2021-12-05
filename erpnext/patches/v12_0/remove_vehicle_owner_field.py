import frappe


def execute():
	dts = ['Quotation', 'Sales Order', 'Delivery Note',
		'Supplier Quotation', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice']

	frappe.db.sql("""
		delete
		from `tabCustom Field`
		where dt in %s and fieldname in ('vehicle_owner', 'vehicle_owner_name')
	""", [dts])
