import frappe


def execute():
	table = frappe.qb.DocType("Stock Closing Balance")

	(
		frappe.qb.update(table)
		.set(table.stock_value, table.stock_value_difference)
		.set(table.valuation_rate, table.stock_value_difference / table.actual_qty)
		.where((table.stock_value == 0) & (table.actual_qty != 0))
		.run()
	)

	(
		frappe.qb.update(table)
		.set(table.stock_value, table.stock_value_difference)
		.where((table.stock_value == 0) & (table.actual_qty == 0))
		.run()
	)
