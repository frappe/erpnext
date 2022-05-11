# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	return EmployeeHoursReport(filters).run()


class EmployeeHoursReport:
	"""Employee Hours Utilization Report Based On Timesheet"""

	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

		self.from_date = getdate(self.filters.from_date)
		self.to_date = getdate(self.filters.to_date)

		self.validate_dates()
		self.validate_standard_working_hours()

	def validate_dates(self):
		self.day_span = (self.to_date - self.from_date).days

		if self.day_span <= 0:
			frappe.throw(_("From Date must come before To Date"))

	def validate_standard_working_hours(self):
		self.standard_working_hours = frappe.db.get_single_value("HR Settings", "standard_working_hours")
		if not self.standard_working_hours:
			msg = _(
				"The metrics for this report are calculated based on the Standard Working Hours. Please set {0} in {1}."
			).format(
				frappe.bold("Standard Working Hours"),
				frappe.utils.get_link_to_form("HR Settings", "HR Settings"),
			)

			frappe.throw(msg)

	def run(self):
		self.generate_columns()
		self.generate_data()
		self.generate_report_summary()
		self.generate_chart_data()

		return self.columns, self.data, None, self.chart, self.report_summary

	def generate_columns(self):
		self.columns = [
			{
				"label": _("Employee"),
				"options": "Employee",
				"fieldname": "employee",
				"fieldtype": "Link",
				"width": 230,
			},
			{
				"label": _("Department"),
				"options": "Department",
				"fieldname": "department",
				"fieldtype": "Link",
				"width": 120,
			},
			{"label": _("Total Hours (T)"), "fieldname": "total_hours", "fieldtype": "Float", "width": 120},
			{
				"label": _("Billed Hours (B)"),
				"fieldname": "billed_hours",
				"fieldtype": "Float",
				"width": 170,
			},
			{
				"label": _("Non-Billed Hours (NB)"),
				"fieldname": "non_billed_hours",
				"fieldtype": "Float",
				"width": 170,
			},
			{
				"label": _("Untracked Hours (U)"),
				"fieldname": "untracked_hours",
				"fieldtype": "Float",
				"width": 170,
			},
			{
				"label": _("% Utilization (B + NB) / T"),
				"fieldname": "per_util",
				"fieldtype": "Percentage",
				"width": 200,
			},
			{
				"label": _("% Utilization (B / T)"),
				"fieldname": "per_util_billed_only",
				"fieldtype": "Percentage",
				"width": 200,
			},
		]

	def generate_data(self):
		self.generate_filtered_time_logs()
		self.generate_stats_by_employee()
		self.set_employee_department_and_name()

		if self.filters.department:
			self.filter_stats_by_department()

		self.calculate_utilizations()

		self.data = []

		for emp, data in self.stats_by_employee.items():
			row = frappe._dict()
			row["employee"] = emp
			row.update(data)
			self.data.append(row)

		#  Sort by descending order of percentage utilization
		self.data.sort(key=lambda x: x["per_util"], reverse=True)

	def filter_stats_by_department(self):
		filtered_data = frappe._dict()
		for emp, data in self.stats_by_employee.items():
			if data["department"] == self.filters.department:
				filtered_data[emp] = data

		# Update stats
		self.stats_by_employee = filtered_data

	def generate_filtered_time_logs(self):
		additional_filters = ""

		filter_fields = ["employee", "project", "company"]

		for field in filter_fields:
			if self.filters.get(field):
				if field == "project":
					additional_filters += f"AND ttd.{field} = '{self.filters.get(field)}'"
				else:
					additional_filters += f"AND tt.{field} = '{self.filters.get(field)}'"

		self.filtered_time_logs = frappe.db.sql(
			"""
			SELECT tt.employee AS employee, ttd.hours AS hours, ttd.is_billable AS is_billable, ttd.project AS project
			FROM `tabTimesheet Detail` AS ttd
			JOIN `tabTimesheet` AS tt
				ON ttd.parent = tt.name
			WHERE tt.employee IS NOT NULL
			AND tt.start_date BETWEEN '{0}' AND '{1}'
			AND tt.end_date BETWEEN '{0}' AND '{1}'
			{2}
		""".format(
				self.filters.from_date, self.filters.to_date, additional_filters
			)
		)

	def generate_stats_by_employee(self):
		self.stats_by_employee = frappe._dict()

		for emp, hours, is_billable, project in self.filtered_time_logs:
			self.stats_by_employee.setdefault(emp, frappe._dict()).setdefault("billed_hours", 0.0)

			self.stats_by_employee[emp].setdefault("non_billed_hours", 0.0)

			if is_billable:
				self.stats_by_employee[emp]["billed_hours"] += flt(hours, 2)
			else:
				self.stats_by_employee[emp]["non_billed_hours"] += flt(hours, 2)

	def set_employee_department_and_name(self):
		for emp in self.stats_by_employee:
			emp_name = frappe.db.get_value("Employee", emp, "employee_name")
			emp_dept = frappe.db.get_value("Employee", emp, "department")

			self.stats_by_employee[emp]["department"] = emp_dept
			self.stats_by_employee[emp]["employee_name"] = emp_name

	def calculate_utilizations(self):
		TOTAL_HOURS = flt(self.standard_working_hours * self.day_span, 2)
		for emp, data in self.stats_by_employee.items():
			data["total_hours"] = TOTAL_HOURS
			data["untracked_hours"] = flt(TOTAL_HOURS - data["billed_hours"] - data["non_billed_hours"], 2)

			# To handle overtime edge-case
			if data["untracked_hours"] < 0:
				data["untracked_hours"] = 0.0

			data["per_util"] = flt(
				((data["billed_hours"] + data["non_billed_hours"]) / TOTAL_HOURS) * 100, 2
			)
			data["per_util_billed_only"] = flt((data["billed_hours"] / TOTAL_HOURS) * 100, 2)

	def generate_report_summary(self):
		self.report_summary = []

		if not self.data:
			return

		avg_utilization = 0.0
		avg_utilization_billed_only = 0.0
		total_billed, total_non_billed = 0.0, 0.0
		total_untracked = 0.0

		for row in self.data:
			avg_utilization += row["per_util"]
			avg_utilization_billed_only += row["per_util_billed_only"]
			total_billed += row["billed_hours"]
			total_non_billed += row["non_billed_hours"]
			total_untracked += row["untracked_hours"]

		avg_utilization /= len(self.data)
		avg_utilization = flt(avg_utilization, 2)

		avg_utilization_billed_only /= len(self.data)
		avg_utilization_billed_only = flt(avg_utilization_billed_only, 2)

		THRESHOLD_PERCENTAGE = 70.0
		self.report_summary = [
			{
				"value": f"{avg_utilization}%",
				"indicator": "Red" if avg_utilization < THRESHOLD_PERCENTAGE else "Green",
				"label": _("Avg Utilization"),
				"datatype": "Percentage",
			},
			{
				"value": f"{avg_utilization_billed_only}%",
				"indicator": "Red" if avg_utilization_billed_only < THRESHOLD_PERCENTAGE else "Green",
				"label": _("Avg Utilization (Billed Only)"),
				"datatype": "Percentage",
			},
			{"value": total_billed, "label": _("Total Billed Hours"), "datatype": "Float"},
			{"value": total_non_billed, "label": _("Total Non-Billed Hours"), "datatype": "Float"},
		]

	def generate_chart_data(self):
		self.chart = {}

		labels = []
		billed_hours = []
		non_billed_hours = []
		untracked_hours = []

		for row in self.data:
			labels.append(row.get("employee_name"))
			billed_hours.append(row.get("billed_hours"))
			non_billed_hours.append(row.get("non_billed_hours"))
			untracked_hours.append(row.get("untracked_hours"))

		self.chart = {
			"data": {
				"labels": labels[:30],
				"datasets": [
					{"name": _("Billed Hours"), "values": billed_hours[:30]},
					{"name": _("Non-Billed Hours"), "values": non_billed_hours[:30]},
					{"name": _("Untracked Hours"), "values": untracked_hours[:30]},
				],
			},
			"type": "bar",
			"barOptions": {"stacked": True},
		}
