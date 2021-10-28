# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form


class ProcessSalesCommission(Document):
	def validate(self):
		self.validate_from_to_dates()
		self.validate_salary_component()

	def validate_from_to_dates(self):
		return super().validate_from_to_dates("from_date", "to_date")

	def validate_salary_component(self):
		if self.pay_via_salary and not frappe.db.get_single_value(
		    "Payroll Settings", "salary_component_for_sales_commission"):
				frappe.throw(_("Please set {0} in {1}").format(
					frappe.bold("Salary Component for Sales Commission"), get_link_to_form("Payroll Settings", "Payroll Settings")))

	def on_submit(self):
		self.process_sales_commission()

	def process_sales_commission(self):
		filter_date = "transaction_date" if self.commission_based_on=="Sales Order" else "posting_date"
		records = [entry.name for entry in frappe.db.get_all(
			self.commission_based_on,
			filters={"company": self.company, "docstatus":1, filter_date: ('between', [self.from_date, self.to_date])})]
		sales_persons_details = frappe.get_all(
			"Sales Team", filters={"parent": ['in', records]},
			fields=["sales_person", "commission_rate", "incentives", "allocated_percentage", "allocated_amount", "parent"])
		if sales_persons_details:
			sales_persons = {e['sales_person'] for e in sales_persons_details}
			sales_persons_list = self.get_sales_persons_list(sales_persons)
			# sales_persons_details_map = self.map_sales_persons_details(sales_persons_list, sales_persons_details)
			self.make_sales_commission_document(sales_persons_list, filter_date)

	def get_sales_persons_list(self, sales_persons):
		sales_persons_list = sales_persons
		if self.department or self.designation or self.branch:
			sales_persons_emp = frappe.get_all("Sales Person", filters= {"name": ["in", sales_persons]}, fields=["employee"], as_dict=True)['employee']
			emp_filters = {"name": ["in", sales_persons_emp], "company": self.company}
			# for field in ["department", "designation", "branch"]:
			if self.department:
				emp_filters["department"] = self.department
			if self.designation:
				emp_filters["designation"] = self.designation
			if self.branch:
				emp_filters["branch"] = self.branch

			sales_persons_list = frappe.get_all("Employee", filters=emp_filters, as_dict=True)
			# for person in sales_persons:
			# 	emp = frappe.db.get_value("Sales Person", filters={"name": person}, fieldname="employee", as_dict=True)['employee']
			# 	if emp:
			# 		employee_details = frappe.db.get_value("Employee", filters={"name": emp}, as_dict=True)
			# 		if self.company != employee_details["company"]:
			# 			sales_persons_list.remove(person)
			# 			continue
			# 		if self.department and self.department != employee_details["department"]:
			# 			sales_persons_list.remove(person)
			# 			continue
			# 		if self.designation and self.designation != employee_details["designation"]:
			# 			sales_persons_list.remove(person)
			# 			continue
			# 		if self.branch and self.branch != employee_details["branch"]:
			# 			sales_persons_list.remove(person)
			# 			continue

		return sales_persons_list

	# def map_sales_persons_details(self, sales_persons, sales_persons_details):
	# 	sales_persons_details_map = {}
	# 	for person in sales_persons:
	# 		sales_persons_details_map[person] = []
	# 		for details in sales_persons_details:
	# 			if details['sales_person'] == person:
	# 				sales_persons_details_map[person].append(details)

	# 	return sales_persons_details_map

	def make_sales_commission_document(self, sales_persons_details_map, filter_date):
		for record in sales_persons_details_map:
			doc = doc = frappe.new_doc("Sales Commission")
			doc.sales_person = record
			doc.from_date = self.from_date
			doc.to_date = self.to_date
			doc.pay_via_salary = self.pay_via_salary
			doc.process_sales_commission_reference = self.name
			doc.add_contributions()
			doc.insert()
			if not frappe.db.get_single_value("Selling Settings", "approval_required_for_sales_commission_payout"):
				doc.reload()
				if self.pay_via_salary and doc.employee:
					if frappe.db.exists('Salary Structure Assignment', {'employee': doc.employee}):
						doc.submit()
						doc.payout_entry()