from __future__ import unicode_literals

import frappe

def execute():
	fields = ("is_stock_item", "is_asset_item", "has_batch_no", "has_serial_no",
		"is_sales_item", "is_purchase_item", "inspection_required", "is_sub_contracted_item")

	# convert to 1 or 0
	update_str = ", ".join(["`{0}`=if(`{0}`='Yes',1,0)".format(f) for f in fields])
	frappe.db.sql("update tabItem set {0}".format(update_str))

	frappe.db.commit()

	# alter fields to int
	for f in fields:
		frappe.db.sql("alter table tabItem change {0} {0} int(1) default '0'".format(f, f))

	frappe.reload_doctype("Item")
