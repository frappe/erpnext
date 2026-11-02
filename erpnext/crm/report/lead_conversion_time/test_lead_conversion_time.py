# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.desk.query_report import run
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.crm.report.lead_conversion_time.lead_conversion_time import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestLeadConversionTime(ERPNextTestSuite):
	def test_first_contact_ignores_null_communication_date(self):
		"""first_contact ordered by the nullable communication_date and read row[0][0]. With no
		IS NOT NULL guard, MariaDB (NULLs-first) returned a NULL-dated Communication -> first_contact
		None -> a wrong duration, while Postgres (NULLs-last) returned the earliest real date. Filtering
		communication_date IS NOT NULL (and guarding the slice) makes both engines use the earliest
		real contact date."""
		email = "_test_lead_conv@example.com"
		customer_name = "_Test Lead Conv 22d"

		lead = frappe.get_doc({"doctype": "Lead", "lead_name": customer_name, "email_id": email}).insert(
			ignore_permissions=True
		)
		# two opportunities of one lead make one row
		for _opportunity in range(2):
			frappe.get_doc(
				{
					"doctype": "Opportunity",
					"opportunity_from": "Lead",
					"party_name": lead.name,
					"company": "_Test Company",
					"currency": "INR",
					"conversion_rate": 1,
					"contact_email": email,
					"customer_name": customer_name,
				}
			).insert(ignore_permissions=True)

		si = create_sales_invoice(do_not_save=1)
		si.contact_email = email
		si.set_posting_time = 1
		si.posting_date = add_days(nowdate(), -2)
		si.save()

		# count query filters on `sender`; first_contact filters on `recipients` -> set both
		# recipients usually carry a display name and other addresses
		real = frappe.get_doc(
			{
				"doctype": "Communication",
				"subject": "real",
				"sender": email,
				"recipients": f"Lead Conv <{email}>, someone@example.com",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value(
			"Communication", real.name, "communication_date", add_days(nowdate(), -22), update_modified=False
		)
		nulldate = frappe.get_doc(
			{"doctype": "Communication", "subject": "nulldate", "sender": email, "recipients": email}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Communication", nulldate.name, "communication_date", None, update_modified=False)

		filters = frappe._dict({"from_date": add_days(nowdate(), -30), "to_date": nowdate()})
		# rows are lists: [customer, interactions, duration, support_tickets]
		self.assertFalse([r for r in execute(filters)[1] if r[0] == customer_name], "draft invoice counted")

		si.submit()
		rows = [r for r in execute(filters)[1] if r[0] == customer_name]
		self.assertEqual(len(rows), 1)
		row = rows[0]
		# from the earliest REAL contact (22 days ago, not the NULL-dated one) to the posting date
		self.assertEqual(row[2], 20.0)

	def test_first_contact_matches_whole_addresses(self):
		email = "ann_lct@example.com"
		lead = make_lead("_Test Lead Conv Overlap", email)
		make_opportunity(lead, email)
		make_submitted_invoice(email)
		make_communication(email, f"jo{email}", -30)
		make_communication(email, f"Ann <{email}>", -22)

		self.assertEqual(get_report_rows(lead.lead_name)[0][2], 20.0)

	def test_lead_converted_through_a_later_opportunity(self):
		email = "_test_lead_conv_later@example.com"
		lead = make_lead("_Test Lead Conv Later", email)
		make_opportunity(lead, None)
		make_opportunity(lead, email)
		make_submitted_invoice(email)
		make_communication(email, email, -22)

		self.assertEqual(len(get_report_rows(lead.lead_name)), 1)

	def test_sales_user_can_run_the_report(self):
		frappe.reload_doc("crm", "report", "lead_conversion_time", force=True)
		user = create_user("lead_conversion_sales_user@example.com", "Sales User")
		filters = {"from_date": add_days(nowdate(), -30), "to_date": nowdate()}

		with self.set_user(user.name):
			self.assertIn("result", run("Lead Conversion Time", filters=filters))


def make_lead(lead_name: str, email: str):
	return frappe.get_doc({"doctype": "Lead", "lead_name": lead_name, "email_id": email}).insert(
		ignore_permissions=True
	)


def make_opportunity(lead, contact_email: str | None):
	return frappe.get_doc(
		{
			"doctype": "Opportunity",
			"opportunity_from": "Lead",
			"party_name": lead.name,
			"company": "_Test Company",
			"currency": "INR",
			"conversion_rate": 1,
			"contact_email": contact_email,
			"customer_name": lead.lead_name,
		}
	).insert(ignore_permissions=True)


def make_submitted_invoice(email: str):
	si = create_sales_invoice(do_not_save=1)
	si.contact_email = email
	si.set_posting_time = 1
	si.posting_date = add_days(nowdate(), -2)
	return si.submit()


def make_communication(sender: str, recipients: str, days: int):
	communication = frappe.get_doc(
		{"doctype": "Communication", "subject": "lead", "sender": sender, "recipients": recipients}
	).insert(ignore_permissions=True)
	frappe.db.set_value(
		"Communication",
		communication.name,
		"communication_date",
		add_days(nowdate(), days),
		update_modified=False,
	)


def get_report_rows(customer_name: str) -> list:
	filters = frappe._dict({"from_date": add_days(nowdate(), -30), "to_date": nowdate()})
	return [row for row in execute(filters)[1] if row[0] == customer_name]
