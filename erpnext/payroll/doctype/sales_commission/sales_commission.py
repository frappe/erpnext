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

	def validate_amount(self):
		if self.total_commission_amount <= 0:
			frappe.throw(_("Total Commission Amount should be greater than 0"))

	def validate_salary_component(self):
		if self.pay_via_salary and not frappe.db.get_single_value("Payroll Settings", "salary_component_for_sales_commission"):
			frappe.throw(_("Please set {0} in {1}").format(
				frappe.bold("Salary Component for Sales Commission"), get_link_to_form("Payroll Settings", "Payroll Settings")))

	def on_submit(self):
		self.validate_amount()
		self.db_set("status", "Unpaid")

	@frappe.whitelist()
	def add_contributions(self):
		self.set("contributions", [])
		filter_date = "transaction_date" if self.commission_based_on=="Sales Order" else "posting_date"
		records = [entry.name for entry in frappe.db.get_all(
			self.commission_based_on,
			filters={"company": self.company, "docstatus":1, filter_date: ('between', [self.from_date, self.to_date])})]
		sales_persons_details = frappe.get_all(
			"Sales Team", filters={"parent": ['in', records], "sales_person": self.sales_person},
			fields=["sales_person", "commission_rate", "incentives", "allocated_percentage", "allocated_amount", "parent"])
		if sales_persons_details:
			for record in sales_persons_details:
				if add_record(record, self.sales_person):
					record_details = frappe.db.get_value(
						self.commission_based_on, filters={"name": record["parent"]},
						fieldname=["customer", filter_date], as_dict=True)
					contribution = {
						"document_type": self.commission_based_on,
						"order_or_invoice": record["parent"],
						"customer": record_details["customer"],
						"posting_date": record_details[filter_date],
						"contribution_percent": record["allocated_percentage"],
						"contribution_amount": record["allocated_amount"],
						"commission_rate": record["commission_rate"],
						"commission_amount": record["incentives"],
					}
					self.append("contributions", contribution)
		self.calculate_total_contribution_and_total_commission_amount()

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

	@frappe.whitelist()
	def payout_entry(self, mode_of_payment=None):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
		if mode_of_payment:
			paid_from = get_bank_cash_account(mode_of_payment, self.company).get("account")

		paid_to = frappe.db.get_value(
			"Company", filters={"name":self.company},
			fieldname=['default_payable_account'], as_dict=True)['default_payable_account']
		if not paid_to:
			frappe.throw(_("Please set Default Payable Account in {}").format(get_link_to_form("Company", self.company)))
		if self.pay_via_salary:
			self.make_additional_salary()
		else:
			self.make_payment_entry(mode_of_payment, paid_from, paid_to)

	def make_additional_salary(self):
		currency = frappe.get_value("Company", self.company, "default_currency")
		doc = frappe.new_doc("Additional Salary")
		doc.employee = self.employee
		doc.company = self.company
		doc.currency = currency
		doc.salary_component = frappe.db.get_single_value("Payroll Settings", "salary_component_for_sales_commission")
		doc.payroll_date = self.to_date
		doc.amount = self.total_commission_amount
		doc.ref_doctype = self.doctype
		doc.ref_docname = self.name

		doc.submit()

		self.db_set("reference_doctype", "Additional Salary")
		self.db_set("reference_name", doc.name)
		self.db_set("status", "Paid")

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
		self.db_set("status", "Paid")

	def add_references(self, doc):
		reference = {
			'reference_doctype': 'Sales Commission',
			'reference_name': self.name,
			'due_date': self.to_date,
			'total_amount': self.total_commission_amount,
			'outstanding_amount': self.total_commission_amount,
			'allocated_amount': self.total_commission_amount,
		}
		doc.append("references", reference)

def add_record(record, sales_person):
	previous_contibutions = frappe.get_all("Contributions", filters={"order_or_invoice":record["parent"], "docstatus": 1}, fields=["parent"])
	if previous_contibutions:
		for contributions in previous_contibutions:
			if frappe.db.get_value("Sales Commission", {"name":contributions["parent"]}, fieldname=["sales_person"]) == sales_person:
				return False
	return True