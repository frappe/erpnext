# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ConsolidatedInvoice(Document):
	pass

@frappe.whitelist()
def get_invoices(from_date, to_date, item_code, customer, cost_center):
	# si.total and si.charges_total is returned instead of outstanding_amount
	# query = "select si.name, si.posting_date, sii.amount as outstanding_amount,sii.excess_amt as excess_amount,sii.normal_loss_amt as normal_loss_amount, sii.abnormal_loss_amt as abnormal_loss_amount, si.total_charges, sii.delivery_note, sii.sales_order, sii.accepted_qty from `tabSales Invoice` si, `tabSales Invoice Item` sii where si.docstatus = 1 and si.outstanding_amount >= 0 and si.customer = '{}' and sii.cost_center = '{}' and si.posting_date between '{}' and '{}' and sii.item_code = '{}' and sii.parent = si.name and not exists (select 1 from `tabConsolidated Invoice Item` ci where ci.invoice_no = si.name and ci.docstatus = 1) order by posting_date".format(customer, cost_center, from_date, to_date, item_code)
	# data = frappe.db.sql(query,as_dict=1)
	# frappe.msgprint(str(query))
	data = frappe.db.sql("select si.name, si.reference_date_for_payment as posting_date, sii.amount as outstanding_amount,sii.excess_amt as excess_amount,sii.normal_loss_amt as normal_loss_amount, sii.abnormal_loss_amt as abnormal_loss_amount, si.total_charges, sii.delivery_note, sii.sales_order, sii.accepted_qty from `tabSales Invoice` si, `tabSales Invoice Item` sii where si.docstatus = 1 and si.outstanding_amount >= 0 and si.customer = %s and sii.cost_center = %s and si.reference_date_for_payment between %s and %s and sii.item_code = %s and sii.parent = si.name and not exists (select 1 from `tabConsolidated Invoice Item` ci where ci.invoice_no = si.name and ci.docstatus = 1) order by reference_date_for_payment", (customer, cost_center, from_date, to_date, item_code), as_dict=True)
	if not data:
		frappe.throw("No Invoices for set Parameters")
	return data
