# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import random_string

from erpnext.crm.doctype.lead.lead import add_lead_to_prospect
from erpnext.crm.doctype.lead.test_lead import make_lead


class TestProspect(unittest.TestCase):
	def test_add_lead_to_prospect_and_address_linking(self):
		lead_doc = make_lead()
		address_doc = make_address(address_title=lead_doc.name)
		address_doc.append("links", {"link_doctype": lead_doc.doctype, "link_name": lead_doc.name})
		address_doc.save()
		prospect_doc = make_prospect()
		add_lead_to_prospect(lead_doc.name, prospect_doc.name)
		prospect_doc.reload()
		lead_exists_in_prosoect = False
		for rec in prospect_doc.get("prospect_lead"):
			if rec.lead == lead_doc.name:
				lead_exists_in_prosoect = True
		self.assertEqual(lead_exists_in_prosoect, True)
		address_doc.reload()
		self.assertEqual(address_doc.has_link("Prospect", prospect_doc.name), True)


def make_prospect(**args):
	args = frappe._dict(args)

	prospect_doc = frappe.get_doc(
		{
			"doctype": "Prospect",
			"company_name": args.company_name or "_Test Company {}".format(random_string(3)),
		}
	).insert()

	return prospect_doc


def make_address(**args):
	args = frappe._dict(args)

	address_doc = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": args.address_title or "Address Title",
			"address_type": args.address_type or "Billing",
			"city": args.city or "Mumbai",
			"address_line1": args.address_line1 or "Vidya Vihar West",
			"country": args.country or "India",
		}
	).insert()

	return address_doc
