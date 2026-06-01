# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType, Field, Order
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.utils import QueryBuilder
from frappe.utils.data import comma_or

SALES_TRANSACTION_DOCTYPES = ["Sales Order", "Sales Invoice", "Delivery Note", "POS Invoice"]


def execute(filters=None):
	if not filters:
		filters = {}

	return SalesPartnerCommissionSummaryReport(filters).run()


class SalesPartnerSummaryReport:
	"""
	Base class to generate Sales Partner Summary related Reports.
	"""

	dt: DocType
	date_field: str
	date_label: str
	columns: list
	data: list
	query: QueryBuilder
	filters: dict

	def __init__(self, filters: dict):
		self.filters = filters
		self.columns = []

	def run(self):
		self.validate_filters()
		self.prepare_columns()
		self.get_data()

		return self.columns, self.data

	def validate_filters(self):
		if not self.filters.get("doctype"):
			frappe.throw(_("Please select the document type first."))

		if self.filters.get("doctype") not in SALES_TRANSACTION_DOCTYPES:
			frappe.throw(_("DocType can be one of them {0}").format(comma_or(SALES_TRANSACTION_DOCTYPES)))

		if not self.filters.get("company"):
			frappe.throw(_("Please select a company."))

		if (
			self.filters.get("from_date")
			and self.filters.get("to_date")
			and self.filters.get("from_date") > self.filters.get("to_date")
		):
			frappe.throw(_("From Date cannot be greater than To Date."))

		self._set_date_field_and_label()

	def _set_date_field_and_label(self):
		self.date_field = (
			"transaction_date" if self.filters.get("doctype") == "Sales Order" else "posting_date"
		)
		self.date_label = _("Order Date") if self.date_field == "transaction_date" else _("Posting Date")

	def prepare_columns(self):
		"""
		Extend this method to add columns on the report. Use `make_column` to add more columns.
		"""
		raise NotImplementedError

	def get_data(self):
		self.build_report_query()

		self.data = self.query.run(as_dict=1)

	def build_report_query(self):
		self._build_report_base_query()
		self.extend_report_query()
		self._apply_common_filters()
		self.apply_filters()

	def _build_report_base_query(self):
		self.dt = DocType(self.filters.get("doctype"))

		company_currency = frappe.get_cached_value("Company", self.filters.get("company"), "default_currency")

		self.query = (
			frappe.qb.from_(self.dt)
			.select(
				self.dt.name,
				self.dt.customer,
				self.dt.territory,
				Field(self.date_field, "posting_date", table=self.dt),
				self.dt.sales_partner,
				self.dt.commission_rate,
				ConstantColumn(company_currency).as_("currency"),
			)
			.where(
				(self.dt.docstatus == 1) & (self.dt.sales_partner.notnull()) & (self.dt.sales_partner != "")
			)
			.orderby(self.dt.name, order=Order.desc)
			.orderby(self.dt.sales_partner)
		)

	def extend_report_query(self):
		"""
		Extend this method to select more columns on the query.
		"""
		pass

	def _apply_common_filters(self):
		for field in ["company", "customer", "territory", "sales_partner"]:
			if self.filters.get(field):
				self.query = self.query.where(Field(field, table=self.dt) == self.filters.get(field))

		if self.filters.get("from_date"):
			self.query = self.query.where(
				Field(self.date_field, table=self.dt) >= self.filters.get("from_date")
			)

		if self.filters.get("to_date"):
			self.query = self.query.where(
				Field(self.date_field, table=self.dt) <= self.filters.get("to_date")
			)

	def apply_filters(self):
		"""
		Extend this method to add more conditions on the query.
		"""
		pass

	def make_column(
		self, label: str, fieldname: str, fieldtype: str, width: int = 140, options: str = "", hidden: int = 0
	):
		self.columns.append(
			dict(
				label=label,
				fieldname=fieldname,
				fieldtype=fieldtype,
				options=options,
				width=width,
				hidden=hidden,
			)
		)


class SalesPartnerCommissionSummaryReport(SalesPartnerSummaryReport):
	def prepare_columns(self):
		self.make_column(_(self.filters.get("doctype")), "name", "Link", options=self.filters.get("doctype"))

		self.make_column(_("Customer"), "customer", "Link", options="Customer")

		self.make_column(_("Currency"), "currency", "Data", 80, hidden=1)

		self.make_column(_("Territory"), "territory", "Link", 100, "Territory")

		self.make_column(self.date_label, "posting_date", "Date")

		self.make_column(_("Amount"), "amount", "Currency", 120, "currency")

		self.make_column(_("Sales Partner"), "sales_partner", "Link", options="Sales Partner")

		self.make_column(_("Commission Rate %"), "commission_rate", "Data", 100)

		self.make_column(_("Total Commission"), "total_commission", "Currency", 120, "currency")

	def extend_report_query(self):
		self.query = self.query.select(
			self.dt.base_net_total.as_("amount"),
			self.dt.total_commission,
		)
