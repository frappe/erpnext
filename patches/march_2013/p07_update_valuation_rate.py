import webnotes

def execute():
	for purchase_invoice in webnotes.conn.sql_list("""select distinct parent 
		from `tabPurchase Invoice Item` where docstatus = 1 and ifnull(valuation_rate, 0)=0"""):
		pi = webnotes.get_obj("Purchase Invoice", purchase_invoice)
		pi.calculate_taxes_and_totals()
		pi.update_raw_material_cost()
		pi.update_valuation_rate("entries")
		for item in pi.doclist.get({"parentfield": "entries"}):
			webnotes.conn.sql("""update `tabPurchase Invoice Item` set valuation_rate = %s 
				where name = %s""", (item.valuation_rate, item.name))
	