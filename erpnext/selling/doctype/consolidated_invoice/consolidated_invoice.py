# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ConsolidatedInvoice(Document):
	pass

@frappe.whitelist()
def get_invoices(from_date, to_date, item_code, customer, cost_center):
	data = frappe.db.sql('''select si.name, si.reference_date_for_payment as posting_date, 
							sii.rate as rate, sii.accepted_qty as qty, 
							sii.amount as outstanding_amount,sii.delivery_note, sii.sales_order, 
							sii.accepted_qty 
						from `tabSales Invoice` si, `tabSales Invoice Item` sii 
						where si.docstatus = 1 and si.outstanding_amount >= 0 
						and si.customer = %s and sii.cost_center = %s 
						and si.reference_date_for_payment between %s 
						and %s and sii.item_code = %s and sii.parent = si.name 
						and not exists (select 1 
										from `tabConsolidated Invoice` c 
										inner join `tabConsolidated Invoice Item` ci 
										on c.name = ci.parent 
										where ci.invoice_no = si.name 
										and c.docstatus != 2) 
						order by reference_date_for_payment''', (customer, cost_center, from_date, to_date, item_code), as_dict=True)
	if not data:
		frappe.throw("No Invoices for set Parameters")
	return data
