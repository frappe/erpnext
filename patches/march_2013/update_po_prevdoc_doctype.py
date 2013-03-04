import webnotes
def execute():
	webnotes.conn.sql("""update `tabPurchase Order Item` set prevdoc_doctype = 'Material Request' 
		where prevdoc_doctype = 'Purchase Request'""")
	webnotes.conn.sql("""update `tabSupplier Quotation Item` 
		set prevdoc_doctype = 'Material Request' where prevdoc_doctype = 'Purchase Request'""")