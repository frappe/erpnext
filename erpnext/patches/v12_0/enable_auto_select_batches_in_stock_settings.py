import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "stock_settings")

	stock_settings = frappe.get_doc("Stock Settings")
	stock_settings.automatically_set_batch_nos_based_on_fifo = True
	stock_settings.save()
