# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import add_years, cint, flt, getdate

import erpnext
from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses


def execute(filters=None):
	return ForecastingReport(filters).execute_report()


class ExponentialSmoothingForecast:
	def forecast_future_data(self):
		for _key, value in self.period_wise_data.items():
			forecast_data = []
			for period in self.period_list:
				forecast_key = "forecast_" + period.key

				if value.get(period.key) and not forecast_data:
					value[forecast_key] = flt(value.get("avg", 0)) or flt(value.get(period.key))

				elif forecast_data:
					previous_period_data = forecast_data[-1]
					value[forecast_key] = previous_period_data[1] + flt(self.filters.smoothing_constant) * (
						flt(previous_period_data[0]) - flt(previous_period_data[1])
					)

				if value.get(forecast_key):
					# will be use to forecaset next period
					forecast_data.append([value.get(period.key), value.get(forecast_key)])


class ForecastingReport(ExponentialSmoothingForecast):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.data = []
		self.doctype = self.filters.based_on_document
		self.child_doctype = self.doctype + " Item"
		self.based_on_field = "qty" if self.filters.based_on_field == "Qty" else "amount"
		self.fieldtype = "Float" if self.based_on_field == "qty" else "Currency"
		self.company_currency = erpnext.get_company_currency(self.filters.company)

	def execute_report(self):
		self.prepare_periodical_data()
		self.forecast_future_data()
		self.prepare_final_data()
		self.add_total()

		columns = self.get_columns()
		charts = self.get_chart_data()
		summary_data = self.get_summary_data()

		return columns, self.data, None, charts, summary_data

	def prepare_periodical_data(self):
		self.period_wise_data = {}

		from_date = add_years(self.filters.from_date, cint(self.filters.no_of_years) * -1)
		self.period_list = get_period_list(
			from_date,
			self.filters.to_date,
			from_date,
			self.filters.to_date,
			"Date Range",
			self.filters.periodicity,
			ignore_fiscal_year=True,
		)

		order_data = self.get_data_for_forecast() or []

		for entry in order_data:
			key = (entry.item_code, entry.warehouse)
			if key not in self.period_wise_data:
				self.period_wise_data[key] = entry

			period_data = self.period_wise_data[key]
			for period in self.period_list:
				# check if posting date is within the period
				if entry.posting_date >= period.from_date and entry.posting_date <= period.to_date:
					period_data[period.key] = period_data.get(period.key, 0.0) + flt(
						entry.get(self.based_on_field)
					)

		for value in self.period_wise_data.values():
			list_of_period_value = [value.get(p.key, 0) for p in self.period_list]

			if list_of_period_value:
				total_qty = [1 for d in list_of_period_value if d]
				if total_qty:
					value["avg"] = flt(sum(list_of_period_value)) / flt(sum(total_qty))

	def get_data_for_forecast(self):
		parent = frappe.qb.DocType(self.doctype)
		child = frappe.qb.DocType(self.child_doctype)

		date_field = (
			"posting_date" if self.doctype in ("Delivery Note", "Sales Invoice") else "transaction_date"
		)

		query = (
			frappe.qb.from_(parent)
			.from_(child)
			.select(
				parent[date_field].as_("posting_date"),
				child.item_code,
				child.warehouse,
				child.item_name,
				child.stock_qty.as_("qty"),
				child.base_amount.as_("amount"),
			)
			.where(
				(parent.docstatus == 1)
				& (parent.name == child.parent)
				& (parent[date_field] < self.filters.from_date)
				& (parent.company == self.filters.company)
			)
		)

		if self.filters.item_code:
			query = query.where(child.item_code == self.filters.item_code)

		if self.filters.warehouse:
			warehouses = get_child_warehouses(self.filters.warehouse) or []
			query = query.where(child.warehouse.isin(warehouses))

		return query.run(as_dict=True)

	def prepare_final_data(self):
		self.data = []

		if not self.period_wise_data:
			return

		for key in self.period_wise_data:
			self.data.append(self.period_wise_data.get(key))

	def add_total(self):
		if not self.data:
			return

		total_row = {"item_code": _("Total Quantity")}

		for value in self.data:
			for period in self.period_list:
				forecast_key = "forecast_" + period.key
				if forecast_key not in total_row:
					total_row.setdefault(forecast_key, 0.0)

				if period.key not in total_row:
					total_row.setdefault(period.key, 0.0)

				total_row[forecast_key] += value.get(forecast_key, 0.0)
				total_row[period.key] += value.get(period.key, 0.0)

		self.data.append(total_row)

	def get_columns(self):
		columns = [
			{
				"label": _("Item Code"),
				"options": "Item",
				"fieldname": "item_code",
				"fieldtype": "Link",
				"width": 130,
			},
			{
				"label": _("Warehouse"),
				"options": "Warehouse",
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"width": 130,
			},
		]

		width = 180 if self.filters.periodicity in ["Yearly", "Half-Yearly", "Quarterly"] else 100
		for period in self.period_list:
			if self.filters.periodicity in [
				"Yearly",
				"Half-Yearly",
				"Quarterly",
			] or period.from_date >= getdate(self.filters.from_date):
				forecast_key = period.key
				label = _(period.label)
				if period.from_date >= getdate(self.filters.from_date):
					forecast_key = "forecast_" + period.key
					label = _(period.label) + " " + _("(Forecast)")

				columns.append(
					{
						"label": label,
						"fieldname": forecast_key,
						"fieldtype": self.fieldtype,
						"width": width,
						"default": 0.0,
					}
				)

		return columns

	def get_chart_data(self):
		if not self.data:
			return

		labels = []
		self.total_demand = []
		self.total_forecast = []
		self.total_history_forecast = []
		self.total_future_forecast = []

		for period in self.period_list:
			forecast_key = "forecast_" + period.key

			labels.append(_(period.label))

			if period.from_date < getdate(self.filters.from_date):
				self.total_demand.append(self.data[-1].get(period.key, 0))
				self.total_history_forecast.append(self.data[-1].get(forecast_key, 0))
			else:
				self.total_future_forecast.append(self.data[-1].get(forecast_key, 0))

			self.total_forecast.append(self.data[-1].get(forecast_key, 0))

		return {
			"data": {
				"labels": labels,
				"datasets": [
					{"name": "Demand", "values": self.total_demand},
					{"name": "Forecast", "values": self.total_forecast},
				],
			},
			"type": "line",
		}

	def get_summary_data(self):
		if not self.data:
			return

		return [
			{
				"value": sum(self.total_demand),
				"label": _("Total Demand (Past Data)"),
				"currency": self.company_currency,
				"datatype": self.fieldtype,
			},
			{
				"value": sum(self.total_history_forecast),
				"label": _("Total Forecast (Past Data)"),
				"currency": self.company_currency,
				"datatype": self.fieldtype,
			},
			{
				"value": sum(self.total_future_forecast),
				"indicator": "Green",
				"label": _("Total Forecast (Future Data)"),
				"currency": self.company_currency,
				"datatype": self.fieldtype,
			},
		]
