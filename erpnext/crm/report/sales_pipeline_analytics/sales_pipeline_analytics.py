# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from datetime import date
from itertools import groupby

import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.query_builder.custom import Month, Quarter, Year
from frappe.utils import cint, flt, getdate


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

		if self.filters.based_on == "Amount" and not self.filters.company:
			frappe.throw(_("Company is mandatory when Based On is Amount"))

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

		for period in self.get_periods():
			self.columns.append({**period, "fieldtype": based_on, "width": 200})

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
			"Number": {"COUNT": "*", "as": "count"},
			"Amount": "opportunity_amount as amount",
		}[self.filters.get("based_on")]

		self.group_by_based_on = {"Owner": "_assign", "Sales Stage": "sales_stage"}[
			self.filters.get("pipeline_by")
		]

		opp = frappe.qb.DocType("Opportunity")

		period_function = Month if self.filters.get("range") == "Monthly" else Quarter
		self.period_expressions = [Year(opp.expected_closing), period_function(opp.expected_closing)]
		self.period_fields = [
			self.period_expressions[0].as_("year"),
			self.period_expressions[1].as_("period"),
		]

		self.pipeline_by = {"Owner": "opportunity_owner", "Sales Stage": "sales_stage"}[
			self.filters.get("pipeline_by")
		]

		self.period_by = "period"

	def get_data(self):
		self.get_fields()

		opp = frappe.qb.DocType("Opportunity")
		pipeline_field = opp._assign if self.group_by_based_on == "_assign" else opp.sales_stage

		if self.filters.get("based_on") == "Number":
			# Ask get_query for exactly the grouped columns via `fields`, instead of taking its
			# default un-grouped "name" select and stripping it.
			self.query_result = (
				frappe.qb.get_query(
					"Opportunity",
					filters=self.get_conditions(),
					fields=[
						pipeline_field.as_(self.pipeline_by),
						frappe.query_builder.functions.Count("*").as_("count"),
						*self.period_fields,
					],
					ignore_permissions=False,
				)
				.groupby(pipeline_field, *self.period_expressions)
				.orderby(*self.period_expressions)
				.run(as_dict=True)
			)
			self.set_row_periods()

		if self.filters.get("based_on") == "Amount":
			query = frappe.qb.get_query(
				"Opportunity",
				filters=self.get_conditions(),
				ignore_permissions=False,
			)
			self.query_result = query.select(
				pipeline_field.as_(self.pipeline_by),
				opp.opportunity_amount.as_("amount"),
				*self.period_fields,
				opp.conversion_rate,
			).run(as_dict=True)

			self.set_row_periods()
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
		else:
			conditions.append(["status", "not in", ["Lost", "Closed"]])

		if self.filters.get("company"):
			conditions.append({"company": self.filters.get("company")})

		if self.filters.get("assigned_to"):
			conditions.append(["_assign", "like", f'%"{self.filters.get("assigned_to")}"%'])

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
				labels.append(column["label"])

		self.chart = {"data": {"labels": labels, "datasets": datasets}, "type": "line"}

		return self.chart

	def get_periodic_data(self):
		self.periodic_data = frappe._dict()

		based_on = {"Number": "count", "Amount": "amount"}[self.filters.get("based_on")]

		pipeline_by = {"Owner": "opportunity_owner", "Sales Stage": "sales_stage"}[
			self.filters.get("pipeline_by")
		]

		for info in self.query_result:
			period = info.get(self.period_by)

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

	def get_periods(self) -> list[dict]:
		periods = []
		months_per_period = 1 if self.filters.get("range") == "Monthly" else 3
		current_date = self.get_period_start(getdate(self.filters.get("from_date")), months_per_period)

		while current_date <= getdate(self.filters.get("to_date")):
			periods.append(self.get_period(current_date))
			current_date = current_date + relativedelta(months=months_per_period)

		return periods

	def get_period_start(self, day: date, months_per_period: int) -> date:
		return date(day.year, (day.month - 1) // months_per_period * months_per_period + 1, 1)

	def get_period(self, period_start: date) -> dict:
		if self.filters.get("range") == "Monthly":
			label = f"{_(period_start.strftime('%B'))} {period_start.year}"
			return {"fieldname": period_start.strftime("%B_%Y").lower(), "label": label}

		quarter = (period_start.month - 1) // 3 + 1
		return {"fieldname": f"q{quarter}_{period_start.year}", "label": f"Q{quarter} {period_start.year}"}

	def set_row_periods(self):
		for row in self.query_result:
			month = cint(row.period) if self.filters.get("range") == "Monthly" else cint(row.period) * 3 - 2
			row.period = self.get_period(date(cint(row.year), month, 1))["fieldname"]

	def append_to_dataset(self, datasets):
		based_on = {"Amount": "amount", "Number": "count"}[self.filters.get("based_on")]
		frequency_list = [period["fieldname"] for period in self.get_periods()]
		count = [0] * len(frequency_list)

		for info in self.query_result:
			for i in range(len(frequency_list)):
				if info[self.period_by] == frequency_list[i]:
					count[i] = count[i] + info[based_on]
		datasets.append({"name": based_on, "values": count})

	def append_data(self, pipeline_by, period_by):
		self.data = []
		for pipeline, period_data in self.periodic_data.items():
			row = {pipeline_by: pipeline}
			for info in self.query_result:
				period = info.get(period_by)
				count = period_data.get(period, 0.0)
				row[period] = count

			self.data.append(row)

	def convert_to_base_currency(self):
		for data in self.query_result:
			data["amount"] = flt(data["amount"]) * (flt(data["conversion_rate"]) or 1)
