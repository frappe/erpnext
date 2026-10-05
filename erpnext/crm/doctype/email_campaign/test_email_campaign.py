# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.crm.doctype.email_campaign.email_campaign import send_email_to_leads_or_contacts
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

	def make_lead(self):
		email = f"_test_ec_{frappe.generate_hash(length=6)}@example.com"
		return frappe.get_doc({"doctype": "Lead", "lead_name": "_Test EC Lead", "email_id": email}).insert()

	def make_lead_email_campaign(self, lead, schedules, start_date=None):
		doc = self.make_email_campaign(self.make_campaign(schedules).name, start_date)
		doc.email_campaign_for = "Lead"
		doc.recipient = lead.name
		return doc.insert()

	def send_campaign_mails(self, recipient_email):
		with patch("frappe.sendmail") as sendmail:
			send_email_to_leads_or_contacts()
		return [c.kwargs for c in sendmail.call_args_list if recipient_email in c.kwargs["recipients"]]

	def test_campaign_mail_carries_an_unsubscribe_link(self):
		lead = self.make_lead()
		email_campaign = self.make_lead_email_campaign(lead, schedules=[0])

		(mail,) = self.send_campaign_mails(lead.email_id)
		self.assertEqual(mail["reference_doctype"], "Email Campaign")
		self.assertEqual(mail["reference_name"], email_campaign.name)
		self.assertTrue(mail["unsubscribe_message"])

	def test_unsubscribed_lead_gets_no_campaign_mail(self):
		lead = self.make_lead()
		self.make_lead_email_campaign(lead, schedules=[0])
		lead.db_set("unsubscribed", 1)

		self.assertEqual(self.send_campaign_mails(lead.email_id), [])
		self.assertRaisesRegex(
			frappe.ValidationError, "unsubscribed", self.make_lead_email_campaign, lead, schedules=[0]
		)

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

	def test_contact_without_an_email_is_rejected(self):
		contact = frappe.get_doc({"doctype": "Contact", "first_name": "_Test Contact No Email"}).insert()
		campaign = self.make_campaign(schedules=[0])
		doc = self.make_email_campaign(campaign.name)
		doc.email_campaign_for = "Contact"
		doc.recipient = contact.name
		self.assertRaisesRegex(frappe.ValidationError, "primary email ID", doc.insert)

	def test_contact_with_an_email_is_accepted(self):
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "_Test Contact With Email",
				"email_ids": [{"email_id": "_test_email_campaign@example.com", "is_primary": 1}],
			}
		).insert()
		campaign = self.make_campaign(schedules=[0])
		doc = self.make_email_campaign(campaign.name)
		doc.email_campaign_for = "Contact"
		doc.recipient = contact.name
		doc.insert()
		self.assertEqual(doc.status, "In Progress")
