# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_months, get_last_day, getdate

from erpnext.accounts.doctype.monthly_distribution.monthly_distribution import (
	MONTHS,
	get_percentage,
	get_periodwise_distribution_data,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestMonthlyDistribution(ERPNextTestSuite):
	"""Monthly Distribution spreads an amount across months. validate() enforces a
	100% total; get_percentage() sums the months that fall inside a period window."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_distribution(self, allocations):
		"""A row for each month: the given percentages, 0 for the other months."""
		allocations = dict(allocations)
		doc = frappe.new_doc("Monthly Distribution")
		doc.distribution_id = f"_Test MD {frappe.generate_hash(length=6)}"
		for month in MONTHS:
			doc.append("percentages", {"month": month, "percentage_allocation": allocations.get(month, 0)})
		return doc

	def test_get_months_populates_twelve_even_rows(self):
		doc = frappe.new_doc("Monthly Distribution")
		doc.distribution_id = "_Test MD Even"
		doc.get_months()

		self.assertEqual(len(doc.percentages), 12)
		self.assertEqual(doc.percentages[0].month, "January")
		self.assertEqual(doc.percentages[-1].month, "December")
		self.assertEqual([d.idx for d in doc.percentages], list(range(1, 13)))
		for d in doc.percentages:
			self.assertAlmostEqual(d.percentage_allocation, 100.0 / 12, places=4)
		# the auto-populated rows round to exactly 100 and pass validation
		doc.validate()

	def test_validate_rejects_total_other_than_100(self):
		doc = self.make_distribution([("January", 50), ("February", 30)])  # sums to 80
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_get_percentage_sums_period_window(self):
		doc = self.make_distribution([("January", 50), ("February", 30), ("March", 20)])
		doc.insert()  # total is 100, so validate passes

		# a quarter starting in January covers Jan+Feb+Mar
		self.assertEqual(get_percentage(doc, getdate("2026-01-01"), 3), 100)
		# a single month picks up only that month
		self.assertEqual(get_percentage(doc, getdate("2026-02-01"), 1), 30)
		# months with 0 contribute nothing
		self.assertEqual(get_percentage(doc, getdate("2026-04-01"), 1), 0)

	def test_periodwise_distribution_maps_each_period(self):
		doc = self.make_distribution([("January", 50), ("February", 30), ("March", 20)])
		doc.insert()

		period_list = [
			frappe._dict(key="q1", from_date=getdate("2026-01-01")),
			frappe._dict(key="q2", from_date=getdate("2026-04-01")),
		]
		data = get_periodwise_distribution_data(doc.name, period_list, "Quarterly")
		self.assertEqual(data["q1"], 100)  # Jan+Feb+Mar
		self.assertEqual(data["q2"], 0)  # Apr+May+Jun carry no allocation

	def test_validate_rejects_invalid_months(self):
		duplicate = self.make_distribution([("January", 100)])
		duplicate.percentages[1].month = "January"
		self.assertRaisesRegex(frappe.ValidationError, "one row for each month", duplicate.insert)

		misspelt = self.make_distribution([("January", 100)])
		misspelt.percentages[4].month = "Mai"
		self.assertRaisesRegex(frappe.ValidationError, "one row for each month", misspelt.insert)

		missing = self.make_distribution([("January", 100)])
		missing.percentages.pop()
		self.assertRaisesRegex(frappe.ValidationError, "one row for each month", missing.insert)

		negative = self.make_distribution([("January", -50), ("February", 150)])
		self.assertRaisesRegex(frappe.ValidationError, "between 0 and 100", negative.insert)

	def test_budget_migration_keeps_months(self):
		from erpnext.patches.v16_0.migrate_budget_records_to_new_structure import get_percentage_allocations

		doc = self.make_distribution([("December", 100)])
		doc.insert()
		allocations = get_percentage_allocations(
			frappe._dict(monthly_distribution=doc.name),
			frappe._dict(year_start_date=getdate("2026-04-01")),
		)
		# April to March: December is the ninth month
		self.assertEqual(allocations, [0] * 8 + [100] + [0] * 3)

	def make_migrated_budget(self, fiscal_year, percentages):
		"""A Budget as the old migration made it: the percentages in row order from the year start."""
		budget = frappe.new_doc("Budget")
		budget.update(
			{
				"budget_against": "Cost Center",
				"company": "_Test Company",
				"cost_center": "_Test Cost Center - _TC",
				"account": "_Test Account Cost for Goods Sold - _TC",
				"from_fiscal_year": fiscal_year,
				"to_fiscal_year": fiscal_year,
				"budget_start_date": "2061-04-01",
				"budget_end_date": "2062-03-31",
				"budget_amount": 1200,
				"distribution_frequency": "Monthly",
				"distribute_equally": 1 if len(set(percentages)) == 1 else 0,
			}
		)
		for i, percent in enumerate(percentages):
			start = add_months(getdate("2061-04-01"), i)
			budget.append(
				"budget_distribution",
				{
					"start_date": start,
					"end_date": get_last_day(start),
					"percent": percent,
					"amount": 1200 * percent / 100,
				},
			)
		budget.flags.ignore_validate = True
		budget.insert(ignore_mandatory=True)
		return budget

	def get_months_with_percent(self, budget_name):
		rows = frappe.get_all(
			"Budget Distribution",
			filters={"parent": budget_name},
			fields=["start_date", "percent", "amount"],
			order_by="idx asc",
		)
		return [(r.start_date, r.percent, r.amount) for r in rows if r.percent]

	def test_fix_migrated_budget_months(self):
		from erpnext.patches.v16_0.fix_budget_distribution_month_order import fix_migrated_budgets

		fiscal_year = "_Test MD Fiscal Year 2061-2062"
		if not frappe.db.exists("Fiscal Year", fiscal_year):
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": fiscal_year,
					"year_start_date": "2061-04-01",
					"year_end_date": "2062-03-31",
				}
			).insert()

		distribution = self.make_distribution([("December", 100)])
		distribution.insert()
		# December's row on the twelfth month (March)
		budget = self.make_migrated_budget(
			fiscal_year, [row.percentage_allocation for row in distribution.percentages]
		)
		edited = self.make_migrated_budget(
			fiscal_year, [row.percentage_allocation for row in distribution.percentages]
		)
		# amount changed after the migration, percent left as it was
		frappe.db.set_value("Budget Distribution", {"parent": edited.name, "idx": 12}, "amount", 1000)

		old = frappe._dict(
			name="_Test MD Old Budget",
			modified=frappe.utils.now_datetime(),
			company="_Test Company",
			budget_against="Cost Center",
			cost_center="_Test Cost Center - _TC",
			project=None,
			fiscal_year=fiscal_year,
			monthly_distribution=distribution.name,
		)
		# made after the old budget was cancelled, so not by the migration
		later = self.make_migrated_budget(
			fiscal_year, [row.percentage_allocation for row in distribution.percentages]
		)
		fix_migrated_budgets(old)

		self.assertEqual(self.get_months_with_percent(budget.name), [(getdate("2061-12-01"), 100, 1200)])
		self.assertEqual(self.get_months_with_percent(edited.name)[0][0], getdate("2062-03-01"))
		self.assertEqual(self.get_months_with_percent(later.name)[0][0], getdate("2062-03-01"))

		# a budget whose distribution was changed after the migration is left as it is
		frappe.db.set_value("Budget Distribution", {"parent": budget.name, "idx": 1}, "percent", 0.5)
		fix_migrated_budgets(old)
		self.assertEqual(
			frappe.db.get_value("Budget Distribution", {"parent": budget.name, "idx": 9}, "percent"), 100
		)

	def test_fix_migrated_budget_months_partial_distribution(self):
		from erpnext.patches.v16_0.fix_budget_distribution_month_order import fix_migrated_budgets

		fiscal_year = "_Test MD Fiscal Year 2061-2062"
		if not frappe.db.exists("Fiscal Year", fiscal_year):
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": fiscal_year,
					"year_start_date": "2061-04-01",
					"year_end_date": "2062-03-31",
				}
			).insert()

		# saved before months were validated: only the months with an allocation
		distribution = self.make_distribution([("December", 100)])
		distribution.percentages = [row for row in distribution.percentages if row.percentage_allocation]
		distribution.flags.ignore_validate = True
		distribution.insert()

		# the migration made one row, on April
		budget = self.make_migrated_budget(fiscal_year, [100])
		fix_migrated_budgets(
			frappe._dict(
				name="_Test MD Old Budget",
				modified=frappe.utils.now_datetime(),
				company="_Test Company",
				budget_against="Cost Center",
				cost_center="_Test Cost Center - _TC",
				project=None,
				fiscal_year=fiscal_year,
				monthly_distribution=distribution.name,
			)
		)

		self.assertEqual(
			frappe.db.count("Budget Distribution", {"parent": budget.name, "parenttype": "Budget"}), 12
		)
		self.assertEqual(self.get_months_with_percent(budget.name), [(getdate("2061-12-01"), 100, 1200)])
		self.assertEqual(frappe.db.get_value("Budget", budget.name, "distribute_equally"), 0)
