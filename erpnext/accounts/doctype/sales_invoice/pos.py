# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_items(price_list, sales_or_purchase, item=None, item_group=None):
	condition = ""
	args = {"price_list": price_list}

	if sales_or_purchase == "Sales":
		condition = "i.is_sales_item='Yes'"
	else:
		condition = "i.is_purchase_item='Yes'"

	if item_group and item_group != "All Item Groups":
		condition += " and i.item_group='%s'" % item_group.replace("'", "\'")

	if item:
		condition += " and CONCAT(i.name, i.item_name) like %(name)s"
		args["name"] = "%%%s%%" % item

	return frappe.db.sql("""select i.name, i.item_name, i.image,
		item_det.price_list_rate, item_det.currency
		from `tabItem` i LEFT JOIN
			(select item_code, price_list_rate, currency from
				`tabItem Price`	where price_list=%s) item_det
		ON
			item_det.item_code=i.name
		where
			%s""" % ('%(price_list)s', condition), args, as_dict=1)

@frappe.whitelist()
def get_item_code(barcode_serial_no):
	input_via = "serial_no"
	item_code = frappe.db.sql("""select name, item_code from `tabSerial No` where
		name=%s""", (barcode_serial_no), as_dict=1)

	if not item_code:
		input_via = "barcode"
		item_code = frappe.db.sql("""select name from `tabItem` where barcode=%s""",
			(barcode_serial_no), as_dict=1)

	if item_code:
		return item_code, input_via
	else:
		frappe.throw(frappe._("Invalid Barcode or Serial No"))

@frappe.whitelist()
def get_mode_of_payment():
	return frappe.get_list("Mode of Payment")
