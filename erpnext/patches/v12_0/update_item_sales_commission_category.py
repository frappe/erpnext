import frappe
from erpnext.stock.get_item_details import get_sales_commission_category
from erpnext.selling.doctype.sales_commission_category.sales_commission_category import get_commission_rate


def execute():
	frappe.reload_doc("selling", "doctype", "sales_commission_category")
	frappe.reload_doc("accounts", "doctype", "sales_invoice_item")

	invoices = frappe.get_all("Sales Invoice")
	for d in invoices:
		doc = frappe.get_doc("Sales Invoice", d.name)
		for d in doc.items:
			if d.item_code:
				d.sales_commission_category = get_sales_commission_category(d.item_code, {'company': doc.company})
				d.commission_rate = get_commission_rate(d.sales_commission_category)

				d.db_set({
					'sales_commission_category': d.sales_commission_category,
					'commission_rate': d.commission_rate,
				}, update_modified=False)

		doc.clear_cache()
