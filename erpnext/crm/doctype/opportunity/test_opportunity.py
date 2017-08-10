# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.utils import today
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
		self.assertEquals(doc.status, "Quotation")

def make_opportunity(**args):
	args = frappe._dict(args)

	opp_doc = frappe.get_doc({
		"doctype": "Opportunity",
		"enquiry_from": "Customer" or args.enquiry_from,
		"enquiry_type": "Sales",
		"with_items": args.with_items or 0,
		"transaction_date": today()
	})

	if opp_doc.enquiry_from == 'Customer':
		opp_doc.customer = args.customer or "_Test Customer"

	if opp_doc.enquiry_from == 'Lead':
		opp_doc.customer = args.lead or "_T-Lead-00001"

	if args.with_items:
		opp_doc.append('items', {
			"item_code": args.item_code or "_Test Item",
			"qty": args.qty or 1
		})

	opp_doc.insert()
	return opp_doc