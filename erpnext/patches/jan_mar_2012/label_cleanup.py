from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model import delete_doc
	from webnotes.modules import reload_doc


	webnotes.conn.sql("""delete from `tabDocField` 
		where label in ('Note1', 'OT Notes', 'Note', 'Note HTML', 'Rates HTML') 
		and parent in ('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order')""")


	del_flds = {
		'Sales Order Item':	"'delivery_date', 'confirmation_date'", 
		'Delivery Note':		"'supplier', 'supplier_address', 'purchase_receipt_no', 'purchase_order_no', 'transaction_date'",
		'Sales Invoice':	"'voucher_date'",
		'Purchase Invoice':		"'voucher_date'",
		'Purchase Receipt':		"'transaction_date'"
	} 

	del_labels = {
		'Delivery Note':		"'Supplier Details'",
		'Purchase Receipt':		"'Get Currrent Stock'"
	}

	for d in del_flds:
		webnotes.conn.sql("delete from `tabDocField` where fieldname in (%s) and parent = '%s'"% (del_flds[d], d))

	for d in del_labels:
		webnotes.conn.sql("delete from `tabDocField` where label in (%s) and parent = '%s'"% (del_labels[d], d))

	delete_doc('DocType', 'Update Delivery Date Detail')

	# Reload print formats
	reload_doc('accounts', 'Print Format', 'Sales Invoice Classic')
	reload_doc('accounts', 'Print Format', 'Sales Invoice Modern')
	reload_doc('accounts', 'Print Format', 'Sales Invoice Spartan')

