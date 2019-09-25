# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, add_to_date, get_datetime, get_timestamp, get_datetime_str
from six import iteritems

class LoanSecurityPrice(Document):
	def validate(self):
		self.validate_dates()

	def validate_dates(self):

		if self.valid_from > self.valid_upto:
			frappe.throw(_("Valid From Time must be lesser than Valid Upto Time."))

		existing_loan_security = frappe.db.sql(""" SELECT name from `tabLoan Security Price`
			WHERE loan_security = %s AND (valid_from BETWEEN %s and %s OR valid_upto BETWEEN %s and %s) """,
			(self.loan_security, self.valid_from, self.valid_upto, self.valid_from, self.valid_upto))

		if existing_loan_security:
			frappe.throw("Loan Security Price overlapping with {0}".format(existing_loan_security[0][0]))

@frappe.whitelist()
def update_loan_security_price(from_timestamp=None, to_timestamp=None, loan_security_type=None, process_loan_security_price=None):
	if not from_timestamp:
		from_timestamp = get_datetime_str(getdate())

	if not to_timestamp:
		to_timestamp = get_datetime_str(add_to_date(getdate(), hours=24))

	filters = [["valid_upto", "<=", to_timestamp],["valid_from", ">=", from_timestamp]]

	if loan_security_type:
		filters.append(["loan_security_type", "=", loan_security_type])

	loan_security_prices = frappe.get_all("Loan Security Price", fields=["loan_security", "loan_security_price"],
		filters=filters)

	if loan_security_prices:
		for loan_security_price in loan_security_prices:
			frappe.db.set_value("Loan Security", loan_security_price.loan_security, 'loan_security_price', loan_security_price.loan_security_price)

	if not process_loan_security_price:
		process = frappe.new_doc("Process Loan Security Price")
		process.from_time = from_timestamp
		process.to_time = to_timestamp
		if loan_security_type:
			process.loan_security_type = loan_security_type

		process.save()

		process_loan_security_price = process.name

	check_for_ltv_shortfall(process_loan_security_price)

def check_for_ltv_shortfall(process_loan_security_price):

	loan_security_price_map = frappe._dict(frappe.get_all("Loan Security",
		fields=["name", "loan_security_price"], as_list=1))

	loans = frappe.db.sql(""" SELECT l.name, l.loan_amount, l.total_principal_paid, lp.loan_security, lp.haircut, lp.qty
		FROM `tabLoan` l, `tabPledge` lp , `tabLoan Security Pledge`p WHERE lp.parent = p.name and p.loan = l.name and l.docstatus = 1
		and l.is_secured_loan and l.status = 'Disbursed' and p.status in ('Pledged', 'Partially Unpledged')""", as_dict=1)

	loan_security_map = {}

	for loan in loans:
		loan_security_map.setdefault(loan.name, {
			"loan_amount": loan.loan_amount - loan.total_principal_paid,
			"security_value": 0.0
		})

		current_loan_security_amount = loan_security_price_map.get(loan.loan_security, 0) * loan.qty

		loan_security_map[loan.name]['security_value'] += current_loan_security_amount - (current_loan_security_amount * loan.haircut/100)

	for loan, value in iteritems(loan_security_map):
		if value["security_value"] < value["loan_amount"]:
			create_loan_security_shortfall(loan, value, process_loan_security_price)

def create_loan_security_shortfall(loan, value, process_loan_security_price):

	existing_shortfall = frappe.db.get_value("Loan Security Shortfall", {"loan": loan, "status": "Pending"}, "name")

	if existing_shortfall:
		ltv_shortfall = frappe.get_doc("Loan Security Shortfall", existing_shortfall)
		ltv_shortfall.shortfall_time = get_datetime()
		ltv_shortfall.loan_amount = value["loan_amount"]
		ltv_shortfall.security_value = value["security_value"]
		ltv_shortfall.shortfall_amount = value["loan_amount"] - value["security_value"]
		ltv_shortfall.process_loan_security_price = process_loan_security_price
		ltv_shortfall.save()
	else:
		ltv_shortfall = frappe.new_doc("Loan Security Shortfall")
		ltv_shortfall.loan = loan
		ltv_shortfall.shortfall_time = get_datetime()
		ltv_shortfall.loan_amount = value["loan_amount"]
		ltv_shortfall.security_value = value["security_value"]
		ltv_shortfall.shortfall_amount = value["loan_amount"] - value["security_value"]
		ltv_shortfall.process_loan_security_price = process_loan_security_price
		ltv_shortfall.save()






