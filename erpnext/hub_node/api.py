# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

import frappe, json
from frappe.utils import now, nowdate

@frappe.whitelist(allow_guest=True)
def make_rfq(supplier, item):

	# supplier_name = "Supp1"
	# supplier_type = "Distributor"
	# supplier_email = "supp1@example.com"
	# company = "ABC"

	# item_code = "Item1"
	# item_group = "Products"

	supplier = frappe.new_doc("Supplier")
	supplier.supplier_name = supplier_name
	supplier.supplier_type = supplier_type

	supplier.insert(ignore_permissions = True)
	frappe.db.commit()

	item = frappe.new_doc("Item")
	item.item_code = item_code
	item.item_group = item_group

	item.insert(ignore_permissions = True)
	frappe.db.commit()


	# supplier, supplier_name, email_id, company
	supplier_data = {
		"supplier": supplier_name,
		"supplier_name": supplier_name,
		"email_id": supplier_email
	}
	rfq = frappe.new_doc('Request for Quotation')
	rfq.transaction_date = nowdate()
	rfq.status = 'Draft'
	rfq.company = company
	rfq.message_for_supplier = 'Please supply the specified items at the best possible rates.'

	rfq.append('suppliers', supplier_data)

	rfq.append("items", {
		"item_code": item_code,
		"description": "ajhs asghaoshf wanfq wdjow",
		"uom": "Nos",
		"qty": 5,
		"warehouse": "Stores - A",
		"schedule_date": nowdate()
	})
	rfq.insert(ignore_permissions=True)
	frappe.db.commit()

	return rfq


	# WORKING

	# supplier_name = "Eg5"
	# email_id = "eg5@example.com"

	# lead = frappe.new_doc("Lead")

	# lead.lead_name = supplier_name
	# lead.email_id = email_id

	# lead.insert(ignore_permissions=True)
	# frappe.db.commit()


	# opportunity = frappe.new_doc("Opportunity")
	# opportunity.enquiry_from = "Lead"
	# opportunity.lead = frappe.get_all("Lead", filters={"email_id": email_id}, fields = ["name"])[0]["name"]

	# opportunity.insert(ignore_permissions=True)
	# frappe.db.commit()

	# return opportunity

@frappe.whitelist(allow_guest=True)
def make_opportunity(buyer_name, email_id):
	# buyer_name = "Eg5"
	# email_id = "eg5@example.com"

	buyer_name = "HUB-" + buyer_name

	lead = frappe.new_doc("Lead")

	lead.lead_name = buyer_name
	lead.email_id = email_id

	lead.insert(ignore_permissions=True)
	frappe.db.commit()


	opportunity = frappe.new_doc("Opportunity")
	opportunity.enquiry_from = "Lead"
	opportunity.lead = frappe.get_all("Lead", filters={"email_id": email_id}, fields = ["name"])[0]["name"]
	opportunity.insert(ignore_permissions=True)
	frappe.db.commit()

	return opportunity