import webnotes

def execute():
	for purchase_invoice in webnotes.conn.sql("""select distinct parent 
		from `tabPurchase Invoice Item` where docstatus = 1 and ifnull(valuation_rate, 0)=0"""):
		pi = webnotes.get_obj("Purchase Invoice", purchase_invoice)
		pi.calculate_taxes_and_totals()
		pi.update_raw_material_cost()
		pi.update_valuation_rate("entries")
		for item in pi.doclist.get({"parentfield": "entries"}):
			webnotes.conn.set_value("Purchase Invoice Item", item.name, "valuation_rate",
				item.valuation_rate)
	