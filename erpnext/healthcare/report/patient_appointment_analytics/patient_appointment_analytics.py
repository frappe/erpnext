# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, scrub
from frappe.utils import add_days, add_to_date, flt, getdate
from six import iteritems

from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
	return Analytics(filters).run()


class Analytics(object):
	def __init__(self, filters=None):
		"""Patient Appointment Analytics Report."""
		self.filters = frappe._dict(filters or {})
		self.months = [
			"Jan",
			"Feb",
			"Mar",
			"Apr",
			"May",
			"Jun",
			"Jul",
			"Aug",
			"Sep",
			"Oct",
			"Nov",
			"Dec",
		]
		self.get_period_date_ranges()

	def run(self):
		self.get_columns()
		self.get_data()
		self.get_chart_data()

		return self.columns, self.data, None, self.chart

	def get_period_date_ranges(self):
		from dateutil.relativedelta import MO, relativedelta

		from_date, to_date = getdate(self.filters.from_date), getdate(self.filters.to_date)

		increment = {"Monthly": 1, "Quarterly": 3, "Half-Yearly": 6, "Yearly": 12}.get(
			self.filters.range, 1
		)

		if self.filters.range in ["Monthly", "Quarterly"]:
			from_date = from_date.replace(day=1)
		elif self.filters.range == "Yearly":
			from_date = get_fiscal_year(from_date)[1]
		else:
			from_date = from_date + relativedelta(from_date, weekday=MO(-1))

		self.periodic_daterange = []
		for dummy in range(1, 53):
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

	def get_columns(self):
		self.columns = []

		if self.filters.tree_type == "Healthcare Practitioner":
			self.columns.append(
				{
					"label": _("Healthcare Practitioner"),
					"options": "Healthcare Practitioner",
					"fieldname": "practitioner",
					"fieldtype": "Link",
					"width": 200,
				}
			)

		elif self.filters.tree_type == "Medical Department":
			self.columns.append(
				{
					"label": _("Medical Department"),
					"fieldname": "department",
					"fieldtype": "Link",
					"options": "Medical Department",
					"width": 150,
				}
			)

		for end_date in self.periodic_daterange:
			period = self.get_period(end_date)
			self.columns.append(
				{"label": _(period), "fieldname": scrub(period), "fieldtype": "Int", "width": 120}
			)

		self.columns.append(
			{"label": _("Total"), "fieldname": "total", "fieldtype": "Int", "width": 120}
		)

	def get_data(self):
		if self.filters.tree_type == "Healthcare Practitioner":
			self.get_appointments_based_on_healthcare_practitioner()
			self.get_rows()

		elif self.filters.tree_type == "Medical Department":
			self.get_appointments_based_on_medical_department()
			self.get_rows()

	def get_period(self, appointment_date):
		if self.filters.range == "Weekly":
			period = "Week " + str(appointment_date.isocalendar()[1])
		elif self.filters.range == "Monthly":
			period = str(self.months[appointment_date.month - 1])
		elif self.filters.range == "Quarterly":
			period = "Quarter " + str(((appointment_date.month - 1) // 3) + 1)
		else:
			year = get_fiscal_year(appointment_date, company=self.filters.company)
			period = str(year[0])

		if getdate(self.filters.from_date).year != getdate(self.filters.to_date).year:
			period += " " + str(appointment_date.year)

		return period

	def get_appointments_based_on_healthcare_practitioner(self):
		filters = self.get_common_filters()

		self.entries = frappe.db.get_all(
			"Patient Appointment",
			fields=["appointment_date", "name", "patient", "practitioner"],
			filters=filters,
		)

	def get_appointments_based_on_medical_department(self):
		filters = self.get_common_filters()
		if not filters.get("department"):
			filters["department"] = ("!=", "")

		self.entries = frappe.db.get_all(
			"Patient Appointment",
			fields=["appointment_date", "name", "patient", "practitioner", "department"],
			filters=filters,
		)

	def get_common_filters(self):
		filters = {}
		filters["appointment_date"] = ("between", [self.filters.from_date, self.filters.to_date])
		for entry in ["appointment_type", "practitioner", "department", "status"]:
			if self.filters.get(entry):
				filters[entry] = self.filters.get(entry)

		return filters

	def get_rows(self):
		self.data = []
		self.get_periodic_data()

		for entity, period_data in iteritems(self.appointment_periodic_data):
			if self.filters.tree_type == "Healthcare Practitioner":
				row = {"practitioner": entity}
			elif self.filters.tree_type == "Medical Department":
				row = {"department": entity}

			total = 0
			for end_date in self.periodic_daterange:
				period = self.get_period(end_date)
				amount = flt(period_data.get(period, 0.0))
				row[scrub(period)] = amount
				total += amount

			row["total"] = total

			self.data.append(row)

	def get_periodic_data(self):
		self.appointment_periodic_data = frappe._dict()

		for d in self.entries:
			period = self.get_period(d.get("appointment_date"))
			if self.filters.tree_type == "Healthcare Practitioner":
				self.appointment_periodic_data.setdefault(d.practitioner, frappe._dict()).setdefault(
					period, 0.0
				)
				self.appointment_periodic_data[d.practitioner][period] += 1

			elif self.filters.tree_type == "Medical Department":
				self.appointment_periodic_data.setdefault(d.department, frappe._dict()).setdefault(period, 0.0)
				self.appointment_periodic_data[d.department][period] += 1

	def get_chart_data(self):
		length = len(self.columns)
		labels = [d.get("label") for d in self.columns[1 : length - 1]]
		self.chart = {"data": {"labels": labels, "datasets": []}, "type": "line"}
