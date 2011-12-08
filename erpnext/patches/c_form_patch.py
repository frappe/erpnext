def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc

	reload_doc('accounts', 'doctype', 'receivable_voucher')
	reload_doc('accounts', 'doctype', 'c_form')
	reload_doc('accounts', 'doctype', 'c_form_invoice_details')

	sql = webnotes.conn.sql
	sql("update `tabReceivable Voucher` set c_form_applicable = 'Yes' where c_form_applicable = 'Y'")
	sql("update `tabReceivable Voucher` set c_form_applicable = 'No' where c_form_applicable = 'N'")
