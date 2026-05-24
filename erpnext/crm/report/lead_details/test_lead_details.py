# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, getdate

from erpnext.crm.report.lead_details.lead_details import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestLeadDetails(ERPNextTestSuite):
def setUp(self):
self.company = "_Test Company"
self.lead = create_test_lead(self.company)

def tearDown(self):
try:
frappe.delete_doc("Lead", self.lead.name, force=True)
finally:
super().tearDown()

def test_lead_details_returns_data(self):
"""Test that the report returns data for a valid company and date range."""
filters = frappe._dict(
company=self.company,
from_date=add_days(getdate(), -1),
to_date=add_days(getdate(), 1),
)
_, data = execute(filters)
self.assertTrue(len(data) > 0, "Report should return at least one row")

def test_lead_details_columns_include_designation(self):
"""Test that the designation column is present in the report output."""
filters = frappe._dict(
company=self.company,
from_date=add_days(getdate(), -1),
to_date=add_days(getdate(), 1),
)
columns, _ = execute(filters)
fieldnames = [col.get("fieldname") if isinstance(col, dict) else col for col in columns]
self.assertIn("designation", fieldnames, "Designation column should be present")

def test_lead_details_filter_by_status(self):
"""Test that filtering by status returns only matching leads."""
filters = frappe._dict(
company=self.company,
from_date=add_days(getdate(), -1),
to_date=add_days(getdate(), 1),
status="Open",
)
_, data = execute(filters)
self.assertTrue(len(data) > 0, "Should return at least one row for status filter")
for row in data:
self.assertEqual(row.get("status"), "Open", "All returned leads should have status Open")

def test_lead_details_date_filter(self):
"""Test that leads outside the date range are excluded."""
filters = frappe._dict(
company=self.company,
from_date=add_days(getdate(), -30),
to_date=add_days(getdate(), -29),
)
_, data = execute(filters)
lead_names = [row.get("name") for row in data]
self.assertNotIn(self.lead.name, lead_names, "Lead should not appear in old date range")


def create_test_lead(company):
lead = frappe.get_doc({
"doctype": "Lead",
"lead_name": "_Test Lead Designation",
"email_id": "test_designation_lead@example.com",
"status": "Open",
"company": company,
})
lead.insert(ignore_permissions=True)
return lead
