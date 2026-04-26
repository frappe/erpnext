# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Case, DocType, Order
from frappe.query_builder import functions as fn
from frappe.query_builder.utils import QueryBuilder
from frappe.utils import cint
from pypika.terms import Term

from erpnext import get_company_currency


def execute(filters=None):
	if not filters:
		filters = {}

	return InactiveCustomersReport(filters).run()


class InactiveCustomersReport:
	filters: dict
	query: QueryBuilder
	data: list
	columns: list
	date_field: str

	def __init__(self, filters):
		self.filters = filters
		self.columns = []

	def run(self):
		self.validate_filters()
		self.prepare_columns()
		self.get_data()

		return self.columns, self.data

	def validate_filters(self):
		# Mandatory filters.
		filters = {"days_since_last_order": _("Days Since Last Order"), "doctype": _("DocType")}
		for fieldname, label in filters.items():
			if not self.filters.get(fieldname):
				frappe.throw(_("{0} is a required filter.").format(frappe.bold(label)))

			if fieldname == "days_since_last_order" and cint(self.filters.get(fieldname)) < 0:
				frappe.throw(_("{0} must be greater than zero.").format(frappe.bold(label)))

			if fieldname == "doctype" and self.filters.get(fieldname) not in ["Sales Invoice", "Sales Order"]:
				frappe.throw(_("{0} can be either Sales Invoice or Sales Order.").format(label))

	def prepare_columns(self):
		self.make_column(_("Customer"), "customer", "Link", options="Customer", width=200)

		if frappe.get_single_value("Selling Settings", "cust_master_name") != "Customer Name":
			self.make_column(_("Customer Name"), "customer_name", width=200)

		self.make_column(_("Company"), "company", "Link", options="Company", width=200)

		self.make_column(_("Territory"), "territory", "Link", options="Territory")

		self.make_column(_("Customer Group"), "customer_group", "Link", options="Customer Group")

		self.make_column(_("Number of Order"), "num_of_order", "Int")

		self.make_column(_("Currency"), "currency", "Link", options="Currency", hidden=1)

		self.make_column(_("Total Order Value"), "total_order_value", "Currency", 120, "currency")

		self.make_column(_("Total Order Considered"), "total_order_considered", "Currency", 120, "currency")

		self.make_column(
			_("Last Order"), "last_order", "Link", options=self.filters.get("doctype"), width=200
		)

		self.make_column(_("Last Order Amount"), "last_order_amount", "Currency", 160, "currency")

		self.make_column(_("Last Order Date"), "last_order_date", "Date")

		self.make_column(_("Days Since Last Order"), "days_since_last_order", "Int")

	def make_column(
		self,
		label: str,
		fieldname: str,
		fieldtype: str = "Data",
		width: int = 140,
		options: str = "",
		hidden: int = 0,
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

	def get_data(self):
		self._build_query_and_get_data()
		self._insert_last_sales_amt_and_company_currency()

	def _build_query_and_get_data(self):
		Customer = DocType("Customer")
		SalesDocType = DocType(self.filters.get("doctype"))

		self.date_field = (
			"posting_date" if self.filters.get("doctype") == "Sales Invoice" else "transaction_date"
		)

		days_since_last_order = fn.CurDate() - fn.Max(fn.Field(self.date_field, table=SalesDocType))

		sum_terms = SalesDocType.base_net_total
		if self.filters.get("doctype") == "Sales Order":
			sum_terms = (
				Case()
				.when(
					SalesDocType.status == "Stopped",
					SalesDocType.base_net_total * SalesDocType.per_delivered / 100,
				)
				.else_(sum_terms)
			)

		self.query = (
			frappe.qb.from_(Customer)
			.join(SalesDocType)
			.on((Customer.name == SalesDocType.customer) & (SalesDocType.docstatus == 1))
			.select(
				Customer.name.as_("customer"),
				Customer.customer_name,
				Customer.territory,
				Customer.customer_group,
				SalesDocType.company,
				fn.Count(SalesDocType.name, "num_of_order"),
				fn.Sum(SalesDocType.base_net_total, "total_order_value"),
				fn.Sum(sum_terms, "total_order_considered"),
				fn.Max(fn.Field(self.date_field, table=SalesDocType), "last_order_date"),
				days_since_last_order.as_("days_since_last_order"),
			)
			.groupby(Customer.name, SalesDocType.company)
			.having(days_since_last_order >= self.filters.get("days_since_last_order"))
			.orderby(Term("days_since_last_order"), order=Order.desc)
		)

		if self.filters.get("company"):
			self.query = self.query.where(SalesDocType.company == self.filters.get("company"))

		self.data = self.query.run(as_dict=1)

	def _insert_last_sales_amt_and_company_currency(self):
		for d in self.data:
			d.update({"currency": get_company_currency(d.get("company"))})
			d.update(self._get_last_sales_details(d.get("customer")))

	def _get_last_sales_details(self, customer):
		filters = {"customer": customer, "docstatus": 1}

		if self.filters.get("doctype") == "Sales Invoice":
			filters.update({"is_return": 0})

		last_sales_amount = frappe.get_all(
			self.filters.get("doctype"),
			fields=["name as last_order", "base_net_total as last_order_amount"],
			filters=filters,
			order_by=f"{self.date_field} desc",
			limit=1,
		)

		return last_sales_amount[0] if last_sales_amount else {}
