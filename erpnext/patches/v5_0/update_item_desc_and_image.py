# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.website.utils import find_first_image
import re

def execute():
	dt_list= ["Purchase Order Item","Supplier Quotation Item", "BOM", "BOM Explosion Item" , \
	"BOM Item", "Opportunity Item" , "Quotation Item" , "Sales Order Item" , "Delivery Note Item" , \
	"Material Request Item" , "Purchase Receipt Item" , "Stock Entry Detail"]
	for dt in dt_list:
		names = frappe.db.sql("""select name, description from `tab{0}` doc where doc.description is not null""".format(dt),as_dict=1)
		for d in names:
			try:
				data = d.description
				image_url = find_first_image(data)
				desc =  re.sub("\<img[^>]+\>", "", data)
				
				frappe.db.sql("""update `tab{0}` doc set doc.description = %s, doc.image = %s 
					where doc.name = %s """.format(dt),(desc, image_url, d.name))
			except:
				pass
	