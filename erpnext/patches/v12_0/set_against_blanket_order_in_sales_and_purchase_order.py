import frappe
def execute():

	frappe.reload_doc('selling', 'doctype', frappe.scrub('Sales Order Item'))
	frappe.reload_doc('buying', 'doctype', frappe.scrub('Purchase Order Item'))

	for doctype in ['Sales Order Item', 'Purchase Order Item']:
		frappe.db.sql("""
			UPDATE `tab{0}`
			SET against_blanket_order = 1
			WHERE ifnull(blanket_order, '') != ''
		""".format(doctype))
