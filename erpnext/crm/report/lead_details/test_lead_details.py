# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.crm.report.lead_details.lead_details import get_data
from erpnext.tests.utils import ERPNextTestSuite


class TestLeadDetailsReport(ERPNextTestSuite):
	def test_address_column_omits_empty_line(self):
		"""An empty address_line2 is '' on MariaDB but NULL on Postgres; CONCAT_WS
		keeps the empty string (trailing ', ') on MariaDB while Postgres drops it.
		The report must render the same clean address on both engines."""
		lead = frappe.get_doc(
			{"doctype": "Lead", "lead_name": "_Test PG Lead Address", "company": "_Test Company"}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "_Test PG Lead Address",
				"address_type": "Billing",
				"address_line1": "221B Baker Street",
				"address_line2": "",
				"city": "London",
				"country": "United Kingdom",
				"links": [{"link_doctype": "Lead", "link_name": lead.name}],
			}
		).insert()

		filters = frappe._dict(
			company="_Test Company", from_date=add_days(today(), -1), to_date=add_days(today(), 1)
		)
		row = next(r for r in get_data(filters) if r.get("name") == lead.name)
		self.assertEqual(row.get("address"), "221B Baker Street")
