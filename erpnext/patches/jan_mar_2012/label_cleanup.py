def execute():
	import webnotes
	from webnotes.model import delete_doc
	from webnotes.modules.module_manager import reload_doc

	reload_doc('selling', 'doctype', 'sales_order')

	webnotes.conn.sql("""delete from `tabDocField` 
		where label in ('Note1', 'OT Notes', 'Note', 'Note HTML', 'Rates HTML') 
		and parent in ('Quotation', 'Sales Order', 'Delivery Note', 'Receivable Voucher')""")

	del_flds = {
		'Sales Order Detail':	"'delivery_date', 'confirmation_date'", 
		'Delivery Note':		"'supplier', 'supplier_address', 'purchase_receipt_no', 'purchase_order_no'"
		'Receivable Voucher':	"'voucher_date'"
	} 

	del_labels = {
		'Delivery Note':		"'Supplier Details'"
	}

	for d in del_flds:
		webnotes.conn.sql("delete from `tabDocField` where fieldname in (%s) and parent = %s", (del_flds[d], d))

	for d in del_labels:
		webnotes.conn.sql("delete from `tabDocField` where label in (%s) and parent = %s", (del_labels[d], d))

	delete_doc('DocType', 'Update Delivery Date Detail')
	delete_doc('DocType', 'Update Delivery Date'
