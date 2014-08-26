import frappe

def execute():
	frappe.reload_doc('selling', 'doctype', 'sales_order')
	frappe.db.sql("""update `tabSales Invoice` set period_from = order_period_from,
		period_to = order_period_to, convert_into_recurring = convert_into_recurring_order""")
