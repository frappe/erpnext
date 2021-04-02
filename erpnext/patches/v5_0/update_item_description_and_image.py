# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.website.utils import find_first_image
from frappe.utils import cstr
import re

def execute():
	item_details = frappe._dict()
	for d in frappe.db.sql("select name, description_html, description from `tabItem`", as_dict=1):
		description = cstr(d.description_html).strip() or cstr(d.description).strip()
		image_url, new_desc = extract_image_and_description(description)

		item_details.setdefault(d.name, frappe._dict({
			"old_description": description,
			"new_description": new_desc,
			"image_url": image_url
		}))


	dt_list= ["Purchase Order Item","Supplier Quotation Item", "BOM", "BOM Explosion Item" , \
	"BOM Item", "Opportunity Item" , "Quotation Item" , "Sales Order Item" , "Delivery Note Item" , \
	"Material Request Item" , "Purchase Receipt Item" , "Stock Entry Detail"]
	for dt in dt_list:
		frappe.reload_doctype(dt)
		records = frappe.db.sql("""select name, `{0}` as item_code, description from `tab{1}`
			where description is not null and image is null and description like '%%<img%%'"""
			.format("item" if dt=="BOM" else "item_code", dt), as_dict=1)

		count = 1
		for d in records:
			if d.item_code and item_details.get(d.item_code) \
					and cstr(d.description) == item_details.get(d.item_code).old_description:
				image_url = item_details.get(d.item_code).image_url
				desc = item_details.get(d.item_code).new_description
			else:
				image_url, desc = extract_image_and_description(cstr(d.description))

			if image_url:
				frappe.db.sql("""update `tab{0}` set description = %s, image = %s
					where name = %s """.format(dt), (desc, image_url, d.name))

				count += 1
				if count % 500 == 0:
					frappe.db.commit()


def extract_image_and_description(data):
	image_url = find_first_image(data)
	desc =  re.sub("\<img[^>]+\>", "", data)

	return image_url, desc
