
import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "sales_invoice_item")
	frappe.reload_doc('accounts', 'doctype', 'purchase_invoice_item')
	frappe.reload_doc('buying', 'doctype', 'purchase_order_item')
	frappe.reload_doc('buying', 'doctype', 'supplier_quotation_item')
	frappe.reload_doc('selling', 'doctype', 'sales_order_item')
	frappe.reload_doc('selling', 'doctype', 'quotation_item')
	frappe.reload_doc('stock', 'doctype', 'delivery_note_item')
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt_item')

	selling_doctypes = ["Sales Order Item", "Sales Invoice Item", "Delivery Note Item", "Quotation Item"]
	buying_doctypes = ["Purchase Order Item", "Purchase Invoice Item", "Purchase Receipt Item", "Supplier Quotation Item"]

	for doctype in selling_doctypes:
		values = frappe.db.sql('''
			SELECT
				discount_percentage, rate_with_margin, price_list_rate, name		
			FROM
				`tab%s`
			WHERE
				ifnull(discount_percentage, 0) > 0
		''' % (doctype), as_dict=True)
		calculate_discount(doctype, values)

	for doctype in buying_doctypes:
		values = frappe.db.sql('''
			SELECT
				discount_percentage, price_list_rate, name		
			FROM
				`tab%s`
			WHERE
				discount_percentage > 0
		''' % (doctype), as_dict=True)
		calculate_discount(doctype, values)

def calculate_discount(doctype, values):
	rate = None
	if not values: return
	for d in values:
		if d.rate_with_margin and d.rate_with_margin > 0:
			rate = d.rate_with_margin
		else:
			rate = d.price_list_rate

		discount_value = rate * d.get('discount_percentage') / 100
		frappe.db.sql('''
			UPDATE
				`tab%s`
			SET
				discount_amount = %s
			WHERE
				name = '%s'
		''' % (doctype, discount_value, d.get('name')))
