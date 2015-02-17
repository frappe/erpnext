# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	dt_list= {"Purchase Order Item","Supplier Quotation Item", "BOM", "Bom Explosion Item" , \
	"Bom Item", "Opportunity Item" , "Quotation Item" , "Sales Order Item" , "Delivery Note Item" , \
	"Material Request Item" , "Purchase Receipt Item" , "Stock Entry Detail"}
	
	for dt in dt_list:
		names = frappe.db.sql("""select name, description from `tab{0}` doc where doc.description is not null""".format(dt),as_dict=1)
		for d in names:
			try:
				data = d.description
				image_url = data.split('<img src=')[1].split('" width=')[0]
				desc = data.split('<td>')[1].split('</td>')[0]
				frappe.db.sql("""update `tab{0}` doc set doc.description = %s, doc.image = %s 
					where doc.name = %s """.format(dt),(desc, image_url, d.name))
			except:
				pass
	