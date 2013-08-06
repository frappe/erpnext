# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("accounts", "doctype", "purchase_invoice_item")
	webnotes.conn.auto_commit_on_many_writes = True
	for purchase_invoice in webnotes.conn.sql_list("""select distinct parent 
		from `tabPurchase Invoice Item` where docstatus = 1 and ifnull(valuation_rate, 0)=0"""):
		pi = webnotes.get_obj("Purchase Invoice", purchase_invoice)
		try:
			pi.calculate_taxes_and_totals()
		except:
			pass
		pi.update_raw_material_cost()
		pi.update_valuation_rate("entries")
		for item in pi.doclist.get({"parentfield": "entries"}):
			webnotes.conn.sql("""update `tabPurchase Invoice Item` set valuation_rate = %s 
				where name = %s""", (item.valuation_rate, item.name))

	webnotes.conn.auto_commit_on_many_writes = False