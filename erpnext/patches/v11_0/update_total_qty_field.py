import frappe

def execute():
	frappe.reload_doc('buying', 'doctype', 'purchase_order')
	frappe.reload_doc('buying', 'doctype', 'supplier_quotation')
	frappe.reload_doc('selling', 'doctype', 'sales_order')
	frappe.reload_doc('selling', 'doctype', 'quotation')
	frappe.reload_doc('stock', 'doctype', 'delivery_note')
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt')
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice')
	frappe.reload_doc('accounts', 'doctype', 'purchase_invoice')
 
	doctypes = ["Sales Order", "Sales Invoice", "Delivery Note",\
		"Purchase Order", "Purchase Invoice", "Purchase Receipt", "Quotation", "Supplier Quotation"]

	for doctype in doctypes:
		total_qty =	frappe.db.sql('''
			SELECT
				parent, SUM(qty) as qty
			FROM
				`tab%s Item`
			GROUP BY parent
		''' % (doctype), as_dict = True)

		when_then = []
		for d in total_qty:
			when_then.append("""
				when dt.name = '{0}' then {1}
			""".format(frappe.db.escape(d.get("parent")), d.get("qty")))

		if when_then:
			frappe.db.sql('''
				UPDATE
					`tab%s` dt SET dt.total_qty = CASE %s ELSE 0.0 END
			''' % (doctype, " ".join(when_then)))