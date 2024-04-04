# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _, scrub
from frappe.utils import add_days, add_to_date, flt, getdate

from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
	return IssueAnalytics(filters).run()


class IssueAnalytics:
	def __init__(self, filters=None):
		"""Issue Analytics Report"""
		self.filters = frappe._dict(filters or {})
		self.get_period_date_ranges()

	def run(self):
		self.get_columns()
		self.get_data()
		self.get_chart_data()

		return self.columns, self.data, None, self.chart

	def get_columns(self):
		self.columns = []

		if self.filters.based_on == "Customer":
			self.columns.append(
				{
					"label": _("Customer"),
					"options": "Customer",
					"fieldname": "customer",
					"fieldtype": "Link",
					"width": 200,
				}
			)

		elif self.filters.based_on == "Assigned To":
			self.columns.append(
				{
					"label": _("User"),
					"fieldname": "user",
					"fieldtype": "Link",
					"options": "User",
					"width": 200,
				}
			)

		elif self.filters.based_on == "Issue Type":
			self.columns.append(
				{
					"label": _("Issue Type"),
					"fieldname": "issue_type",
					"fieldtype": "Link",
					"options": "Issue Type",
					"width": 200,
				}
			)

		elif self.filters.based_on == "Issue Priority":
			self.columns.append(
				{
					"label": _("Issue Priority"),
					"fieldname": "priority",
					"fieldtype": "Link",
					"options": "Issue Priority",
					"width": 200,
				}
			)

		for end_date in self.periodic_daterange:
			period = self.get_period(end_date)
			self.columns.append(
				{"label": _(period), "fieldname": scrub(period), "fieldtype": "Int", "width": 120}
			)

		self.columns.append({"label": _("Total"), "fieldname": "total", "fieldtype": "Int", "width": 120})

	def get_data(self):
		self.get_issues()
		self.get_rows()

	def get_period(self, date):
		months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

		if self.filters.range == "Weekly":
			period = "Week " + str(date.isocalendar()[1])
		elif self.filters.range == "Monthly":
			period = str(months[date.month - 1])
		elif self.filters.range == "Quarterly":
			period = "Quarter " + str(((date.month - 1) // 3) + 1)
		else:
			year = get_fiscal_year(date, self.filters.company)
			period = str(year[0])

		if (
			getdate(self.filters.from_date).year != getdate(self.filters.to_date).year
			and self.filters.range != "Yearly"
		):
			period += " " + str(date.year)

		return period

	def get_period_date_ranges(self):
		from dateutil.relativedelta import MO, relativedelta

		from_date, to_date = getdate(self.filters.from_date), getdate(self.filters.to_date)

		increment = {"Monthly": 1, "Quarterly": 3, "Half-Yearly": 6, "Yearly": 12}.get(self.filters.range, 1)

		if self.filters.range in ["Monthly", "Quarterly"]:
			from_date = from_date.replace(day=1)
		elif self.filters.range == "Yearly":
			from_date = get_fiscal_year(from_date)[1]
		else:
			from_date = from_date + relativedelta(from_date, weekday=MO(-1))

		self.periodic_daterange = []
		for _dummy in range(1, 53):
			if self.filters.range == "Weekly":
				period_end_date = add_days(from_date, 6)
			else:
				period_end_date = add_to_date(from_date, months=increment, days=-1)

			if period_end_date > to_date:
				period_end_date = to_date

			self.periodic_daterange.append(period_end_date)

			from_date = add_days(period_end_date, 1)
			if period_end_date == to_date:
				break

	def get_issues(self):
		filters = self.get_common_filters()
		self.field_map = {
			"Customer": "customer",
			"Issue Type": "issue_type",
			"Issue Priority": "priority",
			"Assigned To": "_assign",
		}

		self.entries = frappe.db.get_all(
			"Issue",
			fields=[self.field_map.get(self.filters.based_on), "name", "opening_date"],
			filters=filters,
		)

	def get_common_filters(self):
		filters = {}
		filters["opening_date"] = ("between", [self.filters.from_date, self.filters.to_date])

		if self.filters.get("assigned_to"):
			filters["_assign"] = ("like", "%" + self.filters.get("assigned_to") + "%")

		for entry in ["company", "status", "priority", "customer", "project"]:
			if self.filters.get(entry):
				filters[entry] = self.filters.get(entry)

		return filters

	def get_rows(self):
		self.data = []
		self.get_periodic_data()

		for entity, period_data in self.issue_periodic_data.items():
			if self.filters.based_on == "Customer":
				row = {"customer": entity}
			elif self.filters.based_on == "Assigned To":
				row = {"user": entity}
			elif self.filters.based_on == "Issue Type":
				row = {"issue_type": entity}
			elif self.filters.based_on == "Issue Priority":
				row = {"priority": entity}

			total = 0
			for end_date in self.periodic_daterange:
				period = self.get_period(end_date)
				amount = flt(period_data.get(period, 0.0))
				row[scrub(period)] = amount
				total += amount

			row["total"] = total

			self.data.append(row)

	def get_periodic_data(self):
		self.issue_periodic_data = frappe._dict()

		for d in self.entries:
			period = self.get_period(d.get("opening_date"))

			if self.filters.based_on == "Assigned To":
				if d._assign:
					for entry in json.loads(d._assign):
						self.issue_periodic_data.setdefault(entry, frappe._dict()).setdefault(period, 0.0)
						self.issue_periodic_data[entry][period] += 1

			else:
				field = self.field_map.get(self.filters.based_on)
				value = d.get(field)
				if not value:
					value = _("Not Specified")

				self.issue_periodic_data.setdefault(value, frappe._dict()).setdefault(period, 0.0)
				self.issue_periodic_data[value][period] += 1

	def get_chart_data(self):
		length = len(self.columns)
		labels = [d.get("label") for d in self.columns[1 : length - 1]]
		self.chart = {"data": {"labels": labels, "datasets": []}, "type": "line"}
