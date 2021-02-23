# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext

from frappe.utils import flt, cint, cstr
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from six import iteritems

class SalaryStructure(Document):
	def validate(self):
		self.set_missing_values()
		self.validate_amount()
		self.strip_condition_and_formula_fields()
		self.validate_max_benefits_with_flexi()
		self.validate_component_based_on_tax_slab()

	def set_missing_values(self):
		overwritten_fields = ["depends_on_payment_days", "variable_based_on_taxable_salary", "is_tax_applicable", "is_flexible_benefit"]
		overwritten_fields_if_missing = ["amount_based_on_formula", "formula", "amount"]
		for table in ["earnings", "deductions"]:
			for d in self.get(table):
				component_default_value = frappe.db.get_value("Salary Component", cstr(d.salary_component),
					overwritten_fields + overwritten_fields_if_missing, as_dict=1)
				if component_default_value:
					for fieldname in overwritten_fields:
						value = component_default_value.get(fieldname)
						if d.get(fieldname) != value:
							d.set(fieldname, value)

					if not (d.get("amount") or d.get("formula")):
						for fieldname in overwritten_fields_if_missing:
							d.set(fieldname, component_default_value.get(fieldname))

	def validate_component_based_on_tax_slab(self):
		for row in self.deductions:
			if row.variable_based_on_taxable_salary and (row.amount or row.formula):
				frappe.throw(_("Row #{0}: Cannot set amount or formula for Salary Component {1} with Variable Based On Taxable Salary")
					.format(row.idx, row.salary_component))

	def validate_amount(self):
		if flt(self.net_pay) < 0 and self.salary_slip_based_on_timesheet:
			frappe.throw(_("Net pay cannot be negative"))

	def strip_condition_and_formula_fields(self):
		# remove whitespaces from condition and formula fields
		for row in self.earnings:
			row.condition = row.condition.strip() if row.condition else ""
			row.formula = row.formula.strip() if row.formula else ""

		for row in self.deductions:
			row.condition = row.condition.strip() if row.condition else ""
			row.formula = row.formula.strip() if row.formula else ""

	def validate_max_benefits_with_flexi(self):
		have_a_flexi = False
		if self.earnings:
			flexi_amount = 0
			for earning_component in self.earnings:
				if earning_component.is_flexible_benefit == 1:
					have_a_flexi = True
					max_of_component = frappe.db.get_value("Salary Component", earning_component.salary_component, "max_benefit_amount")
					flexi_amount += max_of_component

			if have_a_flexi and flt(self.max_benefits) == 0:
				frappe.throw(_("Max benefits should be greater than zero to dispense benefits"))
			if have_a_flexi and flexi_amount and flt(self.max_benefits) > flexi_amount:
				frappe.throw(_("Total flexible benefit component amount {0} should not be less than max benefits {1}")
					.format(flexi_amount, self.max_benefits))
		if not have_a_flexi and flt(self.max_benefits) > 0:
			frappe.throw(_("Salary Structure should have flexible benefit component(s) to dispense benefit amount"))

	def get_employees(self, **kwargs):
		conditions, values = [], []
		for field, value in kwargs.items():
			if value:
				conditions.append("{0}=%s".format(field))
				values.append(value)

		condition_str = " and " + " and ".join(conditions) if conditions else ""

		employees = frappe.db.sql_list("select name from tabEmployee where status='Active' {condition}"
			.format(condition=condition_str), tuple(values))

		return employees

	@frappe.whitelist()
	def assign_salary_structure(self, grade=None, department=None, designation=None,employee=None,
			payroll_payable_account=None, from_date=None, base=None, variable=None, income_tax_slab=None):
		employees = self.get_employees(company= self.company, grade= grade,department= department,designation= designation,name=employee)

		if employees:
			if len(employees) > 20:
				frappe.enqueue(assign_salary_structure_for_employees, timeout=600,
					employees=employees, salary_structure=self,
					payroll_payable_account=payroll_payable_account,
					from_date=from_date, base=base, variable=variable, income_tax_slab=income_tax_slab)
			else:
				assign_salary_structure_for_employees(employees, self,
					payroll_payable_account=payroll_payable_account, 
					from_date=from_date, base=base, variable=variable, income_tax_slab=income_tax_slab)
		else:
			frappe.msgprint(_("No Employee Found"))



def assign_salary_structure_for_employees(employees, salary_structure, payroll_payable_account=None, from_date=None, base=None, variable=None, income_tax_slab=None):
	salary_structures_assignments = []
	existing_assignments_for = get_existing_assignments(employees, salary_structure, from_date)
	count=0
	for employee in employees:
		if employee in existing_assignments_for:
			continue
		count +=1

		salary_structures_assignment = create_salary_structures_assignment(employee,
			salary_structure, payroll_payable_account, from_date, base, variable, income_tax_slab)
		salary_structures_assignments.append(salary_structures_assignment)
		frappe.publish_progress(count*100/len(set(employees) - set(existing_assignments_for)), title = _("Assigning Structures..."))

	if salary_structures_assignments:
		frappe.msgprint(_("Structures have been assigned successfully"))


def create_salary_structures_assignment(employee, salary_structure, payroll_payable_account, from_date, base, variable, income_tax_slab=None):
	if not payroll_payable_account:
		payroll_payable_account = frappe.db.get_value('Company', salary_structure.company, 'default_payroll_payable_account')
		if not payroll_payable_account:
			frappe.throw(_('Please set "Default Payroll Payable Account" in Company Defaults'))
	payroll_payable_account_currency = frappe.db.get_value('Account',  payroll_payable_account, 'account_currency')
	company_curency = erpnext.get_company_currency(salary_structure.company)
	if payroll_payable_account_currency != salary_structure.currency and payroll_payable_account_currency != company_curency:
		frappe.throw(_("Invalid Payroll Payable Account. The account currency must be {0} or {1}").format(salary_structure.currency, company_curency))

	assignment = frappe.new_doc("Salary Structure Assignment")
	assignment.employee = employee
	assignment.salary_structure = salary_structure.name
	assignment.company = salary_structure.company
	assignment.currency = salary_structure.currency
	assignment.payroll_payable_account = payroll_payable_account
	assignment.from_date = from_date
	assignment.base = base
	assignment.variable = variable
	assignment.income_tax_slab = income_tax_slab
	assignment.save(ignore_permissions = True)
	assignment.submit()
	return assignment.name


def get_existing_assignments(employees, salary_structure, from_date):
	salary_structures_assignments = frappe.db.sql_list("""
		select distinct employee from `tabSalary Structure Assignment`
		where salary_structure=%s and employee in (%s)
		and from_date=%s  and company= %s and docstatus=1
	""" % ('%s', ', '.join(['%s']*len(employees)),'%s', '%s'), [salary_structure.name] + employees+[from_date]+[salary_structure.company])
	if salary_structures_assignments:
		frappe.msgprint(_("Skipping Salary Structure Assignment for the following employees, as Salary Structure Assignment records already exists against them. {0}")
			.format("\n".join(salary_structures_assignments)))
	return salary_structures_assignments

@frappe.whitelist()
def make_salary_slip(source_name, target_doc = None, employee = None, as_print = False, print_format = None, for_preview=0, ignore_permissions=False):
	def postprocess(source, target):
		if employee:
			employee_details = frappe.db.get_value("Employee", employee,
				["employee_name", "branch", "designation", "department", "payroll_cost_center"], as_dict=1)
			target.employee = employee
			target.employee_name = employee_details.employee_name
			target.branch = employee_details.branch
			target.designation = employee_details.designation
			target.department = employee_details.department
			target.payroll_cost_center = employee_details.payroll_cost_center
			if not target.payroll_cost_center and target.department:
				target.payroll_cost_center = frappe.db.get_value("Department", target.department, "payroll_cost_center")

		target.run_method('process_salary_structure', for_preview=for_preview)

	doc = get_mapped_doc("Salary Structure", source_name, {
		"Salary Structure": {
			"doctype": "Salary Slip",
			"field_map": {
				"total_earning": "gross_pay",
				"name": "salary_structure",
				"currency": "currency"
			}
		}
	}, target_doc, postprocess, ignore_child_tables=True, ignore_permissions=ignore_permissions)

	if cint(as_print):
		doc.name = 'Preview for {0}'.format(employee)
		return frappe.get_print(doc.doctype, doc.name, doc = doc, print_format = print_format)
	else:
		return doc


@frappe.whitelist()
def get_employees(salary_structure):
	employees = frappe.get_list('Salary Structure Assignment',
		filters={'salary_structure': salary_structure, 'docstatus': 1}, fields=['employee'])

	if not employees:
		frappe.throw(_("There's no Employee with Salary Structure: {0}. Assign {1} to an Employee to preview Salary Slip").format(
			salary_structure, salary_structure))

	return list(set([d.employee for d in employees]))

