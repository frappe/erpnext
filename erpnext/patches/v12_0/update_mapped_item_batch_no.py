import frappe


def execute():
	frappe.db.sql("""
		update `tabSales Invoice Item` si
		inner join `tabDelivery Note Item` di on di.name = si.delivery_note_item
		set si.batch_no = di.batch_no
		where ifnull(si.batch_no, '') = '' and ifnull(di.batch_no, '') != ''
	""")

	frappe.db.sql("""
		update `tabPurchase Invoice Item` pi
		inner join `tabPurchase Receipt Item` di on di.name = pi.purchase_receipt_item
		set pi.batch_no = di.batch_no
		where ifnull(pi.batch_no, '') = '' and ifnull(di.batch_no, '') != ''
	""")
