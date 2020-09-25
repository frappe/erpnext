# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.utils import today, random_string
from erpnext.crm.doctype.lead.lead import make_customer
from erpnext.crm.doctype.opportunity.opportunity import make_quotation
import unittest

test_records = frappe.get_test_records('Opportunity')

class TestOpportunity(unittest.TestCase):
	def test_opportunity_status(self):
		doc = make_opportunity(with_items=0)
		quotation = make_quotation(doc.name)
		quotation.append('items', {
			"item_code": "_Test Item",
			"qty": 1
		})

		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")
		quotation.submit()

		doc = frappe.get_doc('Opportunity', doc.name)
		self.assertEqual(doc.status, "Quotation")

	def test_make_new_lead_if_required(self):
		new_lead_email_id = "new{}@example.com".format(random_string(5))
		args = {
			"doctype": "Opportunity",
			"contact_email": new_lead_email_id,
			"opportunity_type": "Sales",
			"with_items": 0,
			"transaction_date": today()
		}
		# new lead should be created against the new.opportunity@example.com
		opp_doc = frappe.get_doc(args).insert(ignore_permissions=True)

		self.assertTrue(opp_doc.party_name)
		self.assertEqual(opp_doc.opportunity_from, "Lead")
		self.assertEqual(frappe.db.get_value("Lead", opp_doc.party_name, "email_id"),
			new_lead_email_id)

		# create new customer and create new contact against 'new.opportunity@example.com'
		customer = make_customer(opp_doc.party_name).insert(ignore_permissions=True)
		contact = frappe.get_doc({
			"doctype": "Contact",
			"first_name": "_Test Opportunity Customer",
			"links": [{
				"link_doctype": "Customer",
				"link_name": customer.name
			}]
		})
		contact.add_email(new_lead_email_id, is_primary=True)
		contact.insert(ignore_permissions=True)

		opp_doc = frappe.get_doc(args).insert(ignore_permissions=True)
		self.assertTrue(opp_doc.party_name)
		self.assertEqual(opp_doc.opportunity_from, "Customer")
		self.assertEqual(opp_doc.party_name, customer.name)

def make_opportunity(**args):
	args = frappe._dict(args)

	opp_doc = frappe.get_doc({
		"doctype": "Opportunity",
		"company": args.company or "_Test Company",
		"opportunity_from": args.opportunity_from or "Customer",
		"opportunity_type": "Sales",
		"with_items": args.with_items or 0,
		"transaction_date": today()
	})

	if opp_doc.opportunity_from == 'Customer':
		opp_doc.party_name= args.customer or "_Test Customer"

	if opp_doc.opportunity_from == 'Lead':
		opp_doc.party_name = args.lead or "_T-Lead-00001"

	if args.with_items:
		opp_doc.append('items', {
			"item_code": args.item_code or "_Test Item",
			"qty": args.qty or 1,
			"uom": "_Test UOM"
		})

	opp_doc.insert()
	return opp_doc