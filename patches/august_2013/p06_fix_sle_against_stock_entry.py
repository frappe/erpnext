import webnotes
def execute():
	from stock.stock_ledger import update_entries_after
	
	stock_entries = webnotes.conn.sql("""select name from `tabStock Entry` 
		where docstatus < 2  and modified >= '2013-08-15' 
		and ifnull(production_order, '') != '' and ifnull(bom_no, '') != ''""")
		
	for entry in stock_entries:
		webnotes.conn.sql("""update `tabStock Ledger Entry` set is_cancelled = 'Yes' 
			where voucher_type = 'Stock Entry' and voucher_no = %s""", entry[0])
			
		item_warehouse = webnotes.conn.sql("""select distinct item_code, warehouse 
			from `tabStock Ledger Entry` 
			where voucher_type = 'Stock Entry' and voucher_no = %s""", entry[0], as_dict=1)
			
		for d in item_warehouse:
			update_entries_after({
				"item_code": d.item_code,
				"warehouse": d.warehouse,
				"posting_date": "2013-08-15",
				"posting_date": "01:00"
			})