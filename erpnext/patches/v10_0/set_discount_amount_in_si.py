import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "sales_invoice")
	frappe.reload_doc("accounts", "doctype", "sales_invoice_item")

	values = frappe.db.sql('''
		SELECT
			si.discount_percentage, s.conversion_rate, s.name as parent, si.rate_with_margin, si.price_list_rate			
		FROM
			`tabSales Invoice Item` si, `tabSales Invoice` s
		WHERE
			si.discount_percentage > 0 AND s.name = si.parent
		GROUP BY
			si.name
	''', as_dict=True)

	rate = None

	for d in values:
		if d.rate_with_margin > 0:
			rate = d.rate_with_margin
		else:
			rate = d.price_list_rate
		frappe.db.sql('''
			UPDATE
				`tabSales Invoice Item` si
			SET
				discount_amount = ((%s) * (discount_percentage) / 100),
				base_discount_amount = ((%s) * (discount_percentage) / 100) * %s
			WHERE
				parent = %s
		''', (rate, rate, d.get('conversion_rate'), d.get('parent')))
