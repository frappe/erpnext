import webnotes

def execute():
	webnotes.reload_doc("accounts", "doctype", "purchase_invoice_item")
	
	for purchase_invoice in webnotes.conn.sql_list("""select distinct parent 
		from `tabPurchase Invoice Item` pi_item where docstatus = 1 and ifnull(valuation_rate, 0)=0 
		and exists(select name from `tabPurchase Invoice` where name = pi_item.parent)"""):
			pi = webnotes.get_obj("Purchase Invoice", purchase_invoice)
			pi.calculate_taxes_and_totals()
			pi.update_raw_material_cost()
			pi.update_valuation_rate("entries")
			for item in pi.doclist.get({"parentfield": "entries"}):
				webnotes.conn.set_value("Purchase Invoice Item", item.name, "valuation_rate",
					item.valuation_rate)