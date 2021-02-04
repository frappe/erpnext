from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("selling", "doctype", "quotation_item", force=1)
	frappe.reload_doc("selling", "doctype", "sales_order_item", force=1)
	frappe.reload_doc("stock", "doctype", "delivery_note_item", force=1)
	frappe.reload_doc("accounts", "doctype", "sales_invoice_item", force=1)
	frappe.reload_doc("buying", "doctype", "purchase_order_item", force=1)
	frappe.reload_doc("stock", "doctype", "purchase_receipt_item", force=1)
	frappe.reload_doc("accounts", "doctype", "purchase_invoice_item", force=1)

	frappe.db.sql("""UPDATE `tabQuotation Item`
		SET stock_uom_rate = (rate/conversion_factor) 
	""")

	frappe.db.sql("""UPDATE `tabSales Order Item`
		SET stock_uom_rate = (rate/conversion_factor) 
	""")

	frappe.db.sql("""UPDATE `tabDelivery Note Item`
		SET stock_uom_rate = (rate/conversion_factor) 
	""")

	frappe.db.sql("""UPDATE `tabSales Invoice Item`
		SET stock_uom_rate = (rate/conversion_factor) 
	""")

	frappe.db.sql("""UPDATE `tabPurchase Order Item`
		SET stock_uom_rate = (rate/conversion_factor) 
	""")

	frappe.db.sql("""UPDATE `tabPurchase Receipt Item`
		SET stock_uom_rate = (rate/conversion_factor) 
	""")

	frappe.db.sql("""UPDATE `tabPurchase Invoice Item`
		SET stock_uom_rate = (rate/conversion_factor) 
	""")