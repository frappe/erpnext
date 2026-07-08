# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.tests.utils import ERPNextTestSuite


class TestEmailCampaign(ERPNextTestSuite):
	"""Email Campaign derives its window from the linked Campaign schedule and
	guards the start date and the recipient's email."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_email_template(self):
		name = "_Test EC Email Template"
		if not frappe.db.exists("Email Template", name):
			frappe.get_doc(
				{"doctype": "Email Template", "name": name, "subject": "Test", "response": "Hello"}
			).insert()
		return name

	def make_campaign(self, schedules):
		campaign = frappe.new_doc("Campaign")
		campaign.campaign_name = f"_Test EC Campaign {frappe.generate_hash(length=6)}"
		for days in schedules:
			campaign.append(
				"campaign_schedules",
				{"send_after_days": days, "email_template": self.make_email_template()},
			)
		return campaign.insert()

	def make_email_campaign(self, campaign_name, start_date=None):
		doc = frappe.new_doc("Email Campaign")
		doc.campaign_name = campaign_name
		doc.start_date = start_date or today()
		return doc

	def test_start_date_cannot_be_in_the_past(self):
		doc = self.make_email_campaign("irrelevant", start_date=add_days(today(), -1))
		self.assertRaises(frappe.ValidationError, doc.set_date)

	def test_end_date_is_start_plus_max_send_after_days(self):
		campaign = self.make_campaign(schedules=[0, 5])
		doc = self.make_email_campaign(campaign.name)
		doc.set_date()
		self.assertEqual(getdate(doc.end_date), add_days(getdate(today()), 5))

	def test_campaign_without_a_schedule_is_rejected(self):
		campaign = self.make_campaign(schedules=[])
		doc = self.make_email_campaign(campaign.name)
		self.assertRaises(frappe.ValidationError, doc.set_date)

	def test_lead_without_an_email_is_rejected(self):
		lead = frappe.get_doc({"doctype": "Lead", "lead_name": "_Test Lead No Email"}).insert()
		doc = frappe.new_doc("Email Campaign")
		doc.email_campaign_for = "Lead"
		doc.recipient = lead.name
		self.assertRaises(frappe.ValidationError, doc.validate_lead)
