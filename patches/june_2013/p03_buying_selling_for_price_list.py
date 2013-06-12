import webnotes
from webnotes.utils import cint

def execute():
	for price_list in webnotes.conn.sql_list("""select name from `tabPrice List`"""):
		buying, selling = False, False
		for b, s in webnotes.conn.sql("""select distinct buying, selling 
			from `tabItem Price` where price_list_name=%s""", price_list):
				buying = buying or cint(b)
				selling = selling or cint(s)
		
		webnotes.conn.set_value("Price List", price_list, "buying_or_selling", ("Selling" if selling else "Buying"))
		webnotes.conn.sql("""update `tabItem Price` set buying_or_selling=%s where price_list_name=%s""", 
			(("Selling" if selling else "Buying"), price_list))
