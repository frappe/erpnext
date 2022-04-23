# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
import json
from frappe import _
from frappe.utils import flt, getdate, cint
from six import iteritems
from frappe.model.document import Document
from frappe.utils import date_diff, add_days, getdate, add_months, get_first_day, get_datetime
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.loan_management.doctype.loan_security_shortfall.loan_security_shortfall import update_shortfall_status
from erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import process_loan_interest_accrual_for_demand_loans
from erpnext.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import get_per_day_interest, get_last_accrual_date

class LoanRepayment(AccountsController):

	def validate(self):
		amounts = calculate_amounts(self.against_loan, self.posting_date)
		self.set_missing_values(amounts)
		self.check_future_entries()
		self.validate_amount()
		self.allocate_amounts(amounts)

	def before_submit(self):
		self.book_unaccrued_interest()

	def on_submit(self):
		self.update_paid_amount()
		self.make_gl_entries()

	def on_cancel(self):
		self.mark_as_unpaid()
		self.ignore_linked_doctypes = ['GL Entry']
		self.make_gl_entries(cancel=1)

	def set_missing_values(self, amounts):
		precision = cint(frappe.db.get_default("currency_precision")) or 2

		if not self.posting_date:
			self.posting_date = get_datetime()

		if not self.cost_center:
			self.cost_center = erpnext.get_default_cost_center(self.company)

		if not self.interest_payable:
			self.interest_payable = flt(amounts['interest_amount'], precision)

		if not self.penalty_amount:
			self.penalty_amount = flt(amounts['penalty_amount'], precision)

		if not self.pending_principal_amount:
			self.pending_principal_amount = flt(amounts['pending_principal_amount'], precision)

		if not self.payable_principal_amount and self.is_term_loan:
			self.payable_principal_amount = flt(amounts['payable_principal_amount'], precision)

		if not self.payable_amount:
			self.payable_amount = flt(amounts['payable_amount'], precision)

		shortfall_amount = flt(frappe.db.get_value('Loan Security Shortfall', {'loan': self.against_loan, 'status': 'Pending'},
			'shortfall_amount'))

		if shortfall_amount:
			self.shortfall_amount = shortfall_amount

		if amounts.get('due_date'):
			self.due_date = amounts.get('due_date')

	def check_future_entries(self):
		future_repayment_date = frappe.db.get_value("Loan Repayment", {"posting_date": (">", self.posting_date),
			"docstatus": 1, "against_loan": self.against_loan}, 'posting_date')

		if future_repayment_date:
			frappe.throw("Repayment already made till date {0}".format(get_datetime(future_repayment_date)))

	def validate_amount(self):
		precision = cint(frappe.db.get_default("currency_precision")) or 2

		if not self.amount_paid:
			frappe.throw(_("Amount paid cannot be zero"))

	def book_unaccrued_interest(self):
		precision = cint(frappe.db.get_default("currency_precision")) or 2
		if self.total_interest_paid > self.interest_payable:
			if not self.is_term_loan:
				# get last loan interest accrual date
				last_accrual_date = get_last_accrual_date(self.against_loan)

				# get posting date upto which interest has to be accrued
				per_day_interest = get_per_day_interest(self.pending_principal_amount,
					self.rate_of_interest, self.posting_date)

				no_of_days = flt(flt(self.total_interest_paid - self.interest_payable,
					precision)/per_day_interest, 0) - 1

				posting_date = add_days(last_accrual_date, no_of_days)

				# book excess interest paid
				process = process_loan_interest_accrual_for_demand_loans(posting_date=posting_date,
					loan=self.against_loan, accrual_type="Repayment")

				# get loan interest accrual to update paid amount
				lia = frappe.db.get_value('Loan Interest Accrual', {'process_loan_interest_accrual':
					process}, ['name', 'interest_amount', 'payable_principal_amount'], as_dict=1)

				self.append('repayment_details', {
					'loan_interest_accrual': lia.name,
					'paid_interest_amount': flt(self.total_interest_paid - self.interest_payable, precision),
					'paid_principal_amount': 0.0,
					'accrual_type': 'Repayment'
				})

	def update_paid_amount(self):
		loan = frappe.get_doc("Loan", self.against_loan)

		for payment in self.repayment_details:
			frappe.db.sql(""" UPDATE `tabLoan Interest Accrual`
				SET paid_principal_amount = `paid_principal_amount` + %s,
					paid_interest_amount = `paid_interest_amount` + %s
				WHERE name = %s""",
				(flt(payment.paid_principal_amount), flt(payment.paid_interest_amount), payment.loan_interest_accrual))

		frappe.db.sql(""" UPDATE `tabLoan` SET total_amount_paid = %s, total_principal_paid = %s
			WHERE name = %s """, (loan.total_amount_paid + self.amount_paid,
			loan.total_principal_paid + self.principal_amount_paid, self.against_loan))

		update_shortfall_status(self.against_loan, self.principal_amount_paid)

	def mark_as_unpaid(self):
		loan = frappe.get_doc("Loan", self.against_loan)

		no_of_repayments = len(self.repayment_details)

		for payment in self.repayment_details:
			frappe.db.sql(""" UPDATE `tabLoan Interest Accrual`
				SET paid_principal_amount = `paid_principal_amount` - %s,
					paid_interest_amount = `paid_interest_amount` - %s
				WHERE name = %s""",
				(payment.paid_principal_amount, payment.paid_interest_amount, payment.loan_interest_accrual))

			# Cancel repayment interest accrual
			# checking idx as a preventive measure, repayment accrual will always be the last entry
			if payment.accrual_type == 'Repayment' and payment.idx == no_of_repayments:
				lia_doc = frappe.get_doc('Loan Interest Accrual', payment.loan_interest_accrual)
				lia_doc.cancel()

		frappe.db.sql(""" UPDATE `tabLoan` SET total_amount_paid = %s, total_principal_paid = %s
			WHERE name = %s """, (loan.total_amount_paid - self.amount_paid,
			loan.total_principal_paid - self.principal_amount_paid, self.against_loan))

		if loan.status == "Loan Closure Requested":
			frappe.db.set_value("Loan", self.against_loan, "status", "Disbursed")

	def allocate_amounts(self, repayment_details):
		self.set('repayment_details', [])
		self.principal_amount_paid = 0
		self.total_penalty_paid = 0
		interest_paid = self.amount_paid

		if self.shortfall_amount and self.amount_paid > self.shortfall_amount:
			self.principal_amount_paid = self.shortfall_amount
		elif self.shortfall_amount:
			self.principal_amount_paid = self.amount_paid

		interest_paid -= self.principal_amount_paid

		if interest_paid > 0:
			if self.penalty_amount and interest_paid > self.penalty_amount:
				self.total_penalty_paid = self.penalty_amount
			elif self.penalty_amount:
				self.total_penalty_paid = interest_paid

			interest_paid -= self.total_penalty_paid

		total_interest_paid = 0
		# interest_paid = self.amount_paid - self.principal_amount_paid - self.penalty_amount

		if interest_paid > 0:
			for lia, amounts in iteritems(repayment_details.get('pending_accrual_entries', [])):
				if amounts['interest_amount'] + amounts['payable_principal_amount'] <= interest_paid:
					interest_amount = amounts['interest_amount']
					paid_principal = amounts['payable_principal_amount']
					self.principal_amount_paid += paid_principal
					interest_paid -= (interest_amount + paid_principal)
				elif interest_paid:
					if interest_paid >= amounts['interest_amount']:
						interest_amount = amounts['interest_amount']
						paid_principal = interest_paid - interest_amount
						self.principal_amount_paid += paid_principal
						interest_paid = 0
					else:
						interest_amount = interest_paid
						interest_paid = 0
						paid_principal=0

				total_interest_paid += interest_amount
				self.append('repayment_details', {
					'loan_interest_accrual': lia,
					'paid_interest_amount': interest_amount,
					'paid_principal_amount': paid_principal
				})

		if repayment_details['unaccrued_interest'] and interest_paid > 0:
			# no of days for which to accrue interest
			# Interest can only be accrued for an entire day and not partial
			if interest_paid > repayment_details['unaccrued_interest']:
				interest_paid -= repayment_details['unaccrued_interest']
				total_interest_paid += repayment_details['unaccrued_interest']
			else:
				# get no of days for which interest can be paid
				per_day_interest = get_per_day_interest(self.pending_principal_amount,
					self.rate_of_interest, self.posting_date)

				no_of_days = cint(interest_paid/per_day_interest)
				total_interest_paid += no_of_days * per_day_interest
				interest_paid -= no_of_days * per_day_interest

		self.total_interest_paid = total_interest_paid
		if interest_paid > 0:
			self.principal_amount_paid += interest_paid

	def make_gl_entries(self, cancel=0, adv_adj=0):
		gle_map = []
		loan_details = frappe.get_doc("Loan", self.against_loan)

		if self.shortfall_amount and self.amount_paid > self.shortfall_amount:
			remarks = _("Shortfall Repayment of {0}.\nRepayment against Loan: {1}").format(self.shortfall_amount,
				self.against_loan)
		elif self.shortfall_amount:
			remarks = _("Shortfall Repayment of {0}").format(self.shortfall_amount)
		else:
			remarks = _("Repayment against Loan: ") + self.against_loan

		if not loan_details.repay_from_salary:
			if self.total_penalty_paid:
				gle_map.append(
					self.get_gl_dict({
						"account": loan_details.loan_account,
						"against": loan_details.payment_account,
						"debit": self.total_penalty_paid,
						"debit_in_account_currency": self.total_penalty_paid,
						"against_voucher_type": "Loan",
						"against_voucher": self.against_loan,
						"remarks": _("Penalty against loan:") + self.against_loan,
						"cost_center": self.cost_center,
						"party_type": self.applicant_type,
						"party": self.applicant,
						"posting_date": getdate(self.posting_date)
					})
				)

				gle_map.append(
					self.get_gl_dict({
						"account": loan_details.penalty_income_account,
						"against": loan_details.payment_account,
						"credit": self.total_penalty_paid,
						"credit_in_account_currency": self.total_penalty_paid,
						"against_voucher_type": "Loan",
						"against_voucher": self.against_loan,
						"remarks": _("Penalty against loan:") + self.against_loan,
						"cost_center": self.cost_center,
						"posting_date": getdate(self.posting_date)
					})
				)

			gle_map.append(
				self.get_gl_dict({
					"account": loan_details.payment_account,
					"against": loan_details.loan_account + ", " + loan_details.interest_income_account
							+ ", " + loan_details.penalty_income_account,
					"debit": self.amount_paid,
					"debit_in_account_currency": self.amount_paid,
					"against_voucher_type": "Loan",
					"against_voucher": self.against_loan,
					"remarks": remarks,
					"cost_center": self.cost_center,
					"posting_date": getdate(self.posting_date)
				})
			)

			gle_map.append(
				self.get_gl_dict({
					"account": loan_details.loan_account,
					"party_type": loan_details.applicant_type,
					"party": loan_details.applicant,
					"against": loan_details.payment_account,
					"credit": self.amount_paid,
					"credit_in_account_currency": self.amount_paid,
					"against_voucher_type": "Loan",
					"against_voucher": self.against_loan,
					"remarks": remarks,
					"cost_center": self.cost_center,
					"posting_date": getdate(self.posting_date)
				})
			)

			if gle_map:
				make_gl_entries(gle_map, cancel=cancel, adv_adj=adv_adj, merge_entries=False)

def create_repayment_entry(loan, applicant, company, posting_date, loan_type,
	payment_type, interest_payable, payable_principal_amount, amount_paid, penalty_amount=None):

	lr = frappe.get_doc({
		"doctype": "Loan Repayment",
		"against_loan": loan,
		"payment_type": payment_type,
		"company": company,
		"posting_date": posting_date,
		"applicant": applicant,
		"penalty_amount": penalty_amount,
		"interest_payable": interest_payable,
		"payable_principal_amount": payable_principal_amount,
		"amount_paid": amount_paid,
		"loan_type": loan_type
	}).insert()

	return lr

def get_accrued_interest_entries(against_loan, posting_date=None):
	if not posting_date:
		posting_date = getdate()

	unpaid_accrued_entries = frappe.db.sql(
		"""
			SELECT name, posting_date, interest_amount - paid_interest_amount as interest_amount,
				payable_principal_amount - paid_principal_amount as payable_principal_amount,
				accrual_type
			FROM
				`tabLoan Interest Accrual`
			WHERE
				loan = %s
			AND posting_date <= %s
			AND (interest_amount - paid_interest_amount > 0 OR
				payable_principal_amount - paid_principal_amount > 0)
			AND
				docstatus = 1
			ORDER BY posting_date
		""", (against_loan, posting_date), as_dict=1)

	return unpaid_accrued_entries

def get_penalty_details(against_loan):
	penalty_details = frappe.db.sql("""
		SELECT posting_date, (penalty_amount - total_penalty_paid) as pending_penalty_amount
		FROM `tabLoan Repayment` where posting_date >= (SELECT MAX(posting_date) from `tabLoan Repayment`
		where against_loan = %s) and docstatus = 1 and against_loan = %s
	""", (against_loan, against_loan))

	if penalty_details:
		return penalty_details[0][0], flt(penalty_details[0][1])
	else:
		return None, 0

# This function returns the amounts that are payable at the time of loan repayment based on posting date
# So it pulls all the unpaid Loan Interest Accrual Entries and calculates the penalty if applicable

def get_amounts(amounts, against_loan, posting_date):
	precision = cint(frappe.db.get_default("currency_precision")) or 2

	against_loan_doc = frappe.get_doc("Loan", against_loan)
	loan_type_details = frappe.get_doc("Loan Type", against_loan_doc.loan_type)
	accrued_interest_entries = get_accrued_interest_entries(against_loan_doc.name, posting_date)

	computed_penalty_date, pending_penalty_amount = get_penalty_details(against_loan)
	pending_accrual_entries = {}

	total_pending_interest = 0
	penalty_amount = 0
	payable_principal_amount = 0
	final_due_date = ''
	due_date = ''

	for entry in accrued_interest_entries:
		# Loan repayment due date is one day after the loan interest is accrued
		# no of late days are calculated based on loan repayment posting date
		# and if no_of_late days are positive then penalty is levied

		due_date = add_days(entry.posting_date, 1)
		due_date_after_grace_period = add_days(due_date, loan_type_details.grace_period_in_days)

		# Consider one day after already calculated penalty
		if computed_penalty_date and getdate(computed_penalty_date) >= due_date_after_grace_period:
			due_date_after_grace_period = add_days(computed_penalty_date, 1)

		no_of_late_days = date_diff(posting_date, due_date_after_grace_period) + 1

		if no_of_late_days > 0 and (not against_loan_doc.repay_from_salary) and entry.accrual_type == 'Regular':
			penalty_amount += (entry.interest_amount * (loan_type_details.penalty_interest_rate / 100) * no_of_late_days)

		total_pending_interest += entry.interest_amount
		payable_principal_amount += entry.payable_principal_amount

		pending_accrual_entries.setdefault(entry.name, {
			'interest_amount': flt(entry.interest_amount, precision),
			'payable_principal_amount': flt(entry.payable_principal_amount, precision)
		})

		if due_date and not final_due_date:
			final_due_date = add_days(due_date, loan_type_details.grace_period_in_days)

	if against_loan_doc.status in ('Disbursed', 'Loan Closure Requested', 'Closed'):
		pending_principal_amount = against_loan_doc.total_payment - against_loan_doc.total_principal_paid \
			- against_loan_doc.total_interest_payable - against_loan_doc.written_off_amount
	else:
		pending_principal_amount = against_loan_doc.disbursed_amount - against_loan_doc.total_principal_paid \
			- against_loan_doc.total_interest_payable - against_loan_doc.written_off_amount

	unaccrued_interest = 0
	if due_date:
		pending_days = date_diff(posting_date, due_date) + 1
	else:
		last_accrual_date = get_last_accrual_date(against_loan_doc.name)
		pending_days = date_diff(posting_date, last_accrual_date) + 1

	if pending_days > 0:
		principal_amount = flt(pending_principal_amount, precision)
		per_day_interest = get_per_day_interest(principal_amount, loan_type_details.rate_of_interest, posting_date)
		unaccrued_interest += (pending_days * per_day_interest)

	amounts["pending_principal_amount"] = flt(pending_principal_amount, precision)
	amounts["payable_principal_amount"] = flt(payable_principal_amount, precision)
	amounts["interest_amount"] = flt(total_pending_interest, precision)
	amounts["penalty_amount"] = flt(penalty_amount + pending_penalty_amount, precision)
	amounts["payable_amount"] = flt(payable_principal_amount + total_pending_interest + penalty_amount, precision)
	amounts["pending_accrual_entries"] = pending_accrual_entries
	amounts["unaccrued_interest"] = flt(unaccrued_interest, precision)

	if final_due_date:
		amounts["due_date"] = final_due_date

	return amounts

@frappe.whitelist()
def calculate_amounts(against_loan, posting_date, payment_type=''):
	amounts = {
		'penalty_amount': 0.0,
		'interest_amount': 0.0,
		'pending_principal_amount': 0.0,
		'payable_principal_amount': 0.0,
		'payable_amount': 0.0,
		'unaccrued_interest': 0.0,
		'due_date': ''
	}

	amounts = get_amounts(amounts, against_loan, posting_date)

	# update values for closure
	if payment_type == 'Loan Closure':
		amounts['payable_principal_amount'] = amounts['pending_principal_amount']
		amounts['interest_amount'] += amounts['unaccrued_interest']
		amounts['payable_amount'] = amounts['payable_principal_amount'] + amounts['interest_amount']

	return amounts



