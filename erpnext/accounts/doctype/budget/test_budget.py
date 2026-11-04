# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import now_datetime, nowdate

from erpnext.accounts.doctype.budget.budget import (
	BudgetError,
	get_accumulated_monthly_budget,
	get_actual_expense,
)
from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.utils import get_fiscal_year
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.stock.doctype.item.test_item import make_item

test_dependencies = ["Monthly Distribution"]


class TestBudget(unittest.TestCase):
	def test_budget_includes_other_items(self):
		self.addCleanup(frappe.db.rollback)
		for doctype in ("Purchase Order", "Material Request"):
			with self.subTest(doctype=doctype):
				cost_center = f"_Test Budget Commitments {doctype}"
				create_cost_center(cost_center_name=cost_center)
				budget = make_budget(
					budget_against="Cost Center",
					cost_center=f"{cost_center} - _TC",
					budget_amount=1000,
					applicable_on_purchase_order=1,
					applicable_on_material_request=1,
					action_if_annual_budget_exceeded_on_po="Stop",
					action_if_annual_budget_exceeded_on_mr="Stop",
					action_if_accumulated_monthly_budget_exceeded_on_po="Ignore",
					action_if_accumulated_monthly_budget_exceeded_on_mr="Ignore",
					submit_budget=True,
				)

				for item_code in ("_Test Budget Consumable A", "_Test Budget Consumable B"):
					make_item(item_code, {"is_stock_item": 0, "stock_uom": "Nos"})
					doc = frappe.new_doc(doctype)
					doc.company = "_Test Company"
					doc.transaction_date = doc.schedule_date = nowdate()
					if doctype == "Purchase Order":
						doc.supplier = "_Test Supplier"
						doc.currency = "INR"
						doc.conversion_rate = 1
					else:
						doc.material_request_type = "Purchase"

					doc.append(
						"items",
						{
							"item_code": item_code,
							"qty": 1,
							"uom": "Nos",
							"conversion_factor": 1,
							"rate": 600,
							"schedule_date": nowdate(),
							"warehouse": "_Test Warehouse - _TC",
							"expense_account": "_Test Account Cost for Goods Sold - _TC",
							"cost_center": budget.cost_center,
						},
					)
					doc.set_missing_values()
					doc.insert()
					if item_code == "_Test Budget Consumable A":
						doc.submit()
					else:
						# Each item costs less than the budget, but their combined commitment exceeds it.
						frappe.db.savepoint("budget_limit")
						with self.assertRaises(BudgetError):
							doc.submit()
						frappe.db.rollback(save_point="budget_limit")

						# The same second item is allowed when the combined commitment equals the budget.
						doc.reload()
						doc.items[0].rate = 400
						doc.save()
						doc.submit()
						self.assertEqual(doc.docstatus, 1)

	def test_budget_ignores_over_ordered_requests(self):
		self.addCleanup(frappe.db.rollback)
		cost_center = make_budget_for_new_cost_center("_Test Budget Over Ordered Row")
		mr = make_purchase_commitment(
			"Material Request", "_Test Budget Over Ordered Item", cost_center, 100, 10
		)
		frappe.db.set_value("Material Request Item", mr.items[0].name, "ordered_qty", 11)
		frappe.db.savepoint("budget_limit")
		with self.assertRaises(BudgetError):
			make_purchase_commitment("Material Request", "_Test Budget Requested Item", cost_center, 1050)
		frappe.db.rollback(save_point="budget_limit")

	def test_budget_counts_requested_amount_in_purchase_uom(self):
		self.addCleanup(frappe.db.rollback)
		make_item(
			"_Test Budget Boxed Item",
			{"is_stock_item": 0, "stock_uom": "Nos", "uoms": [{"uom": "Box", "conversion_factor": 10}]},
		)
		cost_center = make_budget_for_new_cost_center("_Test Budget Purchase UOM")

		# one box of 10 at 80 commits 80, so 300 more stays within the budget
		make_purchase_commitment(
			"Material Request",
			"_Test Budget Boxed Item",
			cost_center,
			80,
			uom="Box",
			conversion_factor=10,
		)
		make_purchase_commitment("Material Request", "_Test Budget Loose Item", cost_center, 300)

	def test_budget_allows_request_equal_to_budget_with_fractional_uom(self):
		self.addCleanup(frappe.db.rollback)
		frappe.db.set_value("UOM", "Box", "must_be_whole_number", 0)
		make_item(
			"_Test Budget Pound Item",
			{
				"is_stock_item": 0,
				"stock_uom": "Kg",
				"uoms": [{"uom": "Box", "conversion_factor": 0.45359237}],
			},
		)
		cost_center = make_budget_for_new_cost_center("_Test Budget Fractional UOM")

		# 1.25 x 800 is exactly the budget once the stored stock qty is converted back
		make_purchase_commitment(
			"Material Request",
			"_Test Budget Pound Item",
			cost_center,
			800,
			qty=1.25,
			uom="Box",
			conversion_factor=0.45359237,
		)

	def test_monthly_budget_crossed_ignore(self):
		set_total_expense_zero(nowdate(), "cost_center")

		budget = make_budget(budget_against="Cost Center")

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

		budget = make_budget(budget_against="Cost Center")

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			40000,
			"_Test Cost Center - _TC",
			posting_date=nowdate(),
		)

		self.assertRaises(BudgetError, jv.submit)

		budget.load_from_db()
		budget.cancel()

	def test_exception_approver_role(self):
		set_total_expense_zero(nowdate(), "cost_center")

		budget = make_budget(budget_against="Cost Center")

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			40000,
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
		)

		fiscal_year = get_fiscal_year(nowdate())[0]
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")
		frappe.db.set_value("Budget", budget.name, "fiscal_year", fiscal_year)

		accumulated_limit = get_accumulated_monthly_budget(
			budget.monthly_distribution, nowdate(), budget.fiscal_year, budget.accounts[0].budget_amount
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

	def test_monthly_budget_crossed_for_po(self):
		budget = make_budget(
			applicable_on_purchase_order=1,
			action_if_accumulated_monthly_budget_exceeded_on_po="Stop",
			budget_against="Cost Center",
		)

		fiscal_year = get_fiscal_year(nowdate())[0]
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")
		frappe.db.set_value("Budget", budget.name, "fiscal_year", fiscal_year)

		po = create_purchase_order(transaction_date=nowdate(), do_not_submit=True)

		po.set_missing_values()

		self.assertRaises(BudgetError, po.submit)

		budget.load_from_db()
		budget.cancel()
		po.cancel()

	def test_monthly_budget_crossed_for_po_in_foreign_currency(self):
		budget = make_budget(
			applicable_on_purchase_order=1,
			action_if_accumulated_monthly_budget_exceeded_on_po="Stop",
			budget_against="Cost Center",
		)

		fiscal_year = get_fiscal_year(nowdate())[0]
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")
		frappe.db.set_value("Budget", budget.name, "fiscal_year", fiscal_year)

		accumulated_limit = get_accumulated_monthly_budget(
			budget.monthly_distribution, nowdate(), budget.fiscal_year, budget.accounts[0].budget_amount
		)
		po = create_purchase_order(
			currency="USD",
			transaction_date=nowdate(),
			qty=1,
			rate=accumulated_limit / 2,
			do_not_submit=True,
		)
		po.set_missing_values()
		po.conversion_rate = 80

		self.assertRaises(BudgetError, po.submit)

		budget.load_from_db()
		budget.cancel()
		po.cancel()

	def test_monthly_budget_crossed_stop2(self):
		set_total_expense_zero(nowdate(), "project")

		budget = make_budget(budget_against="Project")

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		project = frappe.get_value("Project", {"project_name": "_Test Project"})

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			40000,
			"_Test Cost Center - _TC",
			project=project,
			posting_date=nowdate(),
		)

		self.assertRaises(BudgetError, jv.submit)

		budget.load_from_db()
		budget.cancel()

	def test_yearly_budget_crossed_stop1(self):
		set_total_expense_zero(nowdate(), "cost_center")

		budget = make_budget(budget_against="Cost Center")

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

		budget = make_budget(budget_against="Project")

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

		budget = make_budget(budget_against="Cost Center")
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

		budget = make_budget(budget_against="Project")
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

		budget = make_budget(budget_against="Cost Center", cost_center="_Test Company - _TC")
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			40000,
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

		budget = make_budget(budget_against="Cost Center", cost_center=cost_center)
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			40000,
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

		make_budget(budget_against="Cost Center", cost_center="Main Budget Cost Center 1 - _TC")

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			400000,
			"Main Budget Cost Center 1 - _TC",
			posting_date=nowdate(),
		)

		self.assertRaises(BudgetError, jv.submit)

	def test_budget_against_balance_sheet_account(self):
		budget = frappe.new_doc("Budget")
		budget.budget_against = "Cost Center"
		budget.cost_center = "_Test Cost Center - _TC"
		budget.company = "_Test Company"
		budget.fiscal_year = get_fiscal_year(nowdate())[0]
		budget.append("accounts", {"account": "_Test Bank - _TC", "budget_amount": 200000})

		self.assertRaisesRegex(frappe.ValidationError, "_Test Bank - _TC", budget.insert)


def set_total_expense_zero(posting_date, budget_against_field=None, budget_against_CC=None):
	if budget_against_field == "project":
		budget_against = frappe.db.get_value("Project", {"project_name": "_Test Project"})
	else:
		budget_against = budget_against_CC or "_Test Cost Center - _TC"

	fiscal_year = get_fiscal_year(nowdate())[0]

	args = frappe._dict(
		{
			"account": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"monthly_end_date": posting_date,
			"company": "_Test Company",
			"fiscal_year": fiscal_year,
			"budget_against_field": budget_against_field,
		}
	)

	if not args.get(budget_against_field):
		args[budget_against_field] = budget_against

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


def make_budget_for_new_cost_center(cost_center_name):
	create_cost_center(cost_center_name=cost_center_name)
	return make_budget(
		budget_against="Cost Center",
		cost_center=f"{cost_center_name} - _TC",
		budget_amount=1000,
		applicable_on_purchase_order=1,
		applicable_on_material_request=1,
		action_if_annual_budget_exceeded_on_po="Stop",
		action_if_annual_budget_exceeded_on_mr="Stop",
		action_if_accumulated_monthly_budget_exceeded_on_po="Ignore",
		action_if_accumulated_monthly_budget_exceeded_on_mr="Ignore",
		submit_budget=True,
	).cost_center


def make_purchase_commitment(doctype, item_code, cost_center, rate, qty=1, uom="Nos", conversion_factor=1):
	make_item(item_code, {"is_stock_item": 0, "stock_uom": "Nos"})
	doc = frappe.new_doc(doctype)
	doc.company = "_Test Company"
	doc.transaction_date = doc.schedule_date = nowdate()
	if doctype == "Purchase Order":
		doc.supplier = "_Test Supplier"
		doc.currency = "INR"
		doc.conversion_rate = 1
	else:
		doc.material_request_type = "Purchase"

	doc.append(
		"items",
		{
			"item_code": item_code,
			"qty": qty,
			"uom": uom,
			"conversion_factor": conversion_factor,
			"rate": rate,
			"schedule_date": nowdate(),
			"warehouse": "_Test Warehouse - _TC",
			"expense_account": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": cost_center,
		},
	)
	doc.set_missing_values()
	doc.insert()
	doc.submit()
	return doc


def make_budget(**args):
	args = frappe._dict(args)

	budget_against = args.budget_against
	cost_center = args.cost_center

	fiscal_year = get_fiscal_year(nowdate())[0]

	if budget_against == "Project":
		project_name = "{}%".format("_Test Project/" + fiscal_year)
		budget_list = frappe.get_all("Budget", fields=["name"], filters={"name": ("like", project_name)})
	else:
		cost_center_name = "{}%".format(cost_center or "_Test Cost Center - _TC/" + fiscal_year)
		budget_list = frappe.get_all("Budget", fields=["name"], filters={"name": ("like", cost_center_name)})
	for d in budget_list:
		frappe.db.sql("delete from `tabBudget` where name = %(name)s", d)
		frappe.db.sql("delete from `tabBudget Account` where parent = %(name)s", d)

	budget = frappe.new_doc("Budget")

	if budget_against == "Project":
		budget.project = frappe.get_value("Project", {"project_name": "_Test Project"})
	else:
		budget.cost_center = cost_center or "_Test Cost Center - _TC"

	monthly_distribution = frappe.get_doc("Monthly Distribution", "_Test Distribution")
	monthly_distribution.fiscal_year = fiscal_year

	budget.fiscal_year = fiscal_year
	budget.monthly_distribution = "_Test Distribution"
	budget.company = "_Test Company"
	budget.applicable_on_booking_actual_expenses = 1
	budget.action_if_annual_budget_exceeded = "Stop"
	budget.action_if_accumulated_monthly_budget_exceeded = "Ignore"
	budget.budget_against = budget_against
	budget.append(
		"accounts",
		{"account": "_Test Account Cost for Goods Sold - _TC", "budget_amount": args.budget_amount or 200000},
	)

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

	budget.insert()
	budget.submit()

	return budget
