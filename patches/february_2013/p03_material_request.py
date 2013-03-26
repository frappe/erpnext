import webnotes, os, sys

def execute():
	webnotes.reload_doc("core", "doctype", "doctype")
	
	tables = webnotes.conn.sql_list("show tables")
	if not "tabMaterial Request Item" in tables:
		webnotes.rename_doc("DocType", "Purchase Request Item", "Material Request Item", force=True)
	if not "tabMaterial Request" in tables:
		webnotes.rename_doc("DocType", "Purchase Request", "Material Request", force=True)
	webnotes.reload_doc("buying", "search_criteria", "pending_po_items_to_bill")
	webnotes.reload_doc("buying", "search_criteria", "pending_po_items_to_receive")

	webnotes.reload_doc("stock", "doctype", "material_request")
	webnotes.reload_doc("stock", "doctype", "material_request_item")
	
	webnotes.conn.sql("""update `tabMaterial Request` set material_request_type='Purchase'""")
	
	os.system("rm -rf app/buying/doctype/purchase_request")
	os.system("rm -rf app/buying/doctype/purchase_request_item")
	
	os.system("rm -rf app/hr/doctype/holiday_block_list")
	os.system("rm -rf app/hr/doctype/holiday_block_list_allow")
	os.system("rm -rf app/hr/doctype/holiday_block_list_date")
	
