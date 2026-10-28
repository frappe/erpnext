import frappe
from frappe import _, qb
from frappe.query_builder import Case, Criterion
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt, fmt_money, get_last_day, getdate

from erpnext.accounts.doctype.budget.budget import BudgetError, get_accumulated_monthly_budget
from erpnext.accounts.utils import get_fiscal_year


class BudgetValidation:
	def __init__(self, doc: object | None = None, gl_map: list | None = None):
		if doc:
			self.document_type = doc.get("doctype")
			self.doc = doc
			self.company = doc.get("company")
			self.doc_date = doc.get("transaction_date")
		elif gl_map:
			# When GL Map is passed, there is a possibility of multiple fiscal year.
			# TODO: need to handle it
			self.document_type = "GL Map"
			self.gl_map = gl_map
			self.company = gl_map[0].company
			self.doc_date = gl_map[0].posting_date

		fy = get_fiscal_year(self.doc_date)
		self.fiscal_year = fy[0]
		self.fy_start_date = fy[1]
		self.fy_end_date = fy[2]
		self.get_dimensions()
		self.exception_approver_role = frappe.get_cached_value(
			"Company", self.company, "exception_budget_approver_role"
		)
		self.amount_precision = frappe.get_precision("Budget", "budget_amount")

	def validate(self):
		self.build_validation_map()
		self.validate_for_overbooking()

	def build_validation_map(self):
		"""One entry per budget that the document or GL map touches. A budget on a group dimension
		covers every row posted to a node of its subtree."""
		self.to_validate = frappe._dict()
		for budget in self.get_budget_records():
			rows = self.get_rows_for_budget(budget)
			if rows:
				self.to_validate[budget.name] = self.initialize_dict(budget, rows)

	def get_accounts(self) -> list:
		if self.document_type in ["Purchase Order", "Material Request"]:
			return list({row.expense_account for row in self.doc.items if row.expense_account})

		return list({row.get("account") for row in self.gl_map if row.get("account")})

	def get_rows_for_budget(self, budget) -> list:
		if self.document_type in ["Purchase Order", "Material Request"]:
			rows = [row for row in self.doc.items if row.expense_account == budget.account]
		else:
			rows = [row for row in self.gl_map if row.get("account") == budget.account]

		return [row for row in rows if row.get(budget.dimension_field) in budget.dimension_values]

	def initialize_dict(self, budget, rows):
		_obj = frappe._dict(
			{
				"budget_amount": budget.budget_amount,
				"budget_doc": budget,
				"requested_amount": 0,
				"ordered_amount": 0,
				"actual_expense": 0,
				"requested_amount_to_month_end": 0,
				"ordered_amount_to_month_end": 0,
				"actual_expense_to_month_end": 0,
				"current_requested_amount": 0,
				"current_ordered_amount": 0,
				"current_actual_exp_amount": 0,
				"accumulated_monthly_budget": get_accumulated_monthly_budget(budget.name, self.doc_date),
			}
		)

		if self.document_type in ["Purchase Order", "Material Request"]:
			_obj.update({"items_to_process": rows})
		elif self.document_type == "GL Map":
			_obj.update({"gl_to_process": rows})
		return _obj

	def validate_for_overbooking(self):
		for key, v in self.to_validate.items():
			# Validation happens after submit for Purchase Order and
			# Material Request and so will be included in the query
			# result. so no need to set current document amount
			if self.document_type == "GL Map":
				v.current_actual_exp_amount = sum([x.debit - x.credit for x in v.get("gl_to_process", [])])

			self.get_ordered_amount(key)
			self.get_requested_amount(key)
			self.get_actual_expense(key)
			self.handle_actions(key, v)

	def get_child_nodes(self, budget_against, dimension):
		lft, rgt = frappe.db.get_all(
			budget_against, filters={"name": dimension}, fields=["lft", "rgt"], as_list=1
		)[0]
		return frappe.db.get_all(budget_against, filters={"lft": [">=", lft], "rgt": ["<=", rgt]}, as_list=1)

	def get_dimension_values(self, budget) -> list:
		dimension = budget.get(budget.dimension_field)
		if budget.is_tree and frappe.get_cached_value(budget.budget_against, dimension, "is_group"):
			return [child[0] for child in self.get_child_nodes(budget.budget_against, dimension)]

		return [dimension]

	def get_period(self, budget) -> tuple:
		"""The budget's own period (it may span several fiscal years), and the same period up to the
		end of the posting month for the accumulated monthly limit."""
		month_end = min(getdate(get_last_day(self.doc_date)), getdate(budget.budget_end_date))
		return getdate(budget.budget_start_date), getdate(budget.budget_end_date), month_end

	def get_dimensions(self):
		self.dimensions = []
		for _x in frappe.db.get_all("Accounting Dimension"):
			self.dimensions.append(frappe.get_lazy_doc("Accounting Dimension", _x.name))
		self.dimensions.extend(
			[
				{"fieldname": "cost_center", "document_type": "Cost Center"},
				{"fieldname": "project", "document_type": "Project"},
			]
		)

	def get_budget_records(self) -> list:
		bud = qb.DocType("Budget")

		query = (
			qb.from_(bud)
			.select(
				bud.name,
				bud.budget_against,
				bud.company,
				bud.account,
				bud.budget_amount,
				bud.from_fiscal_year,
				bud.to_fiscal_year,
				bud.budget_start_date,
				bud.budget_end_date,
				bud.applicable_on_material_request,
				bud.action_if_annual_budget_exceeded_on_mr,
				bud.action_if_accumulated_monthly_budget_exceeded_on_mr,
				bud.applicable_on_purchase_order,
				bud.action_if_annual_budget_exceeded_on_po,
				bud.action_if_accumulated_monthly_budget_exceeded_on_po,
				bud.applicable_on_booking_actual_expenses,
				bud.action_if_annual_budget_exceeded,
				bud.action_if_accumulated_monthly_budget_exceeded,
				bud.applicable_on_cumulative_expense,
				bud.action_if_annual_exceeded_on_cumulative_expense,
				bud.action_if_accumulated_monthly_exceeded_on_cumulative_expense,
			)
			.where(
				(bud.docstatus == 1)
				& (bud.company == self.company)
				& (bud.account.isin(self.get_accounts() or [""]))
				& (bud.budget_start_date <= self.doc_date)
				& (bud.budget_end_date >= self.doc_date)
			)
		)

		for x in self.dimensions:
			query = query.select(bud[x.get("fieldname")])

		_budgets = query.run(as_dict=True)

		for x in _budgets:
			x.is_tree = frappe.get_meta(x.budget_against).is_tree
			x.dimension_field = frappe.scrub(x.budget_against)
			x.dimension_values = self.get_dimension_values(x)

		return _budgets

	def get_ordered_amount(self, key: str | None = None):
		if key:
			v = self.to_validate[key]
			budget = v.budget_doc
			start, end, month_end = self.get_period(budget)
			po = qb.DocType("Purchase Order")
			poi = qb.DocType("Purchase Order Item")

			conditions = []
			conditions.append(po.company.eq(self.company))
			conditions.append(po.docstatus.eq(1))
			conditions.append(po.status.ne("Closed"))
			conditions.append(po.transaction_date[start:end])
			conditions.append(poi.amount.gt(poi.billed_amt))
			conditions.append(poi.closed.eq(0))
			conditions.append(poi.expense_account.eq(budget.account))
			conditions.append(poi[budget.dimension_field].isin(budget.dimension_values))

			amount = (IfNull(poi.amount, 0) - IfNull(poi.billed_amt, 0)) * IfNull(po.conversion_rate, 1)
			if ordered_amount := (
				qb.from_(po)
				.inner_join(poi)
				.on(po.name == poi.parent)
				.select(
					Sum(amount).as_("amount"),
					Sum(Case().when(po.transaction_date <= month_end, amount).else_(0)).as_("to_month_end"),
				)
				.where(Criterion.all(conditions))
				.run(as_dict=True)
			):
				v.ordered_amount = flt(ordered_amount[0].amount)
				v.ordered_amount_to_month_end = flt(ordered_amount[0].to_month_end)

	def get_requested_amount(self, key: str | None = None):
		if key:
			v = self.to_validate[key]
			budget = v.budget_doc
			start, end, month_end = self.get_period(budget)
			mr = qb.DocType("Material Request")
			mri = qb.DocType("Material Request Item")

			conditions = []
			conditions.append(mr.company.eq(self.company))
			conditions.append(mr.docstatus.eq(1))
			conditions.append(mr.material_request_type.eq("Purchase"))
			conditions.append(mr.status.ne("Stopped"))
			conditions.append(mr.transaction_date[start:end])
			conditions.append(mri.stock_qty.gt(mri.ordered_qty))
			conditions.append(mri.expense_account.eq(budget.account))
			conditions.append(mri[budget.dimension_field].isin(budget.dimension_values))

			amount = (
				(IfNull(mri.stock_qty, 0) - IfNull(mri.ordered_qty, 0))
				* IfNull(mri.rate, 0)
				/ mri.conversion_factor
			)
			if requested_amount := (
				qb.from_(mr)
				.inner_join(mri)
				.on(mr.name == mri.parent)
				.select(
					Sum(amount).as_("amount"),
					Sum(Case().when(mr.transaction_date <= month_end, amount).else_(0)).as_("to_month_end"),
				)
				.where(Criterion.all(conditions))
				.run(as_dict=True)
			):
				v.requested_amount = flt(requested_amount[0].amount)
				v.requested_amount_to_month_end = flt(requested_amount[0].to_month_end)

	def get_actual_expense(self, key: str | None = None):
		if key:
			v = self.to_validate[key]
			budget = v.budget_doc
			start, end, month_end = self.get_period(budget)
			gl = qb.DocType("GL Entry")

			balance = gl.debit - gl.credit
			query = (
				qb.from_(gl)
				.select(
					Sum(balance).as_("balance"),
					Sum(Case().when(gl.posting_date <= month_end, balance).else_(0)).as_("to_month_end"),
				)
				.where(
					gl.is_cancelled.eq(0)
					& gl.account.eq(budget.account)
					& gl.company.eq(self.company)
					& gl[budget.dimension_field].isin(budget.dimension_values)
					& gl.posting_date[start:end]
				)
			)
			if actual_expense := query.run(as_dict=True):
				v.actual_expense = flt(actual_expense[0].balance)
				v.actual_expense_to_month_end = flt(actual_expense[0].to_month_end)

	def stop(self, msg):
		frappe.throw(msg, BudgetError, title=_("Budget Exceeded"))

	def warn(self, msg):
		frappe.msgprint(msg, _("Budget Exceeded"))

	def execute_action(self, action, msg):
		if self.exception_approver_role and self.exception_approver_role in frappe.get_roles(
			frappe.session.user
		):
			self.warn(msg)
			return

		if action == "Warn":
			self.warn(msg)

		if action == "Stop":
			self.stop(msg)

	def get_budget_label(self, budget) -> tuple:
		return (
			frappe.bold(budget.account),
			frappe.bold(budget.budget_against),
			frappe.bold(budget.get(budget.dimension_field)),
		)

	def handle_individual_doctype_action(
		self,
		config,
		budget,
		budget_amt,
		existing_amt,
		existing_amt_to_month_end,
		current_amt,
		acc_monthly_budget,
	):
		if config.applies:
			currency = frappe.get_cached_value("Company", self.company, "default_currency")
			account, budget_against, dimension = self.get_budget_label(budget)
			annual_diff = flt((existing_amt + current_amt) - budget_amt, self.amount_precision)
			if annual_diff > 0:
				_msg = _(
					"Annual Budget for Account {0} against {1}: {2} is {3}. It will be exceeded by {4}"
				).format(
					account,
					budget_against,
					dimension,
					frappe.bold(fmt_money(budget_amt, currency=currency)),
					frappe.bold(fmt_money(annual_diff, currency=currency)),
				)
				self.execute_action(config.action_for_annual, _msg)

			monthly_diff = flt(
				(existing_amt_to_month_end + current_amt) - acc_monthly_budget, self.amount_precision
			)
			if monthly_diff > 0:
				_msg = _(
					"Accumulated Monthly Budget for Account {0} against {1}: {2} is {3}. It will be exceeded by {4}"
				).format(
					account,
					budget_against,
					dimension,
					frappe.bold(fmt_money(acc_monthly_budget, currency=currency)),
					frappe.bold(fmt_money(monthly_diff, currency=currency)),
				)
				self.execute_action(config.action_for_monthly, _msg)

	def handle_purchase_order_overlimit(self, v_map):
		self.handle_individual_doctype_action(
			frappe._dict(
				{
					"applies": v_map.budget_doc.applicable_on_purchase_order,
					"action_for_annual": v_map.budget_doc.action_if_annual_budget_exceeded_on_po,
					"action_for_monthly": v_map.budget_doc.action_if_accumulated_monthly_budget_exceeded_on_po,
				}
			),
			v_map.budget_doc,
			v_map.budget_amount,
			v_map.ordered_amount,
			v_map.ordered_amount_to_month_end,
			v_map.current_ordered_amount,
			v_map.accumulated_monthly_budget,
		)

	def handle_material_request_overlimit(self, v_map):
		self.handle_individual_doctype_action(
			frappe._dict(
				{
					"applies": v_map.budget_doc.applicable_on_material_request,
					"action_for_annual": v_map.budget_doc.action_if_annual_budget_exceeded_on_mr,
					"action_for_monthly": v_map.budget_doc.action_if_accumulated_monthly_budget_exceeded_on_mr,
				}
			),
			v_map.budget_doc,
			v_map.budget_amount,
			v_map.requested_amount,
			v_map.requested_amount_to_month_end,
			v_map.current_requested_amount,
			v_map.accumulated_monthly_budget,
		)

	def handle_actual_expense_overlimit(self, v_map):
		self.handle_individual_doctype_action(
			frappe._dict(
				{
					"applies": v_map.budget_doc.applicable_on_booking_actual_expenses,
					"action_for_annual": v_map.budget_doc.action_if_annual_budget_exceeded,
					"action_for_monthly": v_map.budget_doc.action_if_accumulated_monthly_budget_exceeded,
				}
			),
			v_map.budget_doc,
			v_map.budget_amount,
			v_map.actual_expense,
			v_map.actual_expense_to_month_end,
			v_map.current_actual_exp_amount,
			v_map.accumulated_monthly_budget,
		)

	def handle_actions(self, key, v_map):
		# Each document checks its own limit: a ledger posting does not re-check open orders and requests
		if self.document_type == "Purchase Order":
			self.handle_purchase_order_overlimit(v_map)
		elif self.document_type == "Material Request":
			self.handle_material_request_overlimit(v_map)
		else:
			self.handle_actual_expense_overlimit(v_map)

		# PO + MR + Actual Expense
		self.handle_cumulative_overlimit(key, v_map)

	def handle_cumulative_overlimit(self, key, v_map):
		if v_map.budget_doc.applicable_on_cumulative_expense:
			self.handle_cumulative_overlimit_for_monthly(key, v_map)
			self.handle_cumulative_overlimit_for_annual(key, v_map)

	def budget_applicable_for(self, v_map, current_amt) -> str:
		budget_doc = v_map.budget_doc
		doctypes = []
		if budget_doc.applicable_on_purchase_order and v_map.ordered_amount:
			doctypes.append("Purchase Order")
		if budget_doc.applicable_on_material_request and v_map.requested_amount:
			doctypes.append("Material Request")
		if budget_doc.applicable_on_booking_actual_expenses and v_map.actual_expense:
			doctypes.append("Actual Expense")
		if current_amt:
			doctypes.append("This Document")

		doctypes = [f"'{x}'" for x in doctypes]
		return "+".join(doctypes)

	def handle_cumulative_overlimit_for_monthly(self, key, v_map):
		current_amt = (
			v_map.current_ordered_amount + v_map.current_requested_amount + v_map.current_actual_exp_amount
		)
		monthly_diff = flt(
			v_map.ordered_amount_to_month_end
			+ v_map.requested_amount_to_month_end
			+ v_map.actual_expense_to_month_end
			+ current_amt
			- v_map.accumulated_monthly_budget,
			self.amount_precision,
		)
		if monthly_diff > 0:
			currency = frappe.get_cached_value("Company", self.company, "default_currency")
			account, budget_against, dimension = self.get_budget_label(v_map.budget_doc)
			_msg = _(
				"Accumulated Monthly Budget for Account {0} against {1} {2} is {3}. It will be collectively ({4}) exceeded by {5}"
			).format(
				account,
				budget_against,
				dimension,
				frappe.bold(fmt_money(v_map.accumulated_monthly_budget, currency=currency)),
				self.budget_applicable_for(v_map, current_amt),
				frappe.bold(fmt_money(monthly_diff, currency=currency)),
			)

			self.execute_action(
				v_map.budget_doc.action_if_accumulated_monthly_exceeded_on_cumulative_expense, _msg
			)

	def handle_cumulative_overlimit_for_annual(self, key, v_map):
		current_amt = (
			v_map.current_ordered_amount + v_map.current_requested_amount + v_map.current_actual_exp_amount
		)
		total_diff = flt(
			v_map.ordered_amount
			+ v_map.requested_amount
			+ v_map.actual_expense
			+ current_amt
			- v_map.budget_amount,
			self.amount_precision,
		)
		if total_diff > 0:
			currency = frappe.get_cached_value("Company", self.company, "default_currency")
			account, budget_against, dimension = self.get_budget_label(v_map.budget_doc)
			_msg = _(
				"Annual Budget for Account {0} against {1} {2} is {3}. It will be collectively ({4}) exceeded by {5}"
			).format(
				account,
				budget_against,
				dimension,
				frappe.bold(fmt_money(v_map.budget_amount, currency=currency)),
				self.budget_applicable_for(v_map, current_amt),
				frappe.bold(fmt_money(total_diff, currency=currency)),
			)
			self.execute_action(v_map.budget_doc.action_if_annual_exceeded_on_cumulative_expense, _msg)
