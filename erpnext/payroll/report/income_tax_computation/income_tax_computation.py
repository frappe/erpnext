# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, flt, getdate, rounded

from erpnext.payroll.doctype.payroll_entry.payroll_entry import get_start_end_dates
from erpnext.payroll.doctype.salary_slip.salary_slip import calculate_tax_by_tax_slab


def execute(filters=None):
	return IncomeTaxComputationReport(filters).run()


class IncomeTaxComputationReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.columns = []
		self.data = []
		self.employees = frappe._dict()
		self.payroll_period_start_date = None
		self.payroll_period_end_date = None
		if self.filters.payroll_period:
			self.payroll_period_start_date, self.payroll_period_end_date = frappe.db.get_value(
				"Payroll Period", self.filters.payroll_period, ["start_date", "end_date"]
			)

	def run(self):
		self.get_fixed_columns()
		self.get_data()
		return self.columns, self.data

	def get_data(self):
		self.get_employee_details()
		self.get_future_salary_slips()
		self.get_ctc()
		self.get_tax_exempted_earnings_and_deductions()
		self.get_employee_tax_exemptions()
		self.get_hra()
		self.get_standard_tax_exemption()
		self.get_total_taxable_amount()
		self.get_applicable_tax()
		self.get_total_deducted_tax()
		self.get_payable_tax()

		self.data = list(self.employees.values())

	def get_employee_details(self):
		filters, or_filters = self.get_employee_filters()
		fields = [
			"name as employee",
			"employee_name",
			"department",
			"designation",
			"date_of_joining",
			"relieving_date",
		]

		employees = frappe.get_all("Employee", filters=filters, or_filters=or_filters, fields=fields)
		ss_assignments = self.get_ss_assignments([d.employee for d in employees])

		for d in employees:
			if d.employee in list(ss_assignments.keys()):
				d.update(ss_assignments[d.employee])
				self.employees.setdefault(d.employee, d)

		if not self.employees:
			frappe.throw(_("No employees found with selected filters and active salary structure"))

	def get_employee_filters(self):
		filters = {"company": self.filters.company}
		or_filters = {
			"status": "Active",
			"relieving_date": ["between", [self.payroll_period_start_date, self.payroll_period_end_date]],
		}
		if self.filters.employee:
			filters = {"name": self.filters.employee}
		elif self.filters.department:
			filters.update({"department": self.filters.department})

		return filters, or_filters

	def get_ss_assignments(self, employees):
		ss_assignments = frappe.get_all(
			"Salary Structure Assignment",
			filters={
				"employee": ["in", employees],
				"docstatus": 1,
				"salary_structure": ["is", "set"],
				"income_tax_slab": ["is", "set"],
			},
			fields=["employee", "income_tax_slab", "salary_structure"],
			order_by="from_date desc",
		)

		employee_ss_assignments = frappe._dict()
		for d in ss_assignments:
			if d.employee not in list(employee_ss_assignments.keys()):
				tax_slab = frappe.get_cached_value(
					"Income Tax Slab", d.income_tax_slab, ["allow_tax_exemption", "disabled"], as_dict=1
				)

				if tax_slab and not tax_slab.disabled:
					employee_ss_assignments.setdefault(
						d.employee,
						{
							"salary_structure": d.salary_structure,
							"income_tax_slab": d.income_tax_slab,
							"allow_tax_exemption": tax_slab.allow_tax_exemption,
						},
					)
		return employee_ss_assignments

	def get_future_salary_slips(self):
		self.future_salary_slips = frappe._dict()
		for employee in list(self.employees.keys()):
			last_ss = self.get_last_salary_slip(employee)
			if last_ss and last_ss.end_date == self.payroll_period_end_date:
				continue

			relieving_date = self.employees[employee].get("relieving_date", "")
			if last_ss:
				ss_start_date = add_days(last_ss.end_date, 1)
			else:
				ss_start_date = self.payroll_period_start_date
				last_ss = frappe._dict(
					{
						"payroll_frequency": "Monthly",
						"salary_structure": self.employees[employee].get("salary_structure"),
					}
				)

			while getdate(ss_start_date) < getdate(self.payroll_period_end_date) and (
				not relieving_date or getdate(ss_start_date) < relieving_date
			):
				ss_end_date = get_start_end_dates(last_ss.payroll_frequency, ss_start_date).end_date

				ss = frappe.new_doc("Salary Slip")
				ss.employee = employee
				ss.start_date = ss_start_date
				ss.end_date = ss_end_date
				ss.salary_structure = last_ss.salary_structure
				ss.payroll_frequency = last_ss.payroll_frequency
				ss.company = self.filters.company
				try:
					ss.process_salary_structure(for_preview=1)
					self.future_salary_slips.setdefault(employee, []).append(ss.as_dict())
				except Exception:
					break

				ss_start_date = add_days(ss_end_date, 1)

	def get_last_salary_slip(self, employee):
		last_salary_slip = frappe.db.get_value(
			"Salary Slip",
			{
				"employee": employee,
				"docstatus": 1,
				"start_date": ["between", [self.payroll_period_start_date, self.payroll_period_end_date]],
			},
			["start_date", "end_date", "salary_structure", "payroll_frequency"],
			order_by="start_date desc",
			as_dict=1,
		)

		return last_salary_slip

	def get_ctc(self):
		# Get total earnings from existing salary slip
		ss = frappe.qb.DocType("Salary Slip")
		existing_ss = frappe._dict(
			(
				frappe.qb.from_(ss)
				.select(ss.employee, Sum(ss.base_gross_pay).as_("amount"))
				.where(ss.docstatus == 1)
				.where(ss.employee.isin(list(self.employees.keys())))
				.where(ss.start_date >= self.payroll_period_start_date)
				.where(ss.end_date <= self.payroll_period_end_date)
				.groupby(ss.employee)
			).run()
		)

		for employee in list(self.employees.keys()):
			future_ss_earnings = self.get_future_earnings(employee)
			ctc = flt(existing_ss.get(employee)) + future_ss_earnings

			self.employees[employee].setdefault("ctc", ctc)

	def get_future_earnings(self, employee):
		future_earnings = 0.0
		for ss in self.future_salary_slips.get(employee, []):
			future_earnings += flt(ss.base_gross_pay)

		return future_earnings

	def get_tax_exempted_earnings_and_deductions(self):
		tax_exempted_components = self.get_tax_exempted_components()

		# Get component totals from existing salary slips
		ss = frappe.qb.DocType("Salary Slip")
		ss_comps = frappe.qb.DocType("Salary Detail")

		records = (
			frappe.qb.from_(ss)
			.inner_join(ss_comps)
			.on(ss.name == ss_comps.parent)
			.select(ss.name, ss.employee, ss_comps.salary_component, Sum(ss_comps.amount).as_("amount"))
			.where(ss.docstatus == 1)
			.where(ss.employee.isin(list(self.employees.keys())))
			.where(ss_comps.salary_component.isin(tax_exempted_components))
			.where(ss.start_date >= self.payroll_period_start_date)
			.where(ss.end_date <= self.payroll_period_end_date)
			.groupby(ss.employee, ss_comps.salary_component)
		).run(as_dict=True)

		existing_ss_exemptions = frappe._dict()
		for d in records:
			existing_ss_exemptions.setdefault(d.employee, {}).setdefault(
				scrub(d.salary_component), d.amount
			)

		for employee in list(self.employees.keys()):
			if not self.employees[employee]["allow_tax_exemption"]:
				continue

			exemptions = existing_ss_exemptions.get(employee, {})
			self.add_exemptions_from_future_salary_slips(employee, exemptions)
			self.employees[employee].update(exemptions)

			total_exemptions = sum(list(exemptions.values()))
			self.add_to_total_exemption(employee, total_exemptions)

	def add_exemptions_from_future_salary_slips(self, employee, exemptions):
		for ss in self.future_salary_slips.get(employee, []):
			for e in ss.earnings:
				if not e.is_tax_applicable:
					exemptions.setdefault(scrub(e.salary_component), 0)
					exemptions[scrub(e.salary_component)] += flt(e.amount)

			for d in ss.deductions:
				if d.exempted_from_income_tax:
					exemptions.setdefault(scrub(d.salary_component), 0)
					exemptions[scrub(d.salary_component)] += flt(d.amount)

		return exemptions

	def get_tax_exempted_components(self):
		# nontaxable earning components
		nontaxable_earning_components = [
			d.name
			for d in frappe.get_all(
				"Salary Component", {"type": "Earning", "is_tax_applicable": 0, "disabled": 0}
			)
		]

		# tax exempted deduction components
		tax_exempted_deduction_components = [
			d.name
			for d in frappe.get_all(
				"Salary Component", {"type": "Deduction", "exempted_from_income_tax": 1, "disabled": 0}
			)
		]

		tax_exempted_components = nontaxable_earning_components + tax_exempted_deduction_components

		# Add columns
		for d in tax_exempted_components:
			self.add_column(d)

		return tax_exempted_components

	def add_to_total_exemption(self, employee, amount):
		self.employees[employee].setdefault("total_exemption", 0)
		self.employees[employee]["total_exemption"] += amount

	def get_employee_tax_exemptions(self):
		# add columns
		exemption_categories = frappe.get_all("Employee Tax Exemption Category", {"is_active": 1})
		for d in exemption_categories:
			self.add_column(d.name)

		self.employees_with_proofs = []
		self.get_tax_exemptions("Employee Tax Exemption Proof Submission")
		if self.filters.consider_tax_exemption_declaration:
			self.get_tax_exemptions("Employee Tax Exemption Declaration")

	def get_tax_exemptions(self, source):
		# Get category-wise exmeptions based on submitted proofs or declarations
		if source == "Employee Tax Exemption Proof Submission":
			child_doctype = "Employee Tax Exemption Proof Submission Detail"
		else:
			child_doctype = "Employee Tax Exemption Declaration Category"

		max_exemptions = self.get_max_exemptions_based_on_category()

		par = frappe.qb.DocType(source)
		child = frappe.qb.DocType(child_doctype)

		records = (
			frappe.qb.from_(par)
			.inner_join(child)
			.on(par.name == child.parent)
			.select(par.employee, child.exemption_category, Sum(child.amount).as_("amount"))
			.where(par.docstatus == 1)
			.where(par.employee.isin(list(self.employees.keys())))
			.where(par.payroll_period == self.filters.payroll_period)
			.groupby(par.employee, child.exemption_category)
		).run(as_dict=True)

		for d in records:
			if not self.employees[d.employee]["allow_tax_exemption"]:
				continue

			if source == "Employee Tax Exemption Declaration" and d.employee in self.employees_with_proofs:
				continue

			amount = flt(d.amount)
			max_eligible_amount = flt(max_exemptions.get(d.exemption_category))
			if max_eligible_amount and amount > max_eligible_amount:
				amount = max_eligible_amount

			self.employees[d.employee].setdefault(scrub(d.exemption_category), amount)
			self.add_to_total_exemption(d.employee, amount)

			if (
				source == "Employee Tax Exemption Proof Submission"
				and d.employee not in self.employees_with_proofs
			):
				self.employees_with_proofs.append(d.employee)

	def get_max_exemptions_based_on_category(self):
		return dict(
			frappe.get_all(
				"Employee Tax Exemption Category",
				filters={"is_active": 1},
				fields=["name", "max_amount"],
				as_list=1,
			)
		)

	def get_hra(self):
		if not frappe.get_meta("Employee Tax Exemption Declaration").has_field("monthly_house_rent"):
			return

		self.add_column("HRA")

		self.employees_with_proofs = []
		self.get_eligible_hra("Employee Tax Exemption Proof Submission")
		if self.filters.consider_tax_exemption_declaration:
			self.get_eligible_hra("Employee Tax Exemption Declaration")

	def get_eligible_hra(self, source):
		if source == "Employee Tax Exemption Proof Submission":
			hra_amount_field = "total_eligible_hra_exemption"
		else:
			hra_amount_field = "annual_hra_exemption"

		records = frappe.get_all(
			source,
			filters={
				"docstatus": 1,
				"employee": ["in", list(self.employees.keys())],
				"payroll_period": self.filters.payroll_period,
			},
			fields=["employee", hra_amount_field],
			as_list=1,
		)

		for d in records:
			if not self.employees[d[0]]["allow_tax_exemption"]:
				continue

			if d[0] not in self.employees_with_proofs:
				self.employees[d[0]].setdefault("hra", d[1])
				self.add_to_total_exemption(d[0], d[1])
				self.employees_with_proofs.append(d[0])

	def get_standard_tax_exemption(self):
		self.add_column("Standard Tax Exemption")

		standard_exemptions_per_slab = dict(
			frappe.get_all(
				"Income Tax Slab",
				filters={"company": self.filters.company, "docstatus": 1, "disabled": 0},
				fields=["name", "standard_tax_exemption_amount"],
				as_list=1,
			)
		)

		for emp, emp_details in self.employees.items():
			if not self.employees[emp]["allow_tax_exemption"]:
				continue

			income_tax_slab = emp_details.get("income_tax_slab")
			standard_exemption = standard_exemptions_per_slab.get(income_tax_slab, 0)
			emp_details["standard_tax_exemption"] = standard_exemption
			self.add_to_total_exemption(emp, standard_exemption)

		self.add_column("Total Exemption")

	def get_total_taxable_amount(self):
		self.add_column("Total Taxable Amount")
		for emp, emp_details in self.employees.items():
			emp_details["total_taxable_amount"] = flt(emp_details.get("ctc")) - flt(
				emp_details.get("total_exemption")
			)

	def get_applicable_tax(self):
		self.add_column("Applicable Tax")

		is_tax_rounded = frappe.db.get_value(
			"Salary Component",
			{"variable_based_on_taxable_salary": 1, "disabled": 0},
			"round_to_the_nearest_integer",
		)

		for emp, emp_details in self.employees.items():
			tax_slab = emp_details.get("income_tax_slab")
			if tax_slab:
				tax_slab = frappe.get_cached_doc("Income Tax Slab", tax_slab)
				employee_dict = frappe.get_doc("Employee", emp).as_dict()
				tax_amount = calculate_tax_by_tax_slab(
					emp_details["total_taxable_amount"], tax_slab, eval_globals=None, eval_locals=employee_dict
				)
			else:
				tax_amount = 0.0

			if is_tax_rounded:
				tax_amount = rounded(tax_amount)
			emp_details["applicable_tax"] = tax_amount

	def get_total_deducted_tax(self):
		self.add_column("Total Tax Deducted")

		ss = frappe.qb.DocType("Salary Slip")
		ss_ded = frappe.qb.DocType("Salary Detail")

		records = (
			frappe.qb.from_(ss)
			.inner_join(ss_ded)
			.on(ss.name == ss_ded.parent)
			.select(ss.employee, Sum(ss_ded.amount).as_("amount"))
			.where(ss.docstatus == 1)
			.where(ss.employee.isin(list(self.employees.keys())))
			.where(ss_ded.parentfield == "deductions")
			.where(ss_ded.variable_based_on_taxable_salary == 1)
			.where(ss.start_date >= self.payroll_period_start_date)
			.where(ss.end_date <= self.payroll_period_end_date)
			.groupby(ss.employee)
		).run(as_dict=True)

		for d in records:
			self.employees[d.employee].setdefault("total_tax_deducted", d.amount)

	def get_payable_tax(self):
		self.add_column("Payable Tax")

		for emp, emp_details in self.employees.items():
			emp_details["payable_tax"] = flt(emp_details.get("applicable_tax")) - flt(
				emp_details.get("total_tax_deducted")
			)

	def add_column(self, label, fieldname=None, fieldtype=None, options=None, width=None):
		col = {
			"label": _(label),
			"fieldname": fieldname or scrub(label),
			"fieldtype": fieldtype or "Currency",
			"options": options,
			"width": width or "140px",
		}
		self.columns.append(col)

	def get_fixed_columns(self):
		self.columns = [
			{
				"label": _("Employee"),
				"fieldname": "employee",
				"fieldtype": "Link",
				"options": "Employee",
				"width": "140px",
			},
			{
				"label": _("Employee Name"),
				"fieldname": "employee_name",
				"fieldtype": "Data",
				"width": "160px",
			},
			{
				"label": _("Department"),
				"fieldname": "department",
				"fieldtype": "Link",
				"options": "Department",
				"width": "140px",
			},
			{
				"label": _("Designation"),
				"fieldname": "designation",
				"fieldtype": "Link",
				"options": "Designation",
				"width": "140px",
			},
			{"label": _("Date of Joining"), "fieldname": "date_of_joining", "fieldtype": "Date"},
			{
				"label": _("Income Tax Slab"),
				"fieldname": "income_tax_slab",
				"fieldtype": "Link",
				"options": "Income Tax Slab",
				"width": "140px",
			},
			{"label": _("CTC"), "fieldname": "ctc", "fieldtype": "Currency", "width": "140px"},
		]
