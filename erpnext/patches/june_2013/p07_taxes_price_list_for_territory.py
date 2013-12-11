# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("setup", "doctype", "applicable_territory")
	webnotes.reload_doc("stock", "doctype", "price_list")
	webnotes.reload_doc("accounts", "doctype", "sales_taxes_and_charges_master")
	webnotes.reload_doc("accounts", "doctype", "shipping_rule")
	
	from setup.utils import get_root_of
	root_territory = get_root_of("Territory")
	
	for parenttype in ["Sales Taxes and Charges Master", "Price List", "Shipping Rule"]:
		for name in webnotes.conn.sql_list("""select name from `tab%s` main
			where not exists (select parent from `tabApplicable Territory` territory
				where territory.parenttype=%s and territory.parent=main.name)""" % \
				(parenttype, "%s"), (parenttype,)):
			
			doc = webnotes.doc({
				"doctype": "Applicable Territory",
				"__islocal": 1,
				"parenttype": parenttype,
				"parentfield": "valid_for_territories",
				"parent": name,
				"territory": root_territory
			})
			doc.save()
