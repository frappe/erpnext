from collections import OrderedDict

import frappe
from frappe import _, qb
from frappe.query_builder import Criterion
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt, fmt_money, get_link_to_form

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

	def validate(self):
		self.build_validation_map()
		self.validate_for_overbooking()

	def build_validation_map(self):
		self.build_budget_keys()
		self.build_item_keys()
		self.build_to_validate_map()

	def initialize_dict(self, key):
		_obj = frappe._dict(
			{
				"budget_amount": self.budget_map[key].budget_amount,
				"budget_doc": self.budget_map[key],
				"requested_amount": 0,
				"ordered_amount": 0,
				"actual_expense": 0,
				"current_requested_amount": 0,
				"current_ordered_amount": 0,
				"current_actual_exp_amount": 0,
			}
		)
		_obj.update(
			{
				"accumulated_monthly_budget": get_accumulated_monthly_budget(
					self.budget_map[key].name,
					self.doc_date,
				)
			}
		)

		if self.document_type in ["Purchase Order", "Material Request"]:
			_obj.update({"items_to_process": self.item_map[key]})
		elif self.document_type == "GL Map":
			_obj.update({"gl_to_process": self.item_map[key]})
		return _obj

	@property
	def overlap(self):
		return self.budget_keys & self.item_keys

	def build_to_validate_map(self):
		self.to_validate = frappe._dict()
		for key in self.overlap:
			self.to_validate[key] = self.initialize_dict(key)

	def validate_for_overbooking(self):
		for key, v in self.to_validate.items():
			self.get_ordered_amount(key)
			self.get_requested_amount(key)

			# Pre-emptive validation before hitting ledger
			self.handle_actions(key, v)

			# Validation happens after submit for Purchase Order and
			# Material Request and so will be included in the query
			# result. so no need to set current document amount
			if self.document_type == "GL Map":
				v.current_actual_exp_amount = sum([x.debit - x.credit for x in v.get("gl_to_process", [])])

			self.get_actual_expense(key)
			self.handle_actions(key, v)

	def get_child_nodes(self, budget_against, dimension):
		lft, rgt = frappe.db.get_all(
			budget_against, filters={"name": dimension}, fields=["lft", "rgt"], as_list=1
		)[0]
		return frappe.db.get_all(budget_against, filters={"lft": [">=", lft], "rgt": ["<=", rgt]}, as_list=1)

	@property
	def budget_keys(self):
		return self.budget_map.keys()

	def build_budget_keys(self):
		"""
		key structure - (dimension_type, dimension, GL account)
		"""
		self.budget_map = OrderedDict()
		for _bud in self.get_budget_records():
			budget_against = frappe.scrub(_bud.budget_against)
			dimension = _bud.get(budget_against)

			if _bud.is_tree and frappe.get_cached_value(_bud.budget_against, dimension, "is_group"):
				child_nodes = self.get_child_nodes(_bud.budget_against, dimension)
				for child in child_nodes:
					key = (budget_against, child[0], _bud.account)
					self.budget_map[key] = _bud
			else:
				key = (budget_against, dimension, _bud.account)
				# TODO: ensure duplicate keys are not possible
				self.budget_map[key] = _bud

	@property
	def item_keys(self):
		return self.item_map.keys()

	def build_item_keys(self):
		"""
		key structure - (dimension_type, dimension, GL account)
		"""
		self.item_map = OrderedDict()
		if self.document_type in ["Purchase Order", "Material Request"]:
			for itm in self.doc.items:
				for dim in self.dimensions:
					if itm.get(dim.get("fieldname")):
						key = (dim.get("fieldname"), itm.get(dim.get("fieldname")), itm.expense_account)
						# TODO: How to handle duplicate items - same item with same dimension with same account
						self.item_map.setdefault(key, []).append(itm)
		elif self.document_type == "GL Map":
			for gl in self.gl_map:
				for dim in self.dimensions:
					if gl.get(dim.get("fieldname")):
						key = (dim.get("fieldname"), gl.get(dim.get("fieldname")), gl.get("account"))
						self.item_map.setdefault(key, []).append(gl)

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
				& (bud.budget_start_date <= self.doc_date)
				& (bud.budget_end_date >= self.doc_date)
			)
		)

		for x in self.dimensions:
			query = query.select(bud[x.get("fieldname")])

		_budgets = query.run(as_dict=True)

		for x in _budgets:
			x.is_tree = frappe.get_meta(x.budget_against).is_tree

		return _budgets

	def get_ordered_amount(self, key: tuple | None = None):
		if key:
			po = qb.DocType("Purchase Order")
			poi = qb.DocType("Purchase Order Item")

			conditions = []
			conditions.append(po.company.eq(self.company))
			conditions.append(po.docstatus.eq(1))
			conditions.append(po.status.ne("Closed"))
			conditions.append(po.transaction_date[self.fy_start_date : self.fy_end_date])
			conditions.append(poi.amount.gt(poi.billed_amt))
			conditions.append(poi.expense_account.eq(key[2]))

			if self.document_type in ["Purchase Order", "Material Request"]:
				if items := set([x.item_code for x in self.doc.items]):
					conditions.append(poi.item_code.isin(items))

			# key structure - (dimension_type, dimension, GL account)
			conditions.append(poi[key[0]].eq(key[1]))

			if ordered_amount := (
				qb.from_(po)
				.inner_join(poi)
				.on(po.name == poi.parent)
				.select(Sum(IfNull(poi.amount, 0) - IfNull(poi.billed_amt, 0)).as_("amount"))
				.where(Criterion.all(conditions))
				.run(as_dict=True)
			):
				self.to_validate[key].ordered_amount = ordered_amount[0].amount or 0

	def get_requested_amount(self, key: tuple | None = None):
		if key:
			mr = qb.DocType("Material Request")
			mri = qb.DocType("Material Request Item")

			conditions = []
			conditions.append(mr.company.eq(self.company))
			conditions.append(mr.docstatus.eq(1))
			conditions.append(mr.material_request_type.eq("Purchase"))
			conditions.append(mr.status.ne("Stopped"))
			conditions.append(mr.transaction_date[self.fy_start_date : self.fy_end_date])
			conditions.append(mri.expense_account.eq(key[2]))

			if self.document_type in ["Purchase Order", "Material Request"]:
				if items := set([x.item_code for x in self.doc.items]):
					conditions.append(mri.item_code.isin(items))

			# key structure - (dimension_type, dimension, GL account)
			conditions.append(mri[key[0]].eq(key[1]))

			if requested_amount := (
				qb.from_(mr)
				.inner_join(mri)
				.on(mr.name == mri.parent)
				.select((Sum(IfNull(mri.stock_qty, 0) - IfNull(mri.ordered_qty, 0)) * mri.rate).as_("amount"))
				.where(Criterion.all(conditions))
				.run(as_dict=True)
			):
				self.to_validate[key].requested_amount = requested_amount[0].amount or 0

	def get_actual_expense(self, key: tuple | None = None):
		if key:
			gl = qb.DocType("GL Entry")

			query = (
				qb.from_(gl)
				.select((Sum(gl.debit) - Sum(gl.credit)).as_("balance"))
				.where(
					gl.is_cancelled.eq(0)
					& gl.account.eq(key[2])
					& gl.fiscal_year.eq(self.fiscal_year)
					& gl.company.eq(self.company)
					& gl[key[0]].eq(key[1])
					& gl.posting_date[self.fy_start_date : self.fy_end_date]
				)
			)
			if actual_expense := query.run(as_dict=True):
				self.to_validate[key].actual_expense = actual_expense[0].balance or 0

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

	def handle_individual_doctype_action(
		self, key, config, budget, budget_amt, existing_amt, current_amt, acc_monthly_budget
	):
		if config.applies:
			currency = frappe.get_cached_value("Company", self.company, "default_currency")
			annual_diff = (existing_amt + current_amt) - budget_amt
			if annual_diff > 0:
				_msg = _(
					"Annual Budget for Account {0} against {1}: {2} is {3}. It will be exceeded by {4}"
				).format(
					frappe.bold(key[2]),
					frappe.bold(frappe.unscrub(key[0])),
					frappe.bold(key[1]),
					frappe.bold(fmt_money(budget_amt, currency=currency)),
					frappe.bold(fmt_money(annual_diff, currency=currency)),
				)
				self.execute_action(config.action_for_annual, _msg)

			monthly_diff = (existing_amt + current_amt) - acc_monthly_budget
			if monthly_diff > 0:
				_msg = _(
					"Accumulated Monthly Budget for Account {0} against {1}: {2} is {3}. It will be exceeded by {4}"
				).format(
					frappe.bold(key[2]),
					frappe.bold(frappe.unscrub(key[0])),
					frappe.bold(key[1]),
					frappe.bold(fmt_money(acc_monthly_budget, currency=currency)),
					frappe.bold(fmt_money(monthly_diff, currency=currency)),
				)
				self.execute_action(config.action_for_monthly, _msg)

	def handle_purchase_order_overlimit(self, key, v_map):
		self.handle_individual_doctype_action(
			key,
			frappe._dict(
				{
					"applies": v_map.budget_doc.applicable_on_purchase_order,
					"action_for_annual": v_map.budget_doc.action_if_annual_budget_exceeded_on_po,
					"action_for_monthly": v_map.budget_doc.action_if_accumulated_monthly_budget_exceeded_on_po,
				}
			),
			v_map.budget_doc.name,
			v_map.budget_amount,
			v_map.ordered_amount,
			v_map.current_ordered_amount,
			v_map.accumulated_monthly_budget,
		)

	def handle_material_request_overlimit(self, key, v_map):
		self.handle_individual_doctype_action(
			key,
			frappe._dict(
				{
					"applies": v_map.budget_doc.applicable_on_material_request,
					"action_for_annual": v_map.budget_doc.action_if_annual_budget_exceeded_on_mr,
					"action_for_monthly": v_map.budget_doc.action_if_accumulated_monthly_budget_exceeded_on_mr,
				}
			),
			v_map.budget_doc.name,
			v_map.budget_amount,
			v_map.requested_amount,
			v_map.current_requested_amount,
			v_map.accumulated_monthly_budget,
		)

	def handle_actual_expense_overlimit(self, key, v_map):
		self.handle_individual_doctype_action(
			key,
			frappe._dict(
				{
					"applies": v_map.budget_doc.applicable_on_booking_actual_expenses,
					"action_for_annual": v_map.budget_doc.action_if_annual_budget_exceeded,
					"action_for_monthly": v_map.budget_doc.action_if_accumulated_monthly_budget_exceeded,
				}
			),
			v_map.budget_doc.name,
			v_map.budget_amount,
			v_map.actual_expense,
			v_map.current_actual_exp_amount,
			v_map.accumulated_monthly_budget,
		)

	def handle_actions(self, key, v_map):
		self.handle_purchase_order_overlimit(key, v_map)
		self.handle_material_request_overlimit(key, v_map)
		self.handle_actual_expense_overlimit(key, v_map)
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
		monthly_diff = (
			v_map.ordered_amount + v_map.requested_amount + v_map.actual_expense + current_amt
		) - v_map.accumulated_monthly_budget
		if monthly_diff > 0:
			currency = frappe.get_cached_value("Company", self.company, "default_currency")
			_msg = _(
				"Accumulated Monthly Budget for Account {0} against {1} {2} is {3}. It will be collectively ({4}) exceeded by {5}"
			).format(
				frappe.bold(key[2]),
				frappe.bold(frappe.unscrub(key[0])),
				frappe.bold(key[1]),
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
		total_diff = (
			v_map.ordered_amount + v_map.requested_amount + v_map.actual_expense + current_amt
		) - v_map.budget_amount
		if total_diff > 0:
			currency = frappe.get_cached_value("Company", self.company, "default_currency")
			_msg = _(
				"Annual Budget for Account {0} against {1} {2} is {3}. It will be collectively ({4}) exceeded by {5}"
			).format(
				frappe.bold(key[2]),
				frappe.bold(frappe.unscrub(key[0])),
				frappe.bold(key[1]),
				frappe.bold(fmt_money(v_map.budget_amount, currency=currency)),
				self.budget_applicable_for(v_map, current_amt),
				frappe.bold(fmt_money(total_diff, currency=currency)),
			)
			self.execute_action(v_map.budget_doc.action_if_annual_exceeded_on_cumulative_expense, _msg)
