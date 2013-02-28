import webnotes

def execute():
	for w in webnotes.conn.sql("""select name from `tabWarehouse` where docstatus=2"""):
		try:
			webnotes.delete_doc("Warehouse", w[0])
		except webnotes.ValidationError:
			pass
		