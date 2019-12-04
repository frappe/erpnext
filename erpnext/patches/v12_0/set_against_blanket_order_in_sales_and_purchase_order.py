import frappe
def execute():
	for doctype in ['Sales Order', 'Purchase Order']:
		frappe.reload_doctype(doctype + ' Item')
		frappe.db.sql("""
			UPDATE `tab{0} Item`
			SET against_blanket_order = 1
			WHERE ifnull(blanket_order, '') != ''
		""".format(doctype))