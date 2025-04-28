# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


<<<<<<< HEAD
from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import add_months, flt, fmt_money, get_last_day, getdate, month_diff
from frappe.utils.data import get_first_day, nowdate
=======
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, flt, fmt_money, get_last_day, getdate
>>>>>>> 7c4cf3e834 (Favicon.svg)

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.utils import get_fiscal_year


class BudgetError(frappe.ValidationError):
	pass


class DuplicateBudgetError(frappe.ValidationError):
	pass


class Budget(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

<<<<<<< HEAD
		from erpnext.accounts.doctype.budget_distribution.budget_distribution import BudgetDistribution

		account: DF.Link
		action_if_accumulated_monthly_budget_exceeded: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_accumulated_monthly_budget_exceeded_on_mr: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_accumulated_monthly_budget_exceeded_on_po: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_accumulated_monthly_exceeded_on_cumulative_expense: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded_on_mr: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded_on_po: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_exceeded_on_cumulative_expense: DF.Literal["", "Stop", "Warn", "Ignore"]
		amended_from: DF.Link | None
		applicable_on_booking_actual_expenses: DF.Check
		applicable_on_cumulative_expense: DF.Check
		applicable_on_material_request: DF.Check
		applicable_on_purchase_order: DF.Check
		budget_against: DF.Literal["", "Cost Center", "Project"]
		budget_amount: DF.Currency
		budget_distribution: DF.Table[BudgetDistribution]
		budget_end_date: DF.Date | None
		budget_start_date: DF.Date | None
		company: DF.Link
		cost_center: DF.Link | None
		distribute_equally: DF.Check
		distribution_frequency: DF.Literal["Monthly", "Quarterly", "Half-Yearly", "Yearly"]
		from_fiscal_year: DF.Link
		naming_series: DF.Literal["BUDGET-.########"]
		project: DF.Link | None
		revision_of: DF.Data | None
		to_fiscal_year: DF.Link
=======
		from erpnext.accounts.doctype.budget_account.budget_account import BudgetAccount

		accounts: DF.Table[BudgetAccount]
		action_if_accumulated_monthly_budget_exceeded: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_accumulated_monthly_budget_exceeded_on_mr: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_accumulated_monthly_budget_exceeded_on_po: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded_on_mr: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded_on_po: DF.Literal["", "Stop", "Warn", "Ignore"]
		amended_from: DF.Link | None
		applicable_on_booking_actual_expenses: DF.Check
		applicable_on_material_request: DF.Check
		applicable_on_purchase_order: DF.Check
		budget_against: DF.Literal["", "Cost Center", "Project"]
		company: DF.Link
		cost_center: DF.Link | None
		fiscal_year: DF.Link
		monthly_distribution: DF.Link | None
		naming_series: DF.Data | None
		project: DF.Link | None
>>>>>>> 7c4cf3e834 (Favicon.svg)
	# end: auto-generated types

	def validate(self):
		if not self.get(frappe.scrub(self.budget_against)):
			frappe.throw(_("{0} is mandatory").format(self.budget_against))
<<<<<<< HEAD
		self.validate_budget_amount()
		self.validate_fiscal_year()
		self.set_fiscal_year_dates()
		self.validate_duplicate()
		self.validate_account()
		self.set_null_value()
		self.validate_applicable_for()
		self.validate_existing_expenses()

	def validate_budget_amount(self):
		if self.budget_amount <= 0:
			frappe.throw(_("Budget Amount can not be {0}.").format(self.budget_amount))

	def validate_fiscal_year(self):
		if self.from_fiscal_year:
			self.validate_fiscal_year_company(self.from_fiscal_year, self.company)
		if self.to_fiscal_year:
			self.validate_fiscal_year_company(self.to_fiscal_year, self.company)

	def validate_fiscal_year_company(self, fiscal_year, company):
		linked_companies = frappe.get_all(
			"Fiscal Year Company", filters={"parent": fiscal_year}, pluck="company"
		)
		if linked_companies and company not in linked_companies:
			frappe.throw(_("Fiscal Year {0} is not available for Company {1}.").format(fiscal_year, company))

	def set_fiscal_year_dates(self):
		if self.from_fiscal_year:
			self.budget_start_date = frappe.get_cached_value(
				"Fiscal Year", self.from_fiscal_year, "year_start_date"
			)
		if self.to_fiscal_year:
			self.budget_end_date = frappe.get_cached_value(
				"Fiscal Year", self.to_fiscal_year, "year_end_date"
			)

		if self.budget_start_date > self.budget_end_date:
			frappe.throw(_("From Fiscal Year cannot be greater than To Fiscal Year"))
=======
		self.validate_duplicate()
		self.validate_accounts()
		self.set_null_value()
		self.validate_applicable_for()
>>>>>>> 7c4cf3e834 (Favicon.svg)

	def validate_duplicate(self):
		budget_against_field = frappe.scrub(self.budget_against)
		budget_against = self.get(budget_against_field)
<<<<<<< HEAD
		account = self.account

		if not account:
			return

		existing_budget = frappe.db.sql(
			f"""
			SELECT name, account
			FROM `tabBudget`
			WHERE
				docstatus < 2
				AND company = %s
				AND {budget_against_field} = %s
				AND account = %s
				AND name != %s
				AND (
					(SELECT year_start_date FROM `tabFiscal Year` WHERE name = from_fiscal_year) <= %s
					AND (SELECT year_end_date FROM `tabFiscal Year` WHERE name = to_fiscal_year) >= %s
				)
			""",
			(self.company, budget_against, account, self.name, self.budget_end_date, self.budget_start_date),
			as_dict=True,
		)

		if existing_budget:
			d = existing_budget[0]
			frappe.throw(
				_(
					"Another Budget record '{0}' already exists against {1} '{2}' and account '{3}' with overlapping fiscal years."
				).format(d.name, self.budget_against, budget_against, d.account),
				DuplicateBudgetError,
			)

	def validate_account(self):
		if not self.account:
			frappe.throw(_("Account is mandatory"))

		account_details = frappe.get_cached_value(
			"Account", self.account, ["is_group", "company", "report_type"], as_dict=1
		)

		if account_details.is_group:
			frappe.throw(_("Budget cannot be assigned against Group Account {0}").format(self.account))
		elif account_details.company != self.company:
			frappe.throw(_("Account {0} does not belong to company {1}").format(self.account, self.company))
		elif account_details.report_type != "Profit and Loss":
			frappe.throw(
				_("Budget cannot be assigned against {0}, as it's not an Income or Expense account").format(
					self.account
				)
			)
=======

		accounts = [d.account for d in self.accounts] or []
		existing_budget = frappe.db.sql(
			"""
			select
				b.name, ba.account from `tabBudget` b, `tabBudget Account` ba
			where
				ba.parent = b.name and b.docstatus < 2 and b.company = {} and {}={} and
				b.fiscal_year={} and b.name != {} and ba.account in ({}) """.format(
				"%s", budget_against_field, "%s", "%s", "%s", ",".join(["%s"] * len(accounts))
			),
			(self.company, budget_against, self.fiscal_year, self.name, *tuple(accounts)),
			as_dict=1,
		)

		for d in existing_budget:
			frappe.throw(
				_(
					"Another Budget record '{0}' already exists against {1} '{2}' and account '{3}' for fiscal year {4}"
				).format(d.name, self.budget_against, budget_against, d.account, self.fiscal_year),
				DuplicateBudgetError,
			)

	def validate_accounts(self):
		account_list = []
		for d in self.get("accounts"):
			if d.account:
				account_details = frappe.get_cached_value(
					"Account", d.account, ["is_group", "company", "report_type"], as_dict=1
				)

				if account_details.is_group:
					frappe.throw(_("Budget cannot be assigned against Group Account {0}").format(d.account))
				elif account_details.company != self.company:
					frappe.throw(
						_("Account {0} does not belongs to company {1}").format(d.account, self.company)
					)
				elif account_details.report_type != "Profit and Loss":
					frappe.throw(
						_(
							"Budget cannot be assigned against {0}, as it's not an Income or Expense account"
						).format(d.account)
					)

				if d.account in account_list:
					frappe.throw(_("Account {0} has been entered multiple times").format(d.account))
				else:
					account_list.append(d.account)
>>>>>>> 7c4cf3e834 (Favicon.svg)

	def set_null_value(self):
		if self.budget_against == "Cost Center":
			self.project = None
		else:
			self.cost_center = None

	def validate_applicable_for(self):
		if self.applicable_on_material_request and not (
			self.applicable_on_purchase_order and self.applicable_on_booking_actual_expenses
		):
			frappe.throw(
				_("Please enable Applicable on Purchase Order and Applicable on Booking Actual Expenses")
			)

		elif self.applicable_on_purchase_order and not (self.applicable_on_booking_actual_expenses):
			frappe.throw(_("Please enable Applicable on Booking Actual Expenses"))

		elif not (
			self.applicable_on_material_request
			or self.applicable_on_purchase_order
			or self.applicable_on_booking_actual_expenses
		):
			self.applicable_on_booking_actual_expenses = 1

<<<<<<< HEAD
	def validate_existing_expenses(self):
		if self.is_new() and self.revision_of:
			return

		params = frappe._dict(
			{
				"company": self.company,
				"account": self.account,
				"budget_start_date": self.budget_start_date,
				"budget_end_date": self.budget_end_date,
				"budget_against_field": frappe.scrub(self.budget_against),
				"budget_against_doctype": frappe.unscrub(self.budget_against),
			}
		)

		params[params.budget_against_field] = self.get(params.budget_against_field)

		if frappe.get_cached_value("DocType", params.budget_against_doctype, "is_tree"):
			params.is_tree = True
		else:
			params.is_tree = False

		actual_spent = get_actual_expense(params)

		if actual_spent > self.budget_amount:
			frappe.throw(
				_(
					"Spending for Account {0} ({1}) between {2} and {3} "
					"has already exceeded the new allocated budget. "
					"Spent: {4}, Budget: {5}"
				).format(
					frappe.bold(self.account),
					frappe.bold(self.company),
					frappe.bold(self.budget_start_date),
					frappe.bold(self.budget_end_date),
					frappe.bold(frappe.utils.fmt_money(actual_spent)),
					frappe.bold(frappe.utils.fmt_money(self.budget_amount)),
				),
				title=_("Budget Limit Exceeded"),
			)

	def before_save(self):
		self.allocate_budget()

	def on_update(self):
		self.validate_distribution_totals()

	def allocate_budget(self):
		if self.revision_of:
			return

		if not self.should_regenerate_budget_distribution():
			return

		self.set("budget_distribution", [])

		periods = self.get_budget_periods()
		total_periods = len(periods)
		row_percent = 100 / total_periods if total_periods else 0

		for start_date, end_date in periods:
			row = self.append("budget_distribution", {})
			row.start_date = start_date
			row.end_date = end_date
			self.add_allocated_amount(row, row_percent)

	def should_regenerate_budget_distribution(self):
		"""Check whether budget distribution should be recalculated."""
		old_doc = self.get_doc_before_save() if not self.is_new() else None
		if not old_doc or not self.budget_distribution:
			return True

		if old_doc:
			changed_fields = [
				"from_fiscal_year",
				"to_fiscal_year",
				"budget_amount",
				"distribution_frequency",
				"distribute_equally",
			]
			for field in changed_fields:
				if old_doc.get(field) != self.get(field):
					return True

		return bool(self.distribute_equally)

	def get_budget_periods(self):
		"""Return list of (start_date, end_date) tuples based on frequency."""
		frequency = self.distribution_frequency
		periods = []

		start_date = getdate(self.budget_start_date)
		end_date = getdate(self.budget_end_date)

		while start_date <= end_date:
			period_start = get_first_day(start_date)
			period_end = self.get_period_end(period_start, frequency)
			period_end = min(period_end, end_date)

			periods.append((period_start, period_end))
			start_date = add_months(period_start, self.get_month_increment(frequency))

		return periods

	def get_period_end(self, start_date, frequency):
		"""Return the correct end date for a given frequency."""
		if frequency == "Monthly":
			return get_last_day(start_date)
		elif frequency == "Quarterly":
			return get_last_day(add_months(start_date, 2))
		elif frequency == "Half-Yearly":
			return get_last_day(add_months(start_date, 5))
		else:  # Yearly
			return get_last_day(add_months(start_date, 11))

	def get_month_increment(self, frequency):
		"""Return how many months to move forward for the next period."""
		return {
			"Monthly": 1,
			"Quarterly": 3,
			"Half-Yearly": 6,
			"Yearly": 12,
		}.get(frequency, 1)

	def add_allocated_amount(self, row, row_percent):
		if not self.distribute_equally:
			row.amount = 0
			row.percent = 0
		else:
			row.amount = flt(self.budget_amount * row_percent / 100, 3)
			row.percent = flt(row_percent, 3)

	def validate_distribution_totals(self):
		if self.should_regenerate_budget_distribution():
			return

		total_amount = sum(d.amount for d in self.budget_distribution)
		total_percent = sum(d.percent for d in self.budget_distribution)

		if flt(abs(total_amount - self.budget_amount), 2) > 0.10:
			frappe.throw(
				_("Total distributed amount {0} must be equal to Budget Amount {1}").format(
					flt(total_amount, 2), self.budget_amount
				)
			)

		if flt(abs(total_percent - 100), 2) > 0.10:
			frappe.throw(
				_("Total distribution percent must equal 100 (currently {0})").format(round(total_percent, 2))
			)


def validate_expense_against_budget(params, expense_amount=0):
	params = frappe._dict(params)
	if not frappe.db.count("Budget", cache=True):
		return

	if not params.fiscal_year:
		params.fiscal_year = get_fiscal_year(params.get("posting_date"), company=params.get("company"))[0]

	posting_date = getdate(params.get("posting_date"))
	posting_fiscal_year = get_fiscal_year(posting_date, company=params.get("company"))[0]
	year_start_date, year_end_date = get_fiscal_year_date_range(posting_fiscal_year, posting_fiscal_year)

	budget_exists = frappe.db.sql(
		"""
		select name
		from `tabBudget`
		where company = %s
		and docstatus = 1
		and (SELECT year_start_date FROM `tabFiscal Year` WHERE name = from_fiscal_year) <= %s
		and (SELECT year_end_date FROM `tabFiscal Year` WHERE name = to_fiscal_year) >= %s
		limit 1
		""",
		(params.company, year_end_date, year_start_date),
	)

	if not budget_exists:
		return

	if params.get("company"):
		frappe.flags.exception_approver_role = frappe.get_cached_value(
			"Company", params.get("company"), "exception_budget_approver_role"
		)

	if not params.account:
		params.account = params.get("expense_account")

	if not params.get("expense_account") and params.get("account"):
		params.expense_account = params.account

	if not (params.get("account") and params.get("cost_center")) and params.item_code:
		params.cost_center, params.account = get_item_details(params)

	if not params.account:
=======
	def before_naming(self):
		self.naming_series = f"{{{frappe.scrub(self.budget_against)}}}./.{self.fiscal_year}/.###"


def validate_expense_against_budget(args, expense_amount=0):
	args = frappe._dict(args)
	if not frappe.get_all("Budget", limit=1):
		return

	if args.get("company") and not args.fiscal_year:
		args.fiscal_year = get_fiscal_year(args.get("posting_date"), company=args.get("company"))[0]
		frappe.flags.exception_approver_role = frappe.get_cached_value(
			"Company", args.get("company"), "exception_budget_approver_role"
		)

	if not frappe.get_cached_value("Budget", {"fiscal_year": args.fiscal_year, "company": args.company}):  # nosec
		return

	if not args.account:
		args.account = args.get("expense_account")

	if not (args.get("account") and args.get("cost_center")) and args.item_code:
		args.cost_center, args.account = get_item_details(args)

	if not args.account:
>>>>>>> 7c4cf3e834 (Favicon.svg)
		return

	default_dimensions = [
		{
			"fieldname": "project",
			"document_type": "Project",
		},
		{
			"fieldname": "cost_center",
			"document_type": "Cost Center",
		},
	]

	for dimension in default_dimensions + get_accounting_dimensions(as_list=False):
		budget_against = dimension.get("fieldname")

		if (
<<<<<<< HEAD
			params.get(budget_against)
			and params.account
			and (frappe.get_cached_value("Account", params.account, "root_type") == "Expense")
=======
			args.get(budget_against)
			and args.account
			and (frappe.get_cached_value("Account", args.account, "root_type") == "Expense")
>>>>>>> 7c4cf3e834 (Favicon.svg)
		):
			doctype = dimension.get("document_type")

			if frappe.get_cached_value("DocType", doctype, "is_tree"):
<<<<<<< HEAD
				lft, rgt = frappe.get_cached_value(doctype, params.get(budget_against), ["lft", "rgt"])
				condition = f"""and exists(select name from `tab{doctype}`
					where lft<={lft} and rgt>={rgt} and name=b.{budget_against})"""  # nosec
				params.is_tree = True
			else:
				condition = f"and b.{budget_against}={frappe.db.escape(params.get(budget_against))}"
				params.is_tree = False

			params.budget_against_field = budget_against
			params.budget_against_doctype = doctype

			budget_records = frappe.db.sql(
				f"""
				SELECT
					b.name,
					b.{budget_against} AS budget_against,
					b.budget_amount,
					b.from_fiscal_year,
					b.to_fiscal_year,
					b.budget_start_date,
					b.budget_end_date,
					IFNULL(b.applicable_on_material_request, 0) AS for_material_request,
					IFNULL(b.applicable_on_purchase_order, 0) AS for_purchase_order,
					IFNULL(b.applicable_on_booking_actual_expenses, 0) AS for_actual_expenses,
					b.action_if_annual_budget_exceeded,
					b.action_if_accumulated_monthly_budget_exceeded,
					b.action_if_annual_budget_exceeded_on_mr,
					b.action_if_accumulated_monthly_budget_exceeded_on_mr,
					b.action_if_annual_budget_exceeded_on_po,
					b.action_if_accumulated_monthly_budget_exceeded_on_po
				FROM
					`tabBudget` b
				WHERE
					b.company = %s
					AND b.docstatus = 1
					AND %s BETWEEN b.budget_start_date AND b.budget_end_date
					AND b.account = %s
					{condition}
				""",
				(params.company, params.posting_date, params.account),
=======
				lft, rgt = frappe.get_cached_value(doctype, args.get(budget_against), ["lft", "rgt"])
				condition = f"""and exists(select name from `tab{doctype}`
					where lft<={lft} and rgt>={rgt} and name=b.{budget_against})"""  # nosec
				args.is_tree = True
			else:
				condition = f"and b.{budget_against}={frappe.db.escape(args.get(budget_against))}"
				args.is_tree = False

			args.budget_against_field = budget_against
			args.budget_against_doctype = doctype

			budget_records = frappe.db.sql(
				f"""
				select
					b.{budget_against} as budget_against, ba.budget_amount, b.monthly_distribution,
					ifnull(b.applicable_on_material_request, 0) as for_material_request,
					ifnull(applicable_on_purchase_order, 0) as for_purchase_order,
					ifnull(applicable_on_booking_actual_expenses,0) as for_actual_expenses,
					b.action_if_annual_budget_exceeded, b.action_if_accumulated_monthly_budget_exceeded,
					b.action_if_annual_budget_exceeded_on_mr, b.action_if_accumulated_monthly_budget_exceeded_on_mr,
					b.action_if_annual_budget_exceeded_on_po, b.action_if_accumulated_monthly_budget_exceeded_on_po
				from
					`tabBudget` b, `tabBudget Account` ba
				where
					b.name=ba.parent and b.fiscal_year=%s
					and ba.account=%s and b.docstatus=1
					{condition}
			""",
				(args.fiscal_year, args.account),
>>>>>>> 7c4cf3e834 (Favicon.svg)
				as_dict=True,
			)  # nosec

			if budget_records:
<<<<<<< HEAD
				validate_budget_records(params, budget_records, expense_amount)


def validate_budget_records(params, budget_records, expense_amount):
	for budget in budget_records:
		if flt(budget.budget_amount):
			yearly_action, monthly_action = get_actions(params, budget)
			params["for_material_request"] = budget.for_material_request
			params["for_purchase_order"] = budget.for_purchase_order
			params["from_fiscal_year"], params["to_fiscal_year"] = (
				budget.from_fiscal_year,
				budget.to_fiscal_year,
			)
			params["budget_start_date"], params["budget_end_date"] = (
				budget.budget_start_date,
				budget.budget_end_date,
			)

			if yearly_action in ("Stop", "Warn"):
				compare_expense_with_budget(
					params,
=======
				validate_budget_records(args, budget_records, expense_amount)


def validate_budget_records(args, budget_records, expense_amount):
	for budget in budget_records:
		if flt(budget.budget_amount):
			yearly_action, monthly_action = get_actions(args, budget)
			args["for_material_request"] = budget.for_material_request
			args["for_purchase_order"] = budget.for_purchase_order

			if yearly_action in ("Stop", "Warn"):
				compare_expense_with_budget(
					args,
>>>>>>> 7c4cf3e834 (Favicon.svg)
					flt(budget.budget_amount),
					_("Annual"),
					yearly_action,
					budget.budget_against,
					expense_amount,
				)

			if monthly_action in ["Stop", "Warn"]:
<<<<<<< HEAD
				budget_amount = get_accumulated_monthly_budget(budget.name, params.posting_date)

				params["month_end_date"] = get_last_day(params.posting_date)

				compare_expense_with_budget(
					params,
=======
				budget_amount = get_accumulated_monthly_budget(
					budget.monthly_distribution, args.posting_date, args.fiscal_year, budget.budget_amount
				)

				args["month_end_date"] = get_last_day(args.posting_date)

				compare_expense_with_budget(
					args,
>>>>>>> 7c4cf3e834 (Favicon.svg)
					budget_amount,
					_("Accumulated Monthly"),
					monthly_action,
					budget.budget_against,
					expense_amount,
				)


<<<<<<< HEAD
def compare_expense_with_budget(params, budget_amount, action_for, action, budget_against, amount=0):
	params.actual_expense, params.requested_amount, params.ordered_amount = get_actual_expense(params), 0, 0
	if not amount:
		params.requested_amount, params.ordered_amount = (
			get_requested_amount(params),
			get_ordered_amount(params),
		)

		if params.get("doctype") == "Material Request" and params.for_material_request:
			amount = params.requested_amount + params.ordered_amount

		elif params.get("doctype") == "Purchase Order" and params.for_purchase_order:
			amount = params.ordered_amount

	total_expense = params.actual_expense + amount

	if total_expense > budget_amount:
		if params.actual_expense > budget_amount:
			diff = params.actual_expense - budget_amount
			_msg = _("{0} Budget for Account {1} against {2} {3} is {4}. It is already exceeded by {5}.")
		else:
			diff = total_expense - budget_amount
			_msg = _("{0} Budget for Account {1} against {2} {3} is {4}. It will be exceeded by {5}.")

		currency = frappe.get_cached_value("Company", params.company, "default_currency")
		msg = _msg.format(
			_(action_for),
			frappe.bold(params.account),
			frappe.unscrub(params.budget_against_field),
			frappe.bold(budget_against),
			frappe.bold(fmt_money(budget_amount, currency=currency)),
			frappe.bold(fmt_money(diff, currency=currency)),
		)

		msg += get_expense_breakup(params, currency, budget_against)
=======
def compare_expense_with_budget(args, budget_amount, action_for, action, budget_against, amount=0):
	args.actual_expense, args.requested_amount, args.ordered_amount = get_actual_expense(args), 0, 0
	if not amount:
		args.requested_amount, args.ordered_amount = get_requested_amount(args), get_ordered_amount(args)

		if args.get("doctype") == "Material Request" and args.for_material_request:
			amount = args.requested_amount + args.ordered_amount

		elif args.get("doctype") == "Purchase Order" and args.for_purchase_order:
			amount = args.ordered_amount

	total_expense = args.actual_expense + amount

	if total_expense > budget_amount:
		if args.actual_expense > budget_amount:
			error_tense = _("is already")
			diff = args.actual_expense - budget_amount
		else:
			error_tense = _("will be")
			diff = total_expense - budget_amount

		currency = frappe.get_cached_value("Company", args.company, "default_currency")

		msg = _("{0} Budget for Account {1} against {2} {3} is {4}. It {5} exceed by {6}").format(
			_(action_for),
			frappe.bold(args.account),
			frappe.unscrub(args.budget_against_field),
			frappe.bold(budget_against),
			frappe.bold(fmt_money(budget_amount, currency=currency)),
			error_tense,
			frappe.bold(fmt_money(diff, currency=currency)),
		)

		msg += get_expense_breakup(args, currency, budget_against)
>>>>>>> 7c4cf3e834 (Favicon.svg)

		if frappe.flags.exception_approver_role and frappe.flags.exception_approver_role in frappe.get_roles(
			frappe.session.user
		):
			action = "Warn"

		if action == "Stop":
			frappe.throw(msg, BudgetError, title=_("Budget Exceeded"))
		else:
			frappe.msgprint(msg, indicator="orange", title=_("Budget Exceeded"))


<<<<<<< HEAD
def get_expense_breakup(params, currency, budget_against):
	msg = "<hr> {} - <ul>".format(_("Total Expenses booked through"))

	common_filters = frappe._dict(
		{
			params.budget_against_field: budget_against,
			"account": params.account,
			"company": params.company,
		}
	)

	from_date = frappe.get_cached_value("Fiscal Year", params.from_fiscal_year, "year_start_date")
	to_date = frappe.get_cached_value("Fiscal Year", params.to_fiscal_year, "year_end_date")
	gl_filters = common_filters.copy()
	gl_filters.update(
		{
			"from_date": from_date,
			"to_date": to_date,
			"is_cancelled": 0,
=======
def get_expense_breakup(args, currency, budget_against):
	msg = "<hr>Total Expenses booked through - <ul>"

	common_filters = frappe._dict(
		{
			args.budget_against_field: budget_against,
			"account": args.account,
			"company": args.company,
>>>>>>> 7c4cf3e834 (Favicon.svg)
		}
	)

	msg += (
		"<li>"
		+ frappe.utils.get_link_to_report(
			"General Ledger",
<<<<<<< HEAD
			label=_("Actual Expenses"),
			filters=gl_filters,
		)
		+ " - "
		+ frappe.bold(fmt_money(params.actual_expense, currency=currency))
		+ "</li>"
	)
	mr_filters = common_filters.copy()
	mr_filters.update(
		{
			"status": [["!=", "Stopped"]],
			"docstatus": 1,
			"material_request_type": "Purchase",
			"schedule_date": [["between", [from_date, to_date]]],
			"item_code": params.item_code,
			"per_ordered": [["<", 100]],
		}
	)
=======
			label="Actual Expenses",
			filters=common_filters.copy().update(
				{
					"from_date": frappe.get_cached_value("Fiscal Year", args.fiscal_year, "year_start_date"),
					"to_date": frappe.get_cached_value("Fiscal Year", args.fiscal_year, "year_end_date"),
					"is_cancelled": 0,
				}
			),
		)
		+ " - "
		+ frappe.bold(fmt_money(args.actual_expense, currency=currency))
		+ "</li>"
	)
>>>>>>> 7c4cf3e834 (Favicon.svg)

	msg += (
		"<li>"
		+ frappe.utils.get_link_to_report(
			"Material Request",
<<<<<<< HEAD
			label=_("Material Requests"),
			report_type="Report Builder",
			doctype="Material Request",
			filters=mr_filters,
		)
		+ " - "
		+ frappe.bold(fmt_money(params.requested_amount, currency=currency))
		+ "</li>"
	)

	po_filters = common_filters.copy()
	po_filters.update(
		{
			"status": [["!=", "Closed"]],
			"docstatus": 1,
			"transaction_date": [["between", [from_date, to_date]]],
			"item_code": params.item_code,
			"per_billed": [["<", 100]],
		}
	)

=======
			label="Material Requests",
			report_type="Report Builder",
			doctype="Material Request",
			filters=common_filters.copy().update(
				{
					"status": [["!=", "Stopped"]],
					"docstatus": 1,
					"material_request_type": "Purchase",
					"schedule_date": [["fiscal year", "2023-2024"]],
					"item_code": args.item_code,
					"per_ordered": [["<", 100]],
				}
			),
		)
		+ " - "
		+ frappe.bold(fmt_money(args.requested_amount, currency=currency))
		+ "</li>"
	)

>>>>>>> 7c4cf3e834 (Favicon.svg)
	msg += (
		"<li>"
		+ frappe.utils.get_link_to_report(
			"Purchase Order",
<<<<<<< HEAD
			label=_("Unbilled Orders"),
			report_type="Report Builder",
			doctype="Purchase Order",
			filters=po_filters,
		)
		+ " - "
		+ frappe.bold(fmt_money(params.ordered_amount, currency=currency))
=======
			label="Unbilled Orders",
			report_type="Report Builder",
			doctype="Purchase Order",
			filters=common_filters.copy().update(
				{
					"status": [["!=", "Closed"]],
					"docstatus": 1,
					"transaction_date": [["fiscal year", "2023-2024"]],
					"item_code": args.item_code,
					"per_billed": [["<", 100]],
				}
			),
		)
		+ " - "
		+ frappe.bold(fmt_money(args.ordered_amount, currency=currency))
>>>>>>> 7c4cf3e834 (Favicon.svg)
		+ "</li></ul>"
	)

	return msg


<<<<<<< HEAD
def get_actions(params, budget):
	yearly_action = budget.action_if_annual_budget_exceeded
	monthly_action = budget.action_if_accumulated_monthly_budget_exceeded

	if params.get("doctype") == "Material Request" and budget.for_material_request:
		yearly_action = budget.action_if_annual_budget_exceeded_on_mr
		monthly_action = budget.action_if_accumulated_monthly_budget_exceeded_on_mr

	elif params.get("doctype") == "Purchase Order" and budget.for_purchase_order:
=======
def get_actions(args, budget):
	yearly_action = budget.action_if_annual_budget_exceeded
	monthly_action = budget.action_if_accumulated_monthly_budget_exceeded

	if args.get("doctype") == "Material Request" and budget.for_material_request:
		yearly_action = budget.action_if_annual_budget_exceeded_on_mr
		monthly_action = budget.action_if_accumulated_monthly_budget_exceeded_on_mr

	elif args.get("doctype") == "Purchase Order" and budget.for_purchase_order:
>>>>>>> 7c4cf3e834 (Favicon.svg)
		yearly_action = budget.action_if_annual_budget_exceeded_on_po
		monthly_action = budget.action_if_accumulated_monthly_budget_exceeded_on_po

	return yearly_action, monthly_action


<<<<<<< HEAD
def get_requested_amount(params):
	item_code = params.get("item_code")
	condition = get_other_condition(params, "Material Request")
=======
def get_requested_amount(args):
	item_code = args.get("item_code")
	condition = get_other_condition(args, "Material Request")
>>>>>>> 7c4cf3e834 (Favicon.svg)

	data = frappe.db.sql(
		""" select ifnull((sum(child.stock_qty - child.ordered_qty) * rate), 0) as amount
		from `tabMaterial Request Item` child, `tabMaterial Request` parent where parent.name = child.parent and
		child.item_code = %s and parent.docstatus = 1 and child.stock_qty > child.ordered_qty and {} and
		parent.material_request_type = 'Purchase' and parent.status != 'Stopped'""".format(condition),
		item_code,
		as_list=1,
	)

	return data[0][0] if data else 0


<<<<<<< HEAD
def get_ordered_amount(params):
	item_code = params.get("item_code")
	condition = get_other_condition(params, "Purchase Order")
=======
def get_ordered_amount(args):
	item_code = args.get("item_code")
	condition = get_other_condition(args, "Purchase Order")
>>>>>>> 7c4cf3e834 (Favicon.svg)

	data = frappe.db.sql(
		f""" select ifnull(sum(child.amount - child.billed_amt), 0) as amount
		from `tabPurchase Order Item` child, `tabPurchase Order` parent where
		parent.name = child.parent and child.item_code = %s and parent.docstatus = 1 and child.amount > child.billed_amt
		and parent.status != 'Closed' and {condition}""",
		item_code,
		as_list=1,
	)

	return data[0][0] if data else 0


<<<<<<< HEAD
def get_other_condition(params, for_doc):
	condition = f"expense_account = '{params.expense_account}'"
	budget_against_field = params.get("budget_against_field")

	if budget_against_field and params.get(budget_against_field):
		condition += f" and child.{budget_against_field} = '{params.get(budget_against_field)}'"

	date_field = "schedule_date" if for_doc == "Material Request" else "transaction_date"

	start_date = frappe.get_cached_value("Fiscal Year", params.from_fiscal_year, "year_start_date")
	end_date = frappe.get_cached_value("Fiscal Year", params.to_fiscal_year, "year_end_date")

	condition += f" and parent.{date_field} between '{start_date}' and '{end_date}'"
=======
def get_other_condition(args, for_doc):
	condition = "expense_account = '%s'" % (args.expense_account)
	budget_against_field = args.get("budget_against_field")

	if budget_against_field and args.get(budget_against_field):
		condition += f" and child.{budget_against_field} = '{args.get(budget_against_field)}'"

	if args.get("fiscal_year"):
		date_field = "schedule_date" if for_doc == "Material Request" else "transaction_date"
		start_date, end_date = frappe.get_cached_value(
			"Fiscal Year", args.get("fiscal_year"), ["year_start_date", "year_end_date"]
		)

		condition += f""" and parent.{date_field}
			between '{start_date}' and '{end_date}' """
>>>>>>> 7c4cf3e834 (Favicon.svg)

	return condition


<<<<<<< HEAD
def get_actual_expense(params):
	if not params.budget_against_doctype:
		params.budget_against_doctype = frappe.unscrub(params.budget_against_field)

	budget_against_field = params.get("budget_against_field")
	condition1 = " and gle.posting_date <= %(month_end_date)s" if params.get("month_end_date") else ""

	date_condition = (
		f"and gle.posting_date between '{params.budget_start_date}' and '{params.budget_end_date}'"
	)

	if params.is_tree:
		lft_rgt = frappe.db.get_value(
			params.budget_against_doctype, params.get(budget_against_field), ["lft", "rgt"], as_dict=1
		)
		params.update(lft_rgt)

		condition2 = f"""
			and exists(
				select name from `tab{params.budget_against_doctype}`
				where lft >= %(lft)s and rgt <= %(rgt)s
				and name = gle.{budget_against_field}
			)
		"""
	else:
		condition2 = f"""
			and gle.{budget_against_field} = %({budget_against_field})s
		"""
=======
def get_actual_expense(args):
	if not args.budget_against_doctype:
		args.budget_against_doctype = frappe.unscrub(args.budget_against_field)

	budget_against_field = args.get("budget_against_field")
	condition1 = " and gle.posting_date <= %(month_end_date)s" if args.get("month_end_date") else ""

	if args.is_tree:
		lft_rgt = frappe.db.get_value(
			args.budget_against_doctype, args.get(budget_against_field), ["lft", "rgt"], as_dict=1
		)

		args.update(lft_rgt)

		condition2 = f"""and exists(select name from `tab{args.budget_against_doctype}`
			where lft>=%(lft)s and rgt<=%(rgt)s
			and name=gle.{budget_against_field})"""
	else:
		condition2 = f"""and exists(select name from `tab{args.budget_against_doctype}`
		where name=gle.{budget_against_field} and
		gle.{budget_against_field} = %({budget_against_field})s)"""
>>>>>>> 7c4cf3e834 (Favicon.svg)

	amount = flt(
		frappe.db.sql(
			f"""
<<<<<<< HEAD
				select sum(gle.debit) - sum(gle.credit)
				from `tabGL Entry` gle
				where
					is_cancelled = 0
					and gle.account = %(account)s
					{condition1}
					{date_condition}
					and gle.company = %(company)s
					and gle.docstatus = 1
					{condition2}
			""",
			params,
=======
		select sum(gle.debit) - sum(gle.credit)
		from `tabGL Entry` gle
		where
			is_cancelled = 0
			and gle.account=%(account)s
			{condition1}
			and gle.fiscal_year=%(fiscal_year)s
			and gle.company=%(company)s
			and gle.docstatus=1
			{condition2}
	""",
			(args),
>>>>>>> 7c4cf3e834 (Favicon.svg)
		)[0][0]
	)  # nosec

	return amount


<<<<<<< HEAD
def get_accumulated_monthly_budget(budget_name, posting_date):
	posting_date = getdate(posting_date)

	bd = frappe.qb.DocType("Budget Distribution")
	b = frappe.qb.DocType("Budget")

	result = (
		frappe.qb.from_(bd)
		.join(b)
		.on(bd.parent == b.name)
		.select(Sum(bd.amount).as_("accumulated_amount"))
		.where(b.name == budget_name)
		.where(bd.start_date <= posting_date)
		.run(as_dict=True)
	)

	return flt(result[0]["accumulated_amount"]) if result else 0.0


def get_item_details(params):
	cost_center, expense_account = None, None

	if not params.get("company"):
		return cost_center, expense_account

	if params.item_code:
		item_defaults = frappe.db.get_value(
			"Item Default",
			{"parent": params.item_code, "company": params.get("company")},
=======
def get_accumulated_monthly_budget(monthly_distribution, posting_date, fiscal_year, annual_budget):
	distribution = {}
	if monthly_distribution:
		for d in frappe.db.sql(
			"""select mdp.month, mdp.percentage_allocation
			from `tabMonthly Distribution Percentage` mdp, `tabMonthly Distribution` md
			where mdp.parent=md.name and md.fiscal_year=%s""",
			fiscal_year,
			as_dict=1,
		):
			distribution.setdefault(d.month, d.percentage_allocation)

	dt = frappe.get_cached_value("Fiscal Year", fiscal_year, "year_start_date")
	accumulated_percentage = 0.0

	while dt <= getdate(posting_date):
		if monthly_distribution:
			accumulated_percentage += distribution.get(getdate(dt).strftime("%B"), 0)
		else:
			accumulated_percentage += 100.0 / 12

		dt = add_months(dt, 1)

	return annual_budget * accumulated_percentage / 100


def get_item_details(args):
	cost_center, expense_account = None, None

	if not args.get("company"):
		return cost_center, expense_account

	if args.item_code:
		item_defaults = frappe.db.get_value(
			"Item Default",
			{"parent": args.item_code, "company": args.get("company")},
>>>>>>> 7c4cf3e834 (Favicon.svg)
			["buying_cost_center", "expense_account"],
		)
		if item_defaults:
			cost_center, expense_account = item_defaults

	if not (cost_center and expense_account):
		for doctype in ["Item Group", "Company"]:
<<<<<<< HEAD
			data = get_expense_cost_center(doctype, params)
=======
			data = get_expense_cost_center(doctype, args)
>>>>>>> 7c4cf3e834 (Favicon.svg)

			if not cost_center and data:
				cost_center = data[0]

			if not expense_account and data:
				expense_account = data[1]

			if cost_center and expense_account:
				return cost_center, expense_account

	return cost_center, expense_account


<<<<<<< HEAD
def get_expense_cost_center(doctype, params):
	if doctype == "Item Group":
		return frappe.db.get_value(
			"Item Default",
			{"parent": params.get(frappe.scrub(doctype)), "company": params.get("company")},
=======
def get_expense_cost_center(doctype, args):
	if doctype == "Item Group":
		return frappe.db.get_value(
			"Item Default",
			{"parent": args.get(frappe.scrub(doctype)), "company": args.get("company")},
>>>>>>> 7c4cf3e834 (Favicon.svg)
			["buying_cost_center", "expense_account"],
		)
	else:
		return frappe.db.get_value(
<<<<<<< HEAD
			doctype, params.get(frappe.scrub(doctype)), ["cost_center", "default_expense_account"]
		)


def get_fiscal_year_date_range(from_fiscal_year, to_fiscal_year):
	from_year = frappe.get_cached_value(
		"Fiscal Year", from_fiscal_year, ["year_start_date", "year_end_date"], as_dict=True
	)
	to_year = frappe.get_cached_value(
		"Fiscal Year", to_fiscal_year, ["year_start_date", "year_end_date"], as_dict=True
	)
	return from_year.year_start_date, to_year.year_end_date


@frappe.whitelist()
def revise_budget(budget_name):
	old_budget = frappe.get_doc("Budget", budget_name)

	if old_budget.docstatus == 1:
		old_budget.cancel()

	new_budget = frappe.copy_doc(old_budget)
	new_budget.docstatus = 0
	new_budget.revision_of = old_budget.name
	new_budget.insert()

	return new_budget.name
=======
			doctype, args.get(frappe.scrub(doctype)), ["cost_center", "default_expense_account"]
		)
>>>>>>> 7c4cf3e834 (Favicon.svg)
