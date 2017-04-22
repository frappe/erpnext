# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

import frappe, json
from frappe.utils import now, nowdate

@frappe.whitelist(allow_guest=True)
def make_rfq(supplier, supplier_name, email_id, company):
	supplier_data = {
		"supplier": supplier,
		"supplier_name": supplier_name,
		"email_id": email_id
	}
	rfq = frappe.new_doc('Request for Quotation')
	rfq.transaction_date = nowdate()
	rfq.status = 'Draft'
	rfq.company = company
	rfq.message_for_supplier = 'Please supply the specified items at the best possible rates.'

	rfq.append('suppliers', supplier_data)

	rfq.append("items", {
		"item_code": "_Test Item",
		"description": "_Test Item",
		"uom": "_Test UOM",
		"qty": 5,
		"warehouse": "_Test Warehouse - _TC",
		"schedule_date": nowdate()
	})
	print "--------------------3---------------------"
	rfq.insert(ignore_permissions=True)
	print "-----------------4------------------------"

	return rfq