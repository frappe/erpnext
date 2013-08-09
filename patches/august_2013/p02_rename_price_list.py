import webnotes

def execute():
	for t in [
			("Supplier Quotation", "price_list_name", "buying_price_list"),
			("Purchase Order", "price_list_name", "buying_price_list"),
			("Purchase Invoice", "price_list_name", "buying_price_list"),
			("Purchase Receipt", "price_list_name", "buying_price_list"),
			("Quotation", "price_list_name", "selling_price_list"),
			("Sales Order", "price_list_name", "selling_price_list"),
			("Delivery Note", "price_list_name", "selling_price_list"),
			("Sales Invoice", "price_list_name", "selling_price_list"),
			("POS Setting", "price_list_name", "selling_price_list"),
			("Shopping Cart Price List", "price_list", "selling_price_list"),
			("Item Price", "price_list_name", "price_list"),
			("BOM", "price_list", "buying_price_list"),
		]:
		webnotes.conn.sql_ddl("alter table `tab%s` change `%s` `%s` varchar(180)" % t)
		
	webnotes.conn.sql("""update tabSingles set field='selling_price_list'
		where field='price_list_name' and doctype='Selling Settings'""")

	webnotes.bean("Selling Settings").save()