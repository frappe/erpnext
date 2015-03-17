# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.website.utils import find_first_image
from frappe.utils import cstr
import re

def execute():
	dt_list= ["Purchase Order Item","Supplier Quotation Item", "BOM", "BOM Explosion Item" , \
	"BOM Item", "Opportunity Item" , "Quotation Item" , "Sales Order Item" , "Delivery Note Item" , \
	"Material Request Item" , "Purchase Receipt Item" , "Stock Entry Detail"]
	for dt in dt_list:
		frappe.reload_doctype(dt)
		names = frappe.db.sql("""select name, description from `tab{0}` where description is not null""".format(dt),as_dict=1)
		for d in names:
			data = cstr(d.description)
			image_url = find_first_image(data)
			desc =  re.sub("\<img[^>]+\>", "", data)

			frappe.db.sql("""update `tab{0}` set description = %s, image = %s
				where name = %s """.format(dt), (desc, image_url, d.name))
