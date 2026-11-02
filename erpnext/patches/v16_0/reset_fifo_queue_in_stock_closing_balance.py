import frappe


def execute():
	table = frappe.qb.DocType("Stock Closing Balance")
	frappe.qb.update(table).set(table.fifo_queue, None).where(table.fifo_queue.isnotnull()).run()
