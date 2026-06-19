# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
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
		si.save()  # draft (docstatus 0 != 2); Date(creation) is today, within range

		# count query filters on `sender`; first_contact filters on `recipients` -> set both
		real = frappe.get_doc(
			{"doctype": "Communication", "subject": "real", "sender": email, "recipients": email}
		).insert(ignore_permissions=True)
		frappe.db.set_value(
			"Communication", real.name, "communication_date", add_days(nowdate(), -22), update_modified=False
		)
		nulldate = frappe.get_doc(
			{"doctype": "Communication", "subject": "nulldate", "sender": email, "recipients": email}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Communication", nulldate.name, "communication_date", None, update_modified=False)

		data = execute(frappe._dict({"from_date": add_days(nowdate(), -30), "to_date": nowdate()}))[1]
		# rows are lists: [customer, interactions, duration, support_tickets]
		row = next((r for r in data if r[0] == customer_name), None)
		self.assertIsNotNone(row, "lead's converted-customer row missing")
		# duration must be measured from the earliest REAL contact (22 days), not the NULL-dated one
		self.assertEqual(row[2], 22.0)
