# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

import frappe, json
from frappe.utils import now, nowdate

@frappe.whitelist(allow_guest=True)
def make(msg_type, data):
	print "//////////////makr/////////////////////"
	if msg_type == "Request for Quotation":
		make_rfq(data)
	if msg_type == "Opportunity":
		make_opportunity(data)

def make_rfq(data):
	print "///////////////rfq////////////////////"
	args = json.loads(data)
	print args

	# supplier_name = "Supp1"
	# supplier_type = "Distributor"
	# supplier_email = "supp1@example.com"
	# company = "ABC"

	# item_code = "Item1"
	# item_group = "Products"

	supplier_name = args["hub_user_name"]
	supplier_type = "Distributor"
	supplier_email = args["email"]
	company = args["company"]

	item_code = args["item_code"]
	item_group = args["item_group"]

	print "///////////////rfq0////////////////////"

	supplier = frappe.new_doc("Supplier")
	supplier.supplier_name = supplier_name
	supplier.supplier_type = supplier_type


	print "///////////////rfq2////////////////////"

	supplier.insert(ignore_permissions = True)
	frappe.db.commit()

	item = frappe.new_doc("Item")
	item.item_code = item_code
	item.item_group = item_group

	print "///////////////rfq3////////////////////"

	# item.insert(ignore_permissions = True)
	# frappe.db.commit()

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
		"qty": 1,
		"warehouse": "Stores - A",
		"schedule_date": nowdate()
	})

	print "///////////////rfq4////////////////////"
	rfq.insert(ignore_permissions=True)
	frappe.db.commit()

	print "///////////////rfq5////////////////////"

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

def make_opportunity(data):
	# buyer_name = "Eg5"
	# email_id = "eg5@example.com"

	args = json.loads(data)
	buyer_name = args.buyer_name
	email_id = args.email_id

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

def test(supplier, item):

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