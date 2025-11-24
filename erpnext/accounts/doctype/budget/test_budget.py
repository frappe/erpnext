# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.client import submit
from frappe.utils import add_days, flt, get_first_day, get_last_day, getdate, now_datetime, nowdate

from erpnext.accounts.doctype.budget.budget import (
	BudgetError,
	get_accumulated_monthly_budget,
	get_actual_expense,
	revise_budget,
)
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.utils import get_fiscal_year
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.tests.utils import ERPNextTestSuite


class TestBudget(ERPNextTestSuite):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.make_monthly_distribution()
		cls.make_projects()

	def setUp(self):
		frappe.db.set_single_value("Accounts Settings", "use_legacy_budget_controller", False)
		self.company = "_Test Company"
		self.fiscal_year = frappe.db.get_value("Fiscal Year", {}, "name")
		self.account = "_Test Account Cost for Goods Sold - _TC"
		self.cost_center = "_Test Cost Center - _TC"

	def test_monthly_budget_crossed_ignore(self):
		set_total_expense_zero(nowdate(), "cost_center")

		budget = make_budget(budget_against="Cost Center", do_not_save=False, submit_budget=True)

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			40000,
			"_Test Cost Center - _TC",
			posting_date=nowdate(),
			submit=True,
		)

		self.assertTrue(
			frappe.db.get_value("GL Entry", {"voucher_type": "Journal Entry", "voucher_no": jv.name})
		)

		budget.cancel()
		jv.cancel()

	def test_monthly_budget_crossed_stop1(self):
		set_total_expense_zero(nowdate(), "cost_center")

		budget = make_budget(budget_against="Cost Center", do_not_save=False, submit_budget=True)

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		accumulated_limit = get_accumulated_monthly_budget(
			budget.name,
			nowdate(),
		)
		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			accumulated_limit + 1,
			"_Test Cost Center - _TC",
			posting_date=nowdate(),
		)

		self.assertRaises(BudgetError, jv.submit)

		budget.load_from_db()
		budget.cancel()

	def test_exception_approver_role(self):
		set_total_expense_zero(nowdate(), "cost_center")

		budget = make_budget(budget_against="Cost Center", do_not_save=False, submit_budget=True)

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		accumulated_limit = get_accumulated_monthly_budget(budget.name, nowdate())
		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			accumulated_limit + 1,
			"_Test Cost Center - _TC",
			posting_date=nowdate(),
		)

		self.assertRaises(BudgetError, jv.submit)

		frappe.db.set_value("Company", budget.company, "exception_budget_approver_role", "Accounts User")

		jv.submit()
		self.assertEqual(frappe.db.get_value("Journal Entry", jv.name, "docstatus"), 1)
		jv.cancel()

		frappe.db.set_value("Company", budget.company, "exception_budget_approver_role", "")

		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_crossed_for_mr(self):
		budget = make_budget(
			applicable_on_material_request=1,
			applicable_on_purchase_order=1,
			action_if_accumulated_monthly_budget_exceeded_on_mr="Stop",
			budget_against="Cost Center",
			do_not_save=False,
			submit_budget=True,
		)

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		accumulated_limit = get_accumulated_monthly_budget(
			budget.name,
			nowdate(),
		)
		mr = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"transaction_date": nowdate(),
				"company": budget.company,
				"items": [
					{
						"item_code": "_Test Item",
						"qty": 1,
						"uom": "_Test UOM",
						"warehouse": "_Test Warehouse - _TC",
						"schedule_date": nowdate(),
						"rate": accumulated_limit + 1,
						"expense_account": "_Test Account Cost for Goods Sold - _TC",
						"cost_center": "_Test Cost Center - _TC",
					}
				],
			}
		)

		mr.set_missing_values()

		self.assertRaises(BudgetError, mr.submit)

		budget.load_from_db()
		budget.cancel()
		mr.cancel()

	def test_monthly_budget_crossed_for_po(self):
		budget = make_budget(
			applicable_on_purchase_order=1,
			action_if_accumulated_monthly_budget_exceeded_on_po="Stop",
			budget_against="Cost Center",
			do_not_save=False,
			submit_budget=True,
		)

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		accumulated_limit = get_accumulated_monthly_budget(
			budget.name,
			nowdate(),
		)
		po = create_purchase_order(
			transaction_date=nowdate(), qty=1, rate=accumulated_limit + 1, do_not_submit=True
		)

		po.set_missing_values()

		self.assertRaises(BudgetError, po.submit)

		budget.load_from_db()
		budget.cancel()
		po.cancel()

	def test_monthly_budget_crossed_stop2(self):
		set_total_expense_zero(nowdate(), "project")

		budget = make_budget(budget_against="Project", do_not_save=False, submit_budget=True)

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		project = frappe.get_value("Project", {"project_name": "_Test Project"})
		accumulated_limit = get_accumulated_monthly_budget(
			budget.name,
			nowdate(),
		)
		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			accumulated_limit + 1,
			"_Test Cost Center - _TC",
			project=project,
			posting_date=nowdate(),
		)

		self.assertRaises(BudgetError, jv.submit)

		budget.load_from_db()
		budget.cancel()

	def test_yearly_budget_crossed_stop1(self):
		set_total_expense_zero(nowdate(), "cost_center")

		budget = make_budget(budget_against="Cost Center", do_not_save=False, submit_budget=True)

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			250000,
			"_Test Cost Center - _TC",
			posting_date=nowdate(),
		)

		self.assertRaises(BudgetError, jv.submit)

		budget.cancel()

	def test_yearly_budget_crossed_stop2(self):
		set_total_expense_zero(nowdate(), "project")

		budget = make_budget(budget_against="Project", do_not_save=False, submit_budget=True)

		project = frappe.get_value("Project", {"project_name": "_Test Project"})

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			250000,
			"_Test Cost Center - _TC",
			project=project,
			posting_date=nowdate(),
		)

		self.assertRaises(BudgetError, jv.submit)

		budget.cancel()

	def test_monthly_budget_on_cancellation1(self):
		set_total_expense_zero(nowdate(), "cost_center")

		budget = make_budget(budget_against="Cost Center", do_not_save=False, submit_budget=True)
		month = now_datetime().month
		if month > 9:
			month = 9

		for _i in range(month + 1):
			jv = make_journal_entry(
				"_Test Account Cost for Goods Sold - _TC",
				"_Test Bank - _TC",
				20000,
				"_Test Cost Center - _TC",
				posting_date=nowdate(),
				submit=True,
			)

			self.assertTrue(
				frappe.db.get_value("GL Entry", {"voucher_type": "Journal Entry", "voucher_no": jv.name})
			)

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		self.assertRaises(BudgetError, jv.cancel)

		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_on_cancellation2(self):
		set_total_expense_zero(nowdate(), "project")

		budget = make_budget(budget_against="Project", do_not_save=False, submit_budget=True)
		month = now_datetime().month
		if month > 9:
			month = 9

		project = frappe.get_value("Project", {"project_name": "_Test Project"})
		for _i in range(month + 1):
			jv = make_journal_entry(
				"_Test Account Cost for Goods Sold - _TC",
				"_Test Bank - _TC",
				20000,
				"_Test Cost Center - _TC",
				posting_date=nowdate(),
				submit=True,
				project=project,
			)

			self.assertTrue(
				frappe.db.get_value("GL Entry", {"voucher_type": "Journal Entry", "voucher_no": jv.name})
			)

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		self.assertRaises(BudgetError, jv.cancel)

		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_against_group_cost_center(self):
		set_total_expense_zero(nowdate(), "cost_center")
		set_total_expense_zero(nowdate(), "cost_center", "_Test Cost Center 2 - _TC")

		budget = make_budget(
			budget_against="Cost Center",
			cost_center="_Test Company - _TC",
			do_not_save=False,
			submit_budget=True,
		)
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		accumulated_limit = get_accumulated_monthly_budget(
			budget.name,
			nowdate(),
		)
		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			accumulated_limit + 1,
			"_Test Cost Center 2 - _TC",
			posting_date=nowdate(),
		)

		self.assertRaises(BudgetError, jv.submit)

		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_against_parent_group_cost_center(self):
		cost_center = "_Test Cost Center 3 - _TC"

		if not frappe.db.exists("Cost Center", cost_center):
			frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": "_Test Cost Center 3",
					"parent_cost_center": "_Test Company - _TC",
					"company": "_Test Company",
					"is_group": 0,
				}
			).insert(ignore_permissions=True)

		budget = make_budget(
			budget_against="Cost Center", cost_center=cost_center, do_not_save=False, submit_budget=True
		)
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		accumulated_limit = get_accumulated_monthly_budget(
			budget.name,
			nowdate(),
		)
		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			accumulated_limit + 1,
			cost_center,
			posting_date=nowdate(),
		)

		self.assertRaises(BudgetError, jv.submit)

		budget.load_from_db()
		budget.cancel()
		jv.cancel()

	def test_monthly_budget_against_main_cost_center(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.cost_center_allocation.test_cost_center_allocation import (
			create_cost_center_allocation,
		)

		cost_centers = [
			"Main Budget Cost Center 1",
			"Sub Budget Cost Center 1",
			"Sub Budget Cost Center 2",
		]

		for cc in cost_centers:
			create_cost_center(cost_center_name=cc, company="_Test Company")

		create_cost_center_allocation(
			"_Test Company",
			"Main Budget Cost Center 1 - _TC",
			{"Sub Budget Cost Center 1 - _TC": 60, "Sub Budget Cost Center 2 - _TC": 40},
		)

		make_budget(
			budget_against="Cost Center",
			cost_center="Main Budget Cost Center 1 - _TC",
			do_not_save=False,
			submit_budget=True,
		)

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			400000,
			"Main Budget Cost Center 1 - _TC",
			posting_date=nowdate(),
		)

		self.assertRaises(BudgetError, jv.submit)

	def test_action_for_cumulative_limit(self):
		set_total_expense_zero(nowdate(), "cost_center")

		budget = make_budget(
			budget_against="Cost Center",
			applicable_on_cumulative_expense=True,
			do_not_save=False,
			submit_budget=True,
		)

		accumulated_limit = get_accumulated_monthly_budget(budget.name, nowdate())

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			accumulated_limit - 1,
			"_Test Cost Center - _TC",
			posting_date=nowdate(),
		)
		jv.submit()

		frappe.db.set_value(
			"Budget", budget.name, "action_if_accumulated_monthly_exceeded_on_cumulative_expense", "Stop"
		)
		po = create_purchase_order(
			transaction_date=nowdate(), qty=1, rate=accumulated_limit + 1, do_not_submit=True
		)
		po.set_missing_values()

		self.assertRaises(BudgetError, po.submit)

		frappe.db.set_value(
			"Budget", budget.name, "action_if_accumulated_monthly_exceeded_on_cumulative_expense", "Ignore"
		)
		po.submit()

		budget.load_from_db()
		budget.cancel()
		po.cancel()
		jv.cancel()

	def test_fiscal_year_validation(self):
		frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": "2100",
				"year_start_date": "2100-04-01",
				"year_end_date": "2101-03-31",
				"companies": [{"company": "_Test Company"}],
			}
		).insert(ignore_permissions=True)

		budget = make_budget(
			budget_against="Cost Center",
			from_fiscal_year="2100",
			to_fiscal_year="2099",
			do_not_save=True,
			submit_budget=False,
		)

		with self.assertRaises(frappe.ValidationError):
			budget.save()

	def test_total_distribution_equals_budget(self):
		budget = make_budget(
			budget_against="Cost Center",
			applicable_on_cumulative_expense=True,
			distribute_equally=0,
			budget_amount=12000,
			do_not_save=False,
			submit_budget=False,
		)

		for row in budget.budget_distribution:
			row.amount = 2000

		with self.assertRaises(frappe.ValidationError):
			budget.save()

	def test_evenly_distribute_budget(self):
		budget = make_budget(
			budget_against="Cost Center", budget_amount=120000, do_not_save=False, submit_budget=True
		)

		total = sum([d.amount for d in budget.budget_distribution])
		self.assertEqual(flt(total), 120000)
		self.assertTrue(all(d.amount == 10000 for d in budget.budget_distribution))

	def test_create_revised_budget(self):
		budget = make_budget(
			budget_against="Cost Center", budget_amount=120000, do_not_save=False, submit_budget=True
		)

		revised_name = revise_budget(budget.name)

		revised_budget = frappe.get_doc("Budget", revised_name)
		self.assertNotEqual(budget.name, revised_budget.name)
		self.assertEqual(revised_budget.budget_against, budget.budget_against)
		self.assertEqual(revised_budget.budget_amount, budget.budget_amount)

		old_budget = frappe.get_doc("Budget", budget.name)
		self.assertEqual(old_budget.docstatus, 2)

	def test_revision_preserves_distribution(self):
		set_total_expense_zero(nowdate(), "cost_center", "_Test Cost Center - _TC")
		budget = make_budget(
			budget_against="Cost Center", budget_amount=120000, do_not_save=False, submit_budget=True
		)

		revised_name = revise_budget(budget.name)
		revised_budget = frappe.get_doc("Budget", revised_name)

		self.assertGreater(len(revised_budget.budget_distribution), 0)

		total = sum(row.amount for row in revised_budget.budget_distribution)
		self.assertEqual(total, revised_budget.budget_amount)

	def test_manual_budget_amount_total(self):
		budget = make_budget(
			budget_against="Cost Center",
			distribute_equally=0,
			budget_amount=30000,
			budget_start_date="2025-04-01",
			budget_end_date="2025-06-30",
			do_not_save=False,
			submit_budget=False,
		)

		budget.budget_distribution = []

		for row in [
			{"start_date": "2025-04-01", "end_date": "2025-04-30", "amount": 10000, "percent": 33.33},
			{"start_date": "2025-05-01", "end_date": "2025-05-31", "amount": 15000, "percent": 50.00},
			{"start_date": "2025-06-01", "end_date": "2025-06-30", "amount": 5000, "percent": 16.67},
		]:
			budget.append("budget_distribution", row)

		budget.save()

		total_child_amount = sum(row.amount for row in budget.budget_distribution)

		self.assertEqual(total_child_amount, budget.budget_amount)

	def test_fiscal_year_company_mismatch(self):
		budget = make_budget(budget_against="Cost Center", do_not_save=True, submit_budget=False)

		fy = frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": "2099",
				"year_start_date": "2099-04-01",
				"year_end_date": "2100-03-31",
				"companies": [{"company": "_Test Company 2"}],
			}
		).insert(ignore_permissions=True)

		budget.from_fiscal_year = fy.name
		budget.to_fiscal_year = fy.name
		budget.company = "_Test Company"

		with self.assertRaises(frappe.ValidationError):
			budget.save()

	def test_manual_distribution_total_equals_budget_amount(self):
		budget = make_budget(
			budget_against="Cost Center",
			cost_center="_Test Cost Center - _TC",
			distribute_equally=0,
			budget_amount=12000,
			do_not_save=False,
			submit_budget=False,
		)

		for d in budget.budget_distribution:
			d.amount = 2000

		with self.assertRaises(frappe.ValidationError):
			budget.save()

	def test_duplicate_budget_validation(self):
		budget = make_budget(
			budget_against="Cost Center",
			distribute_equally=1,
			budget_amount=15000,
			do_not_save=False,
			submit_budget=True,
		)

		new_budget = frappe.new_doc("Budget")
		new_budget.company = "_Test Company"
		new_budget.from_fiscal_year = budget.from_fiscal_year
		new_budget.to_fiscal_year = new_budget.from_fiscal_year
		new_budget.budget_against = "Cost Center"
		new_budget.cost_center = "_Test Cost Center - _TC"
		new_budget.account = "_Test Account Cost for Goods Sold - _TC"
		new_budget.budget_amount = 10000

		with self.assertRaises(frappe.ValidationError):
			new_budget.insert()


def set_total_expense_zero(posting_date, budget_against_field=None, budget_against_CC=None):
	if budget_against_field == "project":
		budget_against = frappe.db.get_value("Project", {"project_name": "_Test Project"})
	else:
		budget_against = budget_against_CC or "_Test Cost Center - _TC"

	fiscal_year = get_fiscal_year(nowdate())[0]
	fiscal_year_start_date, fiscal_year_end_date = get_fiscal_year(nowdate())[1:3]

	args = frappe._dict(
		{
			"account": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"month_end_date": posting_date,
			"company": "_Test Company",
			"from_fiscal_year": fiscal_year,
			"to_fiscal_year": fiscal_year,
			"budget_against_field": budget_against_field,
			"budget_start_date": fiscal_year_start_date,
			"budget_end_date": fiscal_year_end_date,
		}
	)

	if not args.get(budget_against_field):
		args[budget_against_field] = budget_against

	args.budget_against_doctype = frappe.unscrub(budget_against_field)

	if frappe.get_cached_value("DocType", args.budget_against_doctype, "is_tree"):
		args.is_tree = True
	else:
		args.is_tree = False

	existing_expense = get_actual_expense(args)

	if existing_expense:
		if budget_against_field == "cost_center":
			make_journal_entry(
				"_Test Account Cost for Goods Sold - _TC",
				"_Test Bank - _TC",
				-existing_expense,
				"_Test Cost Center - _TC",
				posting_date=nowdate(),
				submit=True,
			)
		elif budget_against_field == "project":
			make_journal_entry(
				"_Test Account Cost for Goods Sold - _TC",
				"_Test Bank - _TC",
				-existing_expense,
				"_Test Cost Center - _TC",
				submit=True,
				project=budget_against,
				posting_date=nowdate(),
			)


def make_budget(**args):
	args = frappe._dict(args)

	budget_against = args.budget_against
	cost_center = args.cost_center
	fiscal_year = get_fiscal_year(nowdate())[0]

	if budget_against == "Project":
		project = frappe.get_value("Project", {"project_name": "_Test Project"})
		budget_list = frappe.get_all(
			"Budget",
			filters={
				"project": project,
				"account": "_Test Account Cost for Goods Sold - _TC",
			},
			pluck="name",
		)
	else:
		budget_list = frappe.get_all(
			"Budget",
			filters={
				"cost_center": cost_center or "_Test Cost Center - _TC",
				"account": "_Test Account Cost for Goods Sold - _TC",
			},
			pluck="name",
		)

	for name in budget_list:
		doc = frappe.get_doc("Budget", name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Budget", name, force=True, ignore_missing=True)

	budget = frappe.new_doc("Budget")

	if budget_against == "Project":
		budget.project = frappe.get_value("Project", {"project_name": "_Test Project"})
	else:
		budget.cost_center = cost_center or "_Test Cost Center - _TC"

	budget.from_fiscal_year = args.from_fiscal_year or fiscal_year
	budget.to_fiscal_year = args.to_fiscal_year or fiscal_year
	budget.company = "_Test Company"
	budget.account = "_Test Account Cost for Goods Sold - _TC"
	budget.budget_amount = args.budget_amount or 200000
	budget.applicable_on_booking_actual_expenses = 1
	budget.action_if_annual_budget_exceeded = "Stop"
	budget.action_if_accumulated_monthly_budget_exceeded = "Ignore"
	budget.budget_against = budget_against

	budget.distribution_frequency = "Monthly"
	budget.distribute_equally = args.get("distribute_equally", 1)

	if args.applicable_on_material_request:
		budget.applicable_on_material_request = 1
		budget.action_if_annual_budget_exceeded_on_mr = args.action_if_annual_budget_exceeded_on_mr or "Warn"
		budget.action_if_accumulated_monthly_budget_exceeded_on_mr = (
			args.action_if_accumulated_monthly_budget_exceeded_on_mr or "Warn"
		)

	if args.applicable_on_purchase_order:
		budget.applicable_on_purchase_order = 1
		budget.action_if_annual_budget_exceeded_on_po = args.action_if_annual_budget_exceeded_on_po or "Warn"
		budget.action_if_accumulated_monthly_budget_exceeded_on_po = (
			args.action_if_accumulated_monthly_budget_exceeded_on_po or "Warn"
		)

	if args.applicable_on_cumulative_expense:
		budget.applicable_on_cumulative_expense = 1
		budget.action_if_annual_exceeded_on_cumulative_expense = (
			args.action_if_annual_exceeded_on_cumulative_expense or "Warn"
		)
		budget.action_if_accumulated_monthly_exceeded_on_cumulative_expense = (
			args.action_if_accumulated_monthly_exceeded_on_cumulative_expense or "Warn"
		)

	if not args.do_not_save:
		try:
			budget.insert(ignore_if_duplicate=True)
		except frappe.DuplicateEntryError:
			pass

	if args.submit_budget:
		budget.submit()

	return budget
