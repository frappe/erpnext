def execute():
	import webnotes
	from webnotes.model import delete_doc
	from webnotes.modules.module_manager import reload_doc

	dt = {
		'selling':	['quotation', 'sales_order', 'quotation_detail', 'sales_order_detail'], 
		'stock':	['delivery_note', 'delivery_note_detail', 'purchase_receipt', 'purchase_receipt_detail'],
		'accounts': ['receivable_voucher', 'payable_voucher', 'rv_detail', 'pv_detail', 'rv_tax_detail', 'purchase_tax_detail'],
		'buying':	['purchase_order', 'po_detail']
	}
	for m in dt:
		for d in dt[m]:
			reload_doc(m, 'doctype', d)


	webnotes.conn.sql("""delete from `tabDocField` 
		where label in ('Note1', 'OT Notes', 'Note', 'Note HTML', 'Rates HTML') 
		and parent in ('Quotation', 'Sales Order', 'Delivery Note', 'Receivable Voucher', 'Purchase Order')""")


	del_flds = {
		'Sales Order Detail':	"'delivery_date', 'confirmation_date'", 
		'Delivery Note':		"'supplier', 'supplier_address', 'purchase_receipt_no', 'purchase_order_no', 'transaction_date'",
		'Receivable Voucher':	"'voucher_date'",
		'Payable Voucher':		"'voucher_date'",
		'Purchase Receipt':		"'transaction_date'"
	} 

	del_labels = {
		'Delivery Note':		"'Supplier Details'",
		'Purchase Receipt':		"'Get Currrent Stock'"
	}

	for d in del_flds:
		webnotes.conn.sql("delete from `tabDocField` where fieldname in (%s) and parent = %s", (del_flds[d], d))

	for d in del_labels:
		webnotes.conn.sql("delete from `tabDocField` where label in (%s) and parent = %s", (del_labels[d], d))

	delete_doc('DocType', 'Update Delivery Date Detail')

