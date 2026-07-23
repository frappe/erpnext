# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Case

from erpnext.selling.report.sales_partner_commission_summary.sales_partner_commission_summary import (
	SalesPartnerSummaryReport,
)


def execute(filters=None):
	if not filters:
		filters = {}

	return SalesPartnerTransactionSummaryReport(filters=filters).run()


class SalesPartnerTransactionSummaryReport(SalesPartnerSummaryReport):
	def prepare_columns(self):
		self.make_column(_(self.filters.get("doctype")), "name", "Link", options=self.filters.get("doctype"))

		self.make_column(_("Customer"), "customer", "Link", options="Customer")

		self.make_column(_("Currency"), "currency", "Data", 80, hidden=1)

		self.make_column(_("Territory"), "territory", "Link", 100, "Territory")

		self.make_column(self.date_label, "posting_date", "Date")

		self.make_column(_("Item Code"), "item_code", "Link", 100, "Item")

		self.make_column(_("Item Group"), "item_group", "Link", 100, "Item Group")

		self.make_column(_("Brand"), "brand", "Link", 100, "Brand")

		self.make_column(_("Quantity"), "qty", "Float", 120)

		self.make_column(_("Rate"), "rate", "Currency", 120, "currency")

		self.make_column(_("Amount"), "amount", "Currency", 120, "currency")

		self.make_column(_("Sales Partner"), "sales_partner", "Link", options="Sales Partner")

		self.make_column(_("Commission Rate %"), "commission_rate", "Data", 100)

		self.make_column(_("Commission"), "commission", "Currency", 120, "currency")

	def extend_report_query(self):
		self.dt_item = frappe.qb.DocType(f"{self.filters['doctype']} Item")

		self.query = (
			self.query.join(self.dt_item)
			.on(self.dt.name == self.dt_item.parent)
			.select(
				self.dt_item.base_net_rate.as_("rate"),
				self.dt_item.qty,
				self.dt_item.base_net_amount.as_("amount"),
				Case()
				.when(
					self.dt_item.grant_commission.eq(1),
					((self.dt_item.base_net_amount * self.dt.commission_rate) / 100),
				)
				.else_(0)
				.as_("commission"),
				self.dt_item.brand,
				self.dt_item.item_group,
				self.dt_item.item_code,
			)
		)

	def apply_filters(self):
		if not self.filters.get("show_return_entries"):
			self.query = self.query.where(self.dt_item.qty > 0.0)

		if self.filters.get("brand"):
			self.query = self.query.where(self.dt_item.brand == self.filters.get("brand"))

		if self.filters.get("item_group"):
			lft, rgt = frappe.get_cached_value("Item Group", self.filters.get("item_group"), ["lft", "rgt"])
			if item_groups := frappe.get_all(
				"Item Group", filters=[["lft", ">=", lft], ["rgt", "<=", rgt]], pluck="name"
			):
				self.query = self.query.where(self.dt_item.item_group.isin(item_groups))
