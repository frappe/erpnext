# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form


class SalesCommission(Document):
	def validate(self):
		self.validate_from_to_dates()
		self.validate_salary_component()
		self.calculate_total_contribution_and_total_commission_amount()

	def validate_from_to_dates(self):
		return super().validate_from_to_dates("from_date", "to_date")

	def validate_salary_component(self):
		if self.pay_via_salary:
			if not frappe.db.get_single_value("Payroll Settings", "salary_component_for_sales_commission"):
				frappe.throw(_("Please set {0} in {1}").format(frappe.bold("Salary Component for Sales Commission"), get_link_to_form("Payroll Settings", "Payroll Settings")))

	def calculate_total_contribution_and_total_commission_amount(self):
		total_contribution, total_commission_amount = 0,0
		for entry in self.contributions:
			total_contribution += entry.contribution_amount
			total_commission_amount += entry.commission_amount

		if self.calculate_commission_manually:
			rate = self.commission_rate
			total_commission_amount = total_contribution * (rate / 100)

		self.total_contribution = total_contribution
		self.total_commission_amount = total_commission_amount

	def on_submit(self):
		if not self.employee:
			frappe.throw(_("No employee is linked to Sales Person: {0}. Please select an employee for {1} to submit this document.").format(frappe.bold(self.sales_person), get_link_to_form("Sales Person", self.sales_person)))
		if self.pay_via_salary:
			self.make_additional_salary()
		else:
			self.make_payment_entry()

	@frappe.whitelist()
	def payout_entry(self, mode_of_payment=None):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
		if mode_of_payment:
			paid_from = get_bank_cash_account(mode_of_payment, self.company).get("account")

		paid_to = frappe.db.get_value("Company", filters={"name":self.company}, fieldname=['default_payable_account'], as_dict=True)['default_payable_account']
		if not paid_to:
			frappe.throw(_("Please set Default Payable Account in {}").format(get_link_to_form("Company", self.company)))
		if self.pay_via_salary:
			self.make_additional_salary()
		else:
			self.make_payment_entry(mode_of_payment, paid_from, paid_to)


	def make_additional_salary(self):
		doc = frappe.new_doc("Additional Salary")
		doc.employee = self.employee
		doc.company = self.company
		doc.salary_component = frappe.db.get_single_value("Payroll Settings", "salary_component_for_sales_commission")
		doc.payroll_date = self.to_date
		doc.amount = self.total_commission_amount
		doc.ref_doctype = self.doctype
		doc.ref_docname = self.name

		doc.submit()

		self.db_set("reference_doctype", "Additional Salary")
		self.db_set("reference_name", doc.name)

	def make_payment_entry(self, mode_of_payment, paid_from, paid_to):
		doc = frappe.new_doc("Payment Entry")
		doc.company = self.company
		doc.payment_type = "Pay"
		doc.mode_of_payment = mode_of_payment
		doc.party_type = "Employee"
		doc.party = self.employee
		doc.paid_from = paid_from
		doc.paid_to = paid_to
		doc.paid_amount = self.total_commission_amount
		doc.received_amount = self.total_commission_amount
		doc.source_exchange_rate = 1
		doc.target_exchange_rate = 1
		doc.set("references", [])
		self.add_references(doc)
		doc.submit()

		self.db_set("reference_doctype", "Payment Entry")
		self.db_set("reference_name", doc.name)

	def add_references(self, doc):
		reference = {}
		reference['reference_doctype'] = "Sales Commission"
		reference['reference_name'] = self.name
		reference['due_date'] = self.to_date
		reference['total_amount'] = self.total_commission_amount
		reference['outstanding_amount'] = self.total_commission_amount
		reference['allocated_amount'] = self.total_commission_amount
		doc.append("references", reference)