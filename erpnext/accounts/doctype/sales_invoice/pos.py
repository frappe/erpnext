# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_items(price_list, sales_or_purchase, item=None):
	condition = ""
	args = {"price_list": price_list}

	if sales_or_purchase == "Sales":
		condition = "i.is_sales_item='Yes'"
	else:
		condition = "i.is_purchase_item='Yes'"

	if item:
		# search serial no
		item_code = frappe.db.sql("""select name as serial_no, item_code
			from `tabSerial No` where name=%s""", (item), as_dict=1)
		if item_code:
			item_code[0]["name"] = item_code[0]["item_code"]
			return item_code

		# search barcode
		item_code = frappe.db.sql("""select name, item_code from `tabItem` where barcode=%s""",
			(item), as_dict=1)
		if item_code:
			item_code[0]["barcode"] = item
			return item_code

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
def get_mode_of_payment():
	return sorted([d.name for d in frappe.get_list("Mode of Payment")])
