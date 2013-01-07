import webnotes

def execute():
	rename_fields()
	
def rename_fields():
	webnotes.reload_doc("stock", "doctype", "stock_ledger_entry")
	
	args = [["Stock Ledger Entry", "bin_aqat", "qty_after_transaction"], 
		["Stock Ledger Entry", "fcfs_stack", "stock_queue"]]
	for doctype, old_fieldname, new_fieldname in args:
		webnotes.conn.sql("""update `tab%s` set `%s`=`%s`""" % 
			(doctype, new_fieldname, old_fieldname))
		