def execute():
	import webnotes
	webnotes.conn.sql("""delete from `tabDefaultValue` where defkey in ('page_break', 'projects', 'packing_details', 'discounts', 'brands', 'item_batch_nos', 'after_sales_installations', 'item_searial_nos', 'item_group_in_details', 'exports', 'imports', 'item_advanced', 'sales_extras', 'more_info', 'quality', 'manufacturing', 'pos', 'item_serial_nos', 'purchase_discounts', 'recurring_invoice') and parent = 'Control Panel'""")
