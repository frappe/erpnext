import webnotes

def execute():
	webnotes.reload_doc("buying", "DocType Mapper", "Material Request-Purchase Order")
	webnotes.reload_doc("buying", "DocType Mapper", "Material Request-Supplier Quotation")
	webnotes.reload_doc("buying", "DocType Mapper", "Sales Order-Material Request")
	webnotes.reload_doc("stock", "DocType Mapper", "Material Request-Stock Entry")