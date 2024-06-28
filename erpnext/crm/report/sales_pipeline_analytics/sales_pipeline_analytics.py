# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from datetime import date
from itertools import groupby

import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.utils import cint, flt, getdate

from erpnext.setup.utils import get_exchange_rate


def execute(filters=None):
	return SalesPipelineAnalytics(filters).run()


class SalesPipelineAnalytics:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

	def validate_filters(self):
		if not self.filters.from_date:
			frappe.throw(_("From Date is mandatory"))

		if not self.filters.to_date:
			frappe.throw(_("To Date is mandatory"))

	def run(self):
		self.validate_filters()
		self.get_columns()
		self.get_data()
		self.get_chart_data()

		return self.columns, self.data, None, self.chart

	def get_columns(self):
		self.columns = []

		self.set_range_columns()
		self.set_pipeline_based_on_column()

	def set_range_columns(self):
		based_on = {"Number": "Int", "Amount": "Currency"}[self.filters.get("based_on")]

		if self.filters.get("range") == "Monthly":
			month_list = self.get_month_list()

			for month in month_list:
				self.columns.append(
					{"fieldname": month, "fieldtype": based_on, "label": _(month), "width": 200}
				)

		elif self.filters.get("range") == "Quarterly":
			for quarter in range(1, 5):
				self.columns.append(
					{"fieldname": f"Q{quarter}", "fieldtype": based_on, "label": f"Q{quarter}", "width": 200}
				)

	def set_pipeline_based_on_column(self):
		if self.filters.get("pipeline_by") == "Owner":
			self.columns.insert(
				0, {"fieldname": "opportunity_owner", "label": _("Opportunity Owner"), "width": 200}
			)

		elif self.filters.get("pipeline_by") == "Sales Stage":
			self.columns.insert(0, {"fieldname": "sales_stage", "label": _("Sales Stage"), "width": 200})

	def get_fields(self):
		self.based_on = {"Owner": "_assign as opportunity_owner", "Sales Stage": "sales_stage"}[
			self.filters.get("pipeline_by")
		]

		self.data_based_on = {
			"Number": "count(name) as count",
			"Amount": "opportunity_amount as amount",
		}[self.filters.get("based_on")]

		self.group_by_based_on = {"Owner": "_assign", "Sales Stage": "sales_stage"}[
			self.filters.get("pipeline_by")
		]

		self.group_by_period = {
			"Monthly": "month(expected_closing)",
			"Quarterly": "QUARTER(expected_closing)",
		}[self.filters.get("range")]

		self.pipeline_by = {"Owner": "opportunity_owner", "Sales Stage": "sales_stage"}[
			self.filters.get("pipeline_by")
		]

		self.duration = {
			"Monthly": "monthname(expected_closing) as month",
			"Quarterly": "QUARTER(expected_closing) as quarter",
		}[self.filters.get("range")]

		self.period_by = {"Monthly": "month", "Quarterly": "quarter"}[self.filters.get("range")]

	def get_data(self):
		self.get_fields()

		if self.filters.get("based_on") == "Number":
			self.query_result = frappe.db.get_list(
				"Opportunity",
				filters=self.get_conditions(),
				fields=[self.based_on, self.data_based_on, self.duration],
				group_by=f"{self.group_by_based_on},{self.group_by_period}",
				order_by=self.group_by_period,
			)

		if self.filters.get("based_on") == "Amount":
			self.query_result = frappe.db.get_list(
				"Opportunity",
				filters=self.get_conditions(),
				fields=[self.based_on, self.data_based_on, self.duration, "currency"],
			)

			self.convert_to_base_currency()

			self.grouped_data = []

			grouping_key = lambda o: (o.get(self.pipeline_by) or "Not Assigned", o[self.period_by])  # noqa
			for (pipeline_by, period_by), rows in groupby(
				sorted(self.query_result, key=grouping_key), grouping_key
			):
				self.grouped_data.append(
					{
						self.pipeline_by: pipeline_by,
						self.period_by: period_by,
						"amount": sum(flt(r["amount"]) for r in rows),
					}
				)

			self.query_result = self.grouped_data

		self.get_periodic_data()
		self.append_data(self.pipeline_by, self.period_by)

	def get_conditions(self):
		conditions = []

		if self.filters.get("opportunity_source"):
			conditions.append({"utm_source": self.filters.get("opportunity_source")})

		if self.filters.get("opportunity_type"):
			conditions.append({"opportunity_type": self.filters.get("opportunity_type")})

		if self.filters.get("status"):
			conditions.append({"status": self.filters.get("status")})

		if self.filters.get("company"):
			conditions.append({"company": self.filters.get("company")})

		if self.filters.get("from_date") and self.filters.get("to_date"):
			conditions.append(
				["expected_closing", "between", [self.filters.get("from_date"), self.filters.get("to_date")]]
			)

		return conditions

	def get_chart_data(self):
		labels = []
		datasets = []

		self.append_to_dataset(datasets)

		for column in self.columns:
			if column["fieldname"] != "opportunity_owner" and column["fieldname"] != "sales_stage":
				labels.append(_(column["fieldname"]))

		self.chart = {"data": {"labels": labels, "datasets": datasets}, "type": "line"}

		return self.chart

	def get_periodic_data(self):
		self.periodic_data = frappe._dict()

		based_on = {"Number": "count", "Amount": "amount"}[self.filters.get("based_on")]

		pipeline_by = {"Owner": "opportunity_owner", "Sales Stage": "sales_stage"}[
			self.filters.get("pipeline_by")
		]

		frequency = {"Monthly": "month", "Quarterly": "quarter"}[self.filters.get("range")]

		for info in self.query_result:
			if self.filters.get("range") == "Monthly":
				period = info.get(frequency)
			if self.filters.get("range") == "Quarterly":
				period = f'Q{cint(info.get("quarter"))}'

			value = info.get(pipeline_by)
			count_or_amount = info.get(based_on)

			if self.filters.get("pipeline_by") == "Owner":
				if value == "Not Assigned" or value == "[]" or value is None or not value:
					assigned_to = ["Not Assigned"]
				else:
					assigned_to = json.loads(value)
				self.check_for_assigned_to(period, value, count_or_amount, assigned_to, info)

			else:
				self.set_formatted_data(period, value, count_or_amount, None)

	def set_formatted_data(self, period, value, count_or_amount, assigned_to):
		if assigned_to:
			if len(assigned_to) > 1:
				if self.filters.get("assigned_to"):
					for user in assigned_to:
						if self.filters.get("assigned_to") == user:
							value = user
							self.periodic_data.setdefault(value, frappe._dict()).setdefault(period, 0)
							self.periodic_data[value][period] += count_or_amount
				else:
					for user in assigned_to:
						value = user
						self.periodic_data.setdefault(value, frappe._dict()).setdefault(period, 0)
						self.periodic_data[value][period] += count_or_amount
			else:
				value = assigned_to[0]
				self.periodic_data.setdefault(value, frappe._dict()).setdefault(period, 0)
				self.periodic_data[value][period] += count_or_amount

		else:
			self.periodic_data.setdefault(value, frappe._dict()).setdefault(period, 0)
			self.periodic_data[value][period] += count_or_amount

	def check_for_assigned_to(self, period, value, count_or_amount, assigned_to, info):
		if self.filters.get("assigned_to"):
			for data in json.loads(info.get("opportunity_owner") or "[]"):
				if data == self.filters.get("assigned_to"):
					self.set_formatted_data(period, data, count_or_amount, assigned_to)
		else:
			self.set_formatted_data(period, value, count_or_amount, assigned_to)

	def get_month_list(self):
		month_list = []
		current_date = getdate(self.filters.get("from_date"))

		while current_date < getdate(self.filters.get("to_date")):
			month_list.append(current_date.strftime("%B"))
			current_date = current_date + relativedelta(months=1)

		return month_list

	def append_to_dataset(self, datasets):
		range_by = {"Monthly": "month", "Quarterly": "quarter"}[self.filters.get("range")]

		based_on = {"Amount": "amount", "Number": "count"}[self.filters.get("based_on")]

		if self.filters.get("range") == "Quarterly":
			frequency_list = [1, 2, 3, 4]
			count = [0] * 4

		if self.filters.get("range") == "Monthly":
			frequency_list = self.get_month_list()
			count = [0] * 12

		for info in self.query_result:
			for i in range(len(frequency_list)):
				if info[range_by] == frequency_list[i]:
					count[i] = count[i] + info[based_on]
		datasets.append({"name": based_on, "values": count})

	def append_data(self, pipeline_by, period_by):
		self.data = []
		for pipeline, period_data in self.periodic_data.items():
			row = {pipeline_by: pipeline}
			for info in self.query_result:
				if self.filters.get("range") == "Monthly":
					period = info.get(period_by)

				if self.filters.get("range") == "Quarterly":
					period = f"Q{cint(info.get(period_by))}"

				count = period_data.get(period, 0.0)
				row[period] = count

			self.data.append(row)

	def get_default_currency(self):
		company = self.filters.get("company")
		return frappe.db.get_value("Company", company, ["default_currency"])

	def get_currency_rate(self, from_currency, to_currency):
		cacheobj = frappe.cache()

		if cacheobj.get(from_currency):
			return flt(str(cacheobj.get(from_currency), "UTF-8"))

		else:
			value = get_exchange_rate(from_currency, to_currency)
			cacheobj.set(from_currency, value)
			return flt(str(cacheobj.get(from_currency), "UTF-8"))

	def convert_to_base_currency(self):
		default_currency = self.get_default_currency()
		for data in self.query_result:
			if data.get("currency") != default_currency:
				opportunity_currency = data.get("currency")
				value = self.get_currency_rate(opportunity_currency, default_currency)
				data["amount"] = data["amount"] * value
