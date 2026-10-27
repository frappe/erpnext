# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, random_string

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.report.customer_acquisition_and_loyalty.customer_acquisition_and_loyalty import (
	get_customer_stats,
)


class TestCustomerAcquisitionAndLoyalty(FrappeTestCase):
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

		# Two submitted invoices for the SAME customer in the SAME month: the customer is
		# acquired that month, so they count once as "new" and never as "repeat"; both
		# invoices' revenue lands in the new bucket.
		si1 = create_sales_invoice(
			customer=customer.name, company="_Test Company", posting_date=first_date, rate=100
		)
		si2 = create_sales_invoice(
			customer=customer.name, company="_Test Company", posting_date=second_date, rate=250
		)

		stats = get_customer_stats(filters)
		bucket = stats.get(month_key)
		self.assertIsNotNone(bucket, "expected a bucket for posting month " + month_key)

		# One NEW customer, no REPEAT: a second invoice in the acquisition month does not
		# turn one customer into two.
		self.assertEqual(bucket["new"][0] - base_new, 1)
		self.assertEqual(bucket["repeat"][0] - base_repeat, 0)

		# Both invoices' revenue is attributed to the new bucket; repeat is untouched.
		self.assertAlmostEqual(bucket["new"][1] - base_new_rev, si1.base_grand_total + si2.base_grand_total)
		self.assertAlmostEqual(bucket["repeat"][1] - base_repeat_rev, 0.0)

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

		# pin both invoices to the customer's territory so they land in the "_Test Territory"
		# bucket (the customer's acquisition territory): one "new" customer, both invoices' revenue
		si1 = create_sales_invoice(
			customer=customer.name,
			company="_Test Company",
			posting_date=first_date,
			rate=100,
			do_not_save=True,
		)
		si1.territory = territory
		si1.insert()
		si1.submit()
		si2 = create_sales_invoice(
			customer=customer.name,
			company="_Test Company",
			posting_date=second_date,
			rate=250,
			do_not_save=True,
		)
		si2.territory = territory
		si2.insert()
		si2.submit()
		# Guard the test's premise: territory must really be on the invoices.
		self.assertEqual(si1.territory, territory)
		self.assertEqual(si2.territory, territory)

		stats = get_customer_stats(filters, tree_view=True)
		bucket = stats.get(territory)
		self.assertIsNotNone(bucket, "expected a bucket keyed by territory " + territory)

		# One NEW customer, no REPEAT, in the acquisition territory bucket.
		self.assertEqual(bucket["new"][0] - base_new, 1)
		self.assertEqual(bucket["repeat"][0] - base_repeat, 0)

		# Both invoices' revenue follows into the new bucket; repeat is untouched.
		self.assertAlmostEqual(bucket["new"][1] - base_new_rev, si1.base_grand_total + si2.base_grand_total)
		self.assertAlmostEqual(bucket["repeat"][1] - base_repeat_rev, 0.0)

	def test_credit_note_nets_revenue_without_counting(self):
		# A credit note must not add a customer to the headcount, but its (negative) amount
		# should still net down that customer's revenue for the period.
		first_date = "2017-06-05"
		return_date = "2017-06-20"
		month_key = getdate(first_date).strftime("%Y-%m")
		filters = frappe._dict(
			{"from_date": "2017-01-01", "to_date": "2017-06-30", "company": "_Test Company"}
		)

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test CAL Return Customer " + random_string(8),
				"customer_group": "_Test Customer Group",
				"customer_type": "Individual",
				"territory": "_Test Territory",
			}
		).insert()

		base = get_customer_stats(filters)
		base_bucket = base.get(month_key, {"new": [0, 0.0], "repeat": [0, 0.0]})
		base_new, base_new_rev = base_bucket["new"]
		base_repeat, base_repeat_rev = base_bucket["repeat"]

		si = create_sales_invoice(
			customer=customer.name, company="_Test Company", posting_date=first_date, rate=100
		)
		cn = create_sales_invoice(
			customer=customer.name,
			company="_Test Company",
			posting_date=return_date,
			qty=-1,
			rate=100,
			is_return=1,
			return_against=si.name,
		)

		bucket = get_customer_stats(filters).get(month_key)
		self.assertIsNotNone(bucket, "expected a bucket for posting month " + month_key)

		# One new customer, no repeat added by the credit note.
		self.assertEqual(bucket["new"][0] - base_new, 1)
		self.assertEqual(bucket["repeat"][0] - base_repeat, 0)

		# Revenue is the sale netted by the credit note, all in the new bucket.
		self.assertAlmostEqual(bucket["new"][1] - base_new_rev, si.base_grand_total + cn.base_grand_total)
		self.assertAlmostEqual(bucket["repeat"][1] - base_repeat_rev, 0.0)
