import frappe


def execute():
	dts = [
		'Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice',
		'Supplier Quotation', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice'
	]

	for dt in dts:
		frappe.reload_doctype(dt + " Item")

		frappe.db.sql("""
			update `tab{0}` t
			inner join `tabItem` i on i.name = t.item_code
			set t.is_stock_item = i.is_stock_item, t.is_fixed_asset = i.is_fixed_asset
		""".format(dt + " Item"))
