# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import json
from itertools import groupby

import frappe
from frappe import _
from frappe.utils import flt

import erpnext
from erpnext.setup.utils import get_exchange_rate

NO_SALES_STAGE = "Not Set"


def execute(filters=None):
	return OpportunitySummaryBySalesStage(filters).run()


class OpportunitySummaryBySalesStage:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

	def run(self):
		self.validate_filters()
		self.get_data()
		self.get_columns()
		self.get_chart_data()
		return self.columns, self.data, None, self.chart

	def validate_filters(self):
		if self.filters.get("data_based_on") == "Amount" and not self.filters.get("company"):
			frappe.throw(_("Company is mandatory when Data Based On is Amount"))

	def get_columns(self):
		self.columns = []

		if self.filters.get("based_on") == "Opportunity Owner":
			self.columns.append(
				{"label": _("Opportunity Owner"), "fieldname": "opportunity_owner", "width": 200}
			)

		if self.filters.get("based_on") == "Source":
			self.columns.append(
				{
					"label": _("Source"),
					"fieldname": "utm_source",
					"fieldtype": "Link",
					"options": "UTM Source",
					"width": 200,
				}
			)

		if self.filters.get("based_on") == "Opportunity Type":
			self.columns.append(
				{"label": _("Opportunity Type"), "fieldname": "opportunity_type", "width": 200}
			)

		self.set_sales_stage_columns()

	def set_sales_stage_columns(self):
		self.sales_stage_list = frappe.db.get_list("Sales Stage", pluck="name")
		if any(row["sales_stage"] == NO_SALES_STAGE for row in self.query_result):
			self.sales_stage_list.append(NO_SALES_STAGE)

		for sales_stage in self.sales_stage_list:
			if self.filters.get("data_based_on") == "Number":
				self.columns.append(
					{"label": _(sales_stage), "fieldname": sales_stage, "fieldtype": "Int", "width": 150}
				)

			elif self.filters.get("data_based_on") == "Amount":
				self.columns.append(
					{"label": _(sales_stage), "fieldname": sales_stage, "fieldtype": "Currency", "width": 150}
				)

	def get_data(self):
		self.data = []

		based_on = {
			"Opportunity Owner": "_assign",
			"Source": "utm_source",
			"Opportunity Type": "opportunity_type",
		}[self.filters.get("based_on")]

		data_based_on = {
			"Number": {"COUNT": "*", "as": "count"},
			"Amount": "opportunity_amount as amount",
		}[self.filters.get("data_based_on")]

		self.get_data_query(based_on, data_based_on)

		self.get_rows()

	def get_data_query(self, based_on, data_based_on):
		if self.filters.get("data_based_on") == "Number":
			group_by = "{},{}".format("sales_stage", based_on)
			self.query_result = frappe.db.get_list(
				"Opportunity",
				filters=self.get_conditions(),
				fields=["sales_stage", data_based_on, based_on],
				group_by=group_by,
			)
			self.set_missing_sales_stage()

		elif self.filters.get("data_based_on") == "Amount":
			self.query_result = frappe.db.get_list(
				"Opportunity",
				filters=self.get_conditions(),
				fields=[
					"sales_stage",
					based_on,
					data_based_on,
					"conversion_rate",
					"currency",
					"transaction_date",
				],
			)

			self.set_missing_sales_stage()
			self.convert_to_base_currency()

			for row in self.query_result:
				if not row.get(based_on):
					row[based_on] = "Not Assigned"

			self.grouped_data = []

			grouping_key = lambda o: (o["sales_stage"], o[based_on])  # noqa
			for (sales_stage, _based_on), rows in groupby(
				sorted(self.query_result, key=grouping_key), key=grouping_key
			):
				self.grouped_data.append(
					{
						"sales_stage": sales_stage,
						based_on: _based_on,
						"amount": sum(flt(r["amount"]) for r in rows),
					}
				)

			self.query_result = self.grouped_data

	def set_missing_sales_stage(self):
		for row in self.query_result:
			row["sales_stage"] = row["sales_stage"] or NO_SALES_STAGE

	def get_rows(self):
		self.data = []
		self.get_formatted_data()

		for based_on, data in self.formatted_data.items():
			row_based_on = {
				"Opportunity Owner": "opportunity_owner",
				"Source": "utm_source",
				"Opportunity Type": "opportunity_type",
			}[self.filters.get("based_on")]

			row = {row_based_on: based_on}

			for d in self.query_result:
				sales_stage = d.get("sales_stage")
				row[sales_stage] = data.get(sales_stage)

			self.data.append(row)

	def get_formatted_data(self):
		self.formatted_data = frappe._dict()

		for d in self.query_result:
			data_based_on = {"Number": "count", "Amount": "amount"}[self.filters.get("data_based_on")]

			based_on = {
				"Opportunity Owner": "_assign",
				"Source": "utm_source",
				"Opportunity Type": "opportunity_type",
			}[self.filters.get("based_on")]

			if self.filters.get("based_on") == "Opportunity Owner":
				value = d.get(based_on)
				if not value or value in ["[]", "null", "Not Assigned"]:
					assignments = ["Not Assigned"]
				else:
					try:
						assignments = json.loads(value)
					except json.JSONDecodeError:
						assignments = ["Not Assigned"]

				sales_stage = d.get("sales_stage")
				count = d.get(data_based_on)

				if assignments:
					if len(assignments) > 1:
						for assigned_to in assignments:
							self.set_formatted_data_based_on_sales_stage(assigned_to, sales_stage, count)
					else:
						assigned_to = assignments[0]
						self.set_formatted_data_based_on_sales_stage(assigned_to, sales_stage, count)
			else:
				value = d.get(based_on)
				sales_stage = d.get("sales_stage")
				count = d.get(data_based_on)
				self.set_formatted_data_based_on_sales_stage(value, sales_stage, count)

	def set_formatted_data_based_on_sales_stage(self, based_on, sales_stage, count):
		self.formatted_data.setdefault(based_on, frappe._dict()).setdefault(sales_stage, 0)
		self.formatted_data[based_on][sales_stage] += count

	def get_conditions(self):
		filters = []

		if self.filters.get("company"):
			filters.append({"company": self.filters.get("company")})

		if self.filters.get("opportunity_type"):
			filters.append({"opportunity_type": self.filters.get("opportunity_type")})

		if self.filters.get("opportunity_source"):
			filters.append({"utm_source": self.filters.get("opportunity_source")})

		if self.filters.get("status"):
			filters.append({"status": ("in", self.filters.get("status"))})

		if self.filters.get("from_date") and self.filters.get("to_date"):
			filters.append(
				["transaction_date", "between", [self.filters.get("from_date"), self.filters.get("to_date")]]
			)

		return filters

	def get_chart_data(self):
		datasets = []
		values = [0] * len(self.sales_stage_list)

		options = {"Number": "count", "Amount": "amount"}[self.filters.get("data_based_on")]

		for data in self.query_result:
			for count in range(len(self.sales_stage_list)):
				if data["sales_stage"] == self.sales_stage_list[count]:
					values[count] = values[count] + data[options]

		datasets.append({"name": options, "values": values})
		self.chart = {"data": {"labels": self.sales_stage_list, "datasets": datasets}, "type": "line"}

	def convert_to_base_currency(self):
		company_currency = erpnext.get_company_currency(self.filters.company)
		for row in self.query_result:
			row["amount"] = flt(row["amount"]) * self.get_conversion_rate(row, company_currency)

	def get_conversion_rate(self, row: dict, company_currency: str) -> float:
		if flt(row.conversion_rate):
			return flt(row.conversion_rate)
		if not row.currency or row.currency == company_currency:
			return 1.0
		# opportunities saved while no exchange rate was available
		return flt(get_exchange_rate(row.currency, company_currency, row.transaction_date))
