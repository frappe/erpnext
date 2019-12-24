import frappe
def execute():
	for doctype in ['Sales Order Item', 'Purchase Order Item']:
		frappe.reload_doctype(doctype)
		frappe.db.sql("""
			UPDATE `tab{0}`
			SET against_blanket_order = 1
			WHERE ifnull(blanket_order, '') != ''
		""".format(doctype))
