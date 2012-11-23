import webnotes

def execute():
	webnotes.conn.sql("""delete from `tabSearch Criteria` where name='Delivery Note Itemwise Pending To Bill'""")
	from webnotes.modules import reload_doc
	reload_doc("stock", "report", "delivered_items_to_be_billed")