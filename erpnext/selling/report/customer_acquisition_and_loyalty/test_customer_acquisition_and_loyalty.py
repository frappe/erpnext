# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import getdate, random_string

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.report.customer_acquisition_and_loyalty.customer_acquisition_and_loyalty import (
	get_customer_stats,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestCustomerAcquisitionAndLoyalty(ERPNextTestSuite):
	def test_new_vs_repeat_classification(self):
		# Use a posting month in the past so the YYYY-MM bucket is unlikely to collide
		# with other fixtures; deltas vs a baseline still neutralise any overlap.
		first_date = "2017-04-05"
		second_date = "2017-04-20"
		month_key = getdate(first_date).strftime("%Y-%m")
		# source uses both filters.get(...) and attribute access (filters.from_date),
		# so pass a frappe._dict the way the report's execute() does.
		filters = frappe._dict(
			{"from_date": "2017-01-01", "to_date": "2017-04-30", "company": "_Test Company"}
		)

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test CAL Customer " + random_string(8),
				"customer_group": "_Test Customer Group",
				"customer_type": "Individual",
				"territory": "_Test Territory",
			}
		).insert()

		# Baseline before adding any activity for this customer.
		base = get_customer_stats(filters)
		base_bucket = base.get(month_key, {"new": [0, 0.0], "repeat": [0, 0.0]})
		base_new = base_bucket["new"][0]
		base_new_rev = base_bucket["new"][1]
		base_repeat = base_bucket["repeat"][0]
		base_repeat_rev = base_bucket["repeat"][1]

		# Two submitted invoices for the SAME customer in the SAME month:
		# the earlier one is the customer's FIRST invoice -> "new", the later -> "repeat".
		si1 = create_sales_invoice(
			customer=customer.name, company="_Test Company", posting_date=first_date, rate=100
		)
		si2 = create_sales_invoice(
			customer=customer.name, company="_Test Company", posting_date=second_date, rate=250
		)

		stats = get_customer_stats(filters)
		bucket = stats.get(month_key)
		self.assertIsNotNone(bucket, "expected a bucket for posting month " + month_key)

		# Exactly one NEW and one REPEAT were added for this customer's activity.
		self.assertEqual(bucket["new"][0] - base_new, 1)
		self.assertEqual(bucket["repeat"][0] - base_repeat, 1)

		# Revenue is attributed by base_grand_total of the corresponding invoice:
		# the first (new) invoice carries si1's total, the second (repeat) carries si2's.
		self.assertAlmostEqual(bucket["new"][1] - base_new_rev, si1.base_grand_total)
		self.assertAlmostEqual(bucket["repeat"][1] - base_repeat_rev, si2.base_grand_total)

	def test_territory_tree_view_classification(self):
		# Covers the tree_view=True path of get_customer_stats, where buckets are keyed
		# by Sales Invoice territory instead of YYYY-MM. This is the keying that
		# get_data_by_territory() (which also drives frappe.get_all("Territory", ...))
		# consumes. A fresh customer on "_Test Territory" makes the bucket deterministic.
		territory = "_Test Territory"
		first_date = "2017-05-05"
		second_date = "2017-05-20"
		# get_customer_stats reads filters.from_date (attribute) and filters.get("to_date"),
		# so build the _dict the same way execute() does.
		filters = frappe._dict(
			{"from_date": "2017-01-01", "to_date": "2017-05-31", "company": "_Test Company"}
		)

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test CAL Territory Customer " + random_string(8),
				"customer_group": "_Test Customer Group",
				"customer_type": "Individual",
				"territory": territory,
			}
		).insert()

		# Baseline for the territory bucket before this customer has any invoices.
		base = get_customer_stats(filters, tree_view=True)
		base_bucket = base.get(territory, {"new": [0, 0.0], "repeat": [0, 0.0]})
		base_new = base_bucket["new"][0]
		base_new_rev = base_bucket["new"][1]
		base_repeat = base_bucket["repeat"][0]
		base_repeat_rev = base_bucket["repeat"][1]

		# get_party_details copies the customer's territory onto the invoice, so both
		# invoices land in the "_Test Territory" bucket: first -> "new", second -> "repeat".
		si1 = create_sales_invoice(
			customer=customer.name, company="_Test Company", posting_date=first_date, rate=100
		)
		si2 = create_sales_invoice(
			customer=customer.name, company="_Test Company", posting_date=second_date, rate=250
		)
		# Guard the test's premise: territory must really be on the invoices.
		self.assertEqual(si1.territory, territory)
		self.assertEqual(si2.territory, territory)

		stats = get_customer_stats(filters, tree_view=True)
		bucket = stats.get(territory)
		self.assertIsNotNone(bucket, "expected a bucket keyed by territory " + territory)

		# Exactly one NEW and one REPEAT attributable to this customer in the bucket.
		self.assertEqual(bucket["new"][0] - base_new, 1)
		self.assertEqual(bucket["repeat"][0] - base_repeat, 1)

		# Revenue follows base_grand_total of the corresponding invoice.
		self.assertAlmostEqual(bucket["new"][1] - base_new_rev, si1.base_grand_total)
		self.assertAlmostEqual(bucket["repeat"][1] - base_repeat_rev, si2.base_grand_total)
