# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, get_datetime, getdate

import erpnext
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import (
	get_last_accrual_date,
	get_per_day_interest,
)
from erpnext.loan_management.doctype.loan_security_shortfall.loan_security_shortfall import (
	update_shortfall_status,
)
from erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import (
	process_loan_interest_accrual_for_demand_loans,
)


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
		self.update_repayment_schedule()
		self.make_gl_entries()

	def on_cancel(self):
		self.check_future_accruals()
		self.update_repayment_schedule(cancel=1)
		self.mark_as_unpaid()
		self.ignore_linked_doctypes = ["GL Entry", "Payment Ledger Entry"]
		self.make_gl_entries(cancel=1)

	def set_missing_values(self, amounts):
		precision = cint(frappe.db.get_default("currency_precision")) or 2

		if not self.posting_date:
			self.posting_date = get_datetime()

		if not self.cost_center:
			self.cost_center = erpnext.get_default_cost_center(self.company)

		if not self.interest_payable:
			self.interest_payable = flt(amounts["interest_amount"], precision)

		if not self.penalty_amount:
			self.penalty_amount = flt(amounts["penalty_amount"], precision)

		if not self.pending_principal_amount:
			self.pending_principal_amount = flt(amounts["pending_principal_amount"], precision)

		if not self.payable_principal_amount and self.is_term_loan:
			self.payable_principal_amount = flt(amounts["payable_principal_amount"], precision)

		if not self.payable_amount:
			self.payable_amount = flt(amounts["payable_amount"], precision)

		shortfall_amount = flt(
			frappe.db.get_value(
				"Loan Security Shortfall", {"loan": self.against_loan, "status": "Pending"}, "shortfall_amount"
			)
		)

		if shortfall_amount:
			self.shortfall_amount = shortfall_amount

		if amounts.get("due_date"):
			self.due_date = amounts.get("due_date")

		if hasattr(self, "repay_from_salary") and hasattr(self, "payroll_payable_account"):
			if self.repay_from_salary and not self.payroll_payable_account:
				frappe.throw(_("Please set Payroll Payable Account in Loan Repayment"))
			elif not self.repay_from_salary and self.payroll_payable_account:
				self.repay_from_salary = 1

	def check_future_entries(self):
		future_repayment_date = frappe.db.get_value(
			"Loan Repayment",
			{"posting_date": (">", self.posting_date), "docstatus": 1, "against_loan": self.against_loan},
			"posting_date",
		)

		if future_repayment_date:
			frappe.throw("Repayment already made till date {0}".format(get_datetime(future_repayment_date)))

	def validate_amount(self):
		precision = cint(frappe.db.get_default("currency_precision")) or 2

		if not self.amount_paid:
			frappe.throw(_("Amount paid cannot be zero"))

	def book_unaccrued_interest(self):
		precision = cint(frappe.db.get_default("currency_precision")) or 2
		if flt(self.total_interest_paid, precision) > flt(self.interest_payable, precision):
			if not self.is_term_loan:
				# get last loan interest accrual date
				last_accrual_date = get_last_accrual_date(self.against_loan, self.posting_date)

				# get posting date upto which interest has to be accrued
				per_day_interest = get_per_day_interest(
					self.pending_principal_amount, self.rate_of_interest, self.posting_date
				)

				no_of_days = (
					flt(flt(self.total_interest_paid - self.interest_payable, precision) / per_day_interest, 0)
					- 1
				)

				posting_date = add_days(last_accrual_date, no_of_days)

				# book excess interest paid
				process = process_loan_interest_accrual_for_demand_loans(
					posting_date=posting_date, loan=self.against_loan, accrual_type="Repayment"
				)

				# get loan interest accrual to update paid amount
				lia = frappe.db.get_value(
					"Loan Interest Accrual",
					{"process_loan_interest_accrual": process},
					["name", "interest_amount", "payable_principal_amount"],
					as_dict=1,
				)

				if lia:
					self.append(
						"repayment_details",
						{
							"loan_interest_accrual": lia.name,
							"paid_interest_amount": flt(self.total_interest_paid - self.interest_payable, precision),
							"paid_principal_amount": 0.0,
							"accrual_type": "Repayment",
						},
					)

	def update_paid_amount(self):
		loan = frappe.get_value(
			"Loan",
			self.against_loan,
			[
				"total_amount_paid",
				"total_principal_paid",
				"status",
				"is_secured_loan",
				"total_payment",
				"loan_amount",
				"disbursed_amount",
				"total_interest_payable",
				"written_off_amount",
			],
			as_dict=1,
		)

		loan.update(
			{
				"total_amount_paid": loan.total_amount_paid + self.amount_paid,
				"total_principal_paid": loan.total_principal_paid + self.principal_amount_paid,
			}
		)

		pending_principal_amount = get_pending_principal_amount(loan)
		if not loan.is_secured_loan and pending_principal_amount <= 0:
			loan.update({"status": "Loan Closure Requested"})

		for payment in self.repayment_details:
			frappe.db.sql(
				""" UPDATE `tabLoan Interest Accrual`
				SET paid_principal_amount = `paid_principal_amount` + %s,
					paid_interest_amount = `paid_interest_amount` + %s
				WHERE name = %s""",
				(
					flt(payment.paid_principal_amount),
					flt(payment.paid_interest_amount),
					payment.loan_interest_accrual,
				),
			)

		frappe.db.sql(
			""" UPDATE `tabLoan`
			SET total_amount_paid = %s, total_principal_paid = %s, status = %s
			WHERE name = %s """,
			(loan.total_amount_paid, loan.total_principal_paid, loan.status, self.against_loan),
		)

		update_shortfall_status(self.against_loan, self.principal_amount_paid)

	def mark_as_unpaid(self):
		loan = frappe.get_value(
			"Loan",
			self.against_loan,
			[
				"total_amount_paid",
				"total_principal_paid",
				"status",
				"is_secured_loan",
				"total_payment",
				"loan_amount",
				"disbursed_amount",
				"total_interest_payable",
				"written_off_amount",
			],
			as_dict=1,
		)

		no_of_repayments = len(self.repayment_details)

		loan.update(
			{
				"total_amount_paid": loan.total_amount_paid - self.amount_paid,
				"total_principal_paid": loan.total_principal_paid - self.principal_amount_paid,
			}
		)

		if loan.status == "Loan Closure Requested":
			if loan.disbursed_amount >= loan.loan_amount:
				loan["status"] = "Disbursed"
			else:
				loan["status"] = "Partially Disbursed"

		for payment in self.repayment_details:
			frappe.db.sql(
				""" UPDATE `tabLoan Interest Accrual`
				SET paid_principal_amount = `paid_principal_amount` - %s,
					paid_interest_amount = `paid_interest_amount` - %s
				WHERE name = %s""",
				(payment.paid_principal_amount, payment.paid_interest_amount, payment.loan_interest_accrual),
			)

			# Cancel repayment interest accrual
			# checking idx as a preventive measure, repayment accrual will always be the last entry
			if payment.accrual_type == "Repayment" and payment.idx == no_of_repayments:
				lia_doc = frappe.get_doc("Loan Interest Accrual", payment.loan_interest_accrual)
				lia_doc.cancel()

		frappe.db.sql(
			""" UPDATE `tabLoan`
			SET total_amount_paid = %s, total_principal_paid = %s, status = %s
			WHERE name = %s """,
			(loan.total_amount_paid, loan.total_principal_paid, loan.status, self.against_loan),
		)

	def check_future_accruals(self):
		if self.is_term_loan:
			return

		future_accrual_date = frappe.db.get_value(
			"Loan Interest Accrual",
			{"posting_date": (">", self.posting_date), "docstatus": 1, "loan": self.against_loan},
			"posting_date",
		)

		if future_accrual_date:
			frappe.throw(
				"Cannot cancel. Interest accruals already processed till {0}".format(
					get_datetime(future_accrual_date)
				)
			)

	def update_repayment_schedule(self, cancel=0):
		if self.is_term_loan and self.principal_amount_paid > self.payable_principal_amount:
			regenerate_repayment_schedule(self.against_loan, cancel)

	def allocate_amounts(self, repayment_details):
		precision = cint(frappe.db.get_default("currency_precision")) or 2
		self.set("repayment_details", [])
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
				self.total_penalty_paid = flt(self.penalty_amount, precision)
			elif self.penalty_amount:
				self.total_penalty_paid = flt(interest_paid, precision)

			interest_paid -= self.total_penalty_paid

		if self.is_term_loan:
			interest_paid, updated_entries = self.allocate_interest_amount(interest_paid, repayment_details)
			self.allocate_principal_amount_for_term_loans(interest_paid, repayment_details, updated_entries)
		else:
			interest_paid, updated_entries = self.allocate_interest_amount(interest_paid, repayment_details)
			self.allocate_excess_payment_for_demand_loans(interest_paid, repayment_details)

	def allocate_interest_amount(self, interest_paid, repayment_details):
		updated_entries = {}
		self.total_interest_paid = 0
		idx = 1

		if interest_paid > 0:
			for lia, amounts in repayment_details.get("pending_accrual_entries", []).items():
				interest_amount = 0
				if amounts["interest_amount"] <= interest_paid:
					interest_amount = amounts["interest_amount"]
					self.total_interest_paid += interest_amount
					interest_paid -= interest_amount
				elif interest_paid:
					if interest_paid >= amounts["interest_amount"]:
						interest_amount = amounts["interest_amount"]
						self.total_interest_paid += interest_amount
						interest_paid = 0
					else:
						interest_amount = interest_paid
						self.total_interest_paid += interest_amount
						interest_paid = 0

				if interest_amount:
					self.append(
						"repayment_details",
						{
							"loan_interest_accrual": lia,
							"paid_interest_amount": interest_amount,
							"paid_principal_amount": 0,
						},
					)
					updated_entries[lia] = idx
					idx += 1

		return interest_paid, updated_entries

	def allocate_principal_amount_for_term_loans(
		self, interest_paid, repayment_details, updated_entries
	):
		if interest_paid > 0:
			for lia, amounts in repayment_details.get("pending_accrual_entries", []).items():
				paid_principal = 0
				if amounts["payable_principal_amount"] <= interest_paid:
					paid_principal = amounts["payable_principal_amount"]
					self.principal_amount_paid += paid_principal
					interest_paid -= paid_principal
				elif interest_paid:
					if interest_paid >= amounts["payable_principal_amount"]:
						paid_principal = amounts["payable_principal_amount"]
						self.principal_amount_paid += paid_principal
						interest_paid = 0
					else:
						paid_principal = interest_paid
						self.principal_amount_paid += paid_principal
						interest_paid = 0

				if updated_entries.get(lia):
					idx = updated_entries.get(lia)
					self.get("repayment_details")[idx - 1].paid_principal_amount += paid_principal
				else:
					self.append(
						"repayment_details",
						{
							"loan_interest_accrual": lia,
							"paid_interest_amount": 0,
							"paid_principal_amount": paid_principal,
						},
					)

		if interest_paid > 0:
			self.principal_amount_paid += interest_paid

	def allocate_excess_payment_for_demand_loans(self, interest_paid, repayment_details):
		if repayment_details["unaccrued_interest"] and interest_paid > 0:
			# no of days for which to accrue interest
			# Interest can only be accrued for an entire day and not partial
			if interest_paid > repayment_details["unaccrued_interest"]:
				interest_paid -= repayment_details["unaccrued_interest"]
				self.total_interest_paid += repayment_details["unaccrued_interest"]
			else:
				# get no of days for which interest can be paid
				per_day_interest = get_per_day_interest(
					self.pending_principal_amount, self.rate_of_interest, self.posting_date
				)

				no_of_days = cint(interest_paid / per_day_interest)
				self.total_interest_paid += no_of_days * per_day_interest
				interest_paid -= no_of_days * per_day_interest

		if interest_paid > 0:
			self.principal_amount_paid += interest_paid

	def make_gl_entries(self, cancel=0, adv_adj=0):
		gle_map = []
		if self.shortfall_amount and self.amount_paid > self.shortfall_amount:
			remarks = "Shortfall repayment of {0}.<br>Repayment against loan {1}".format(
				self.shortfall_amount, self.against_loan
			)
		elif self.shortfall_amount:
			remarks = "Shortfall repayment of {0} against loan {1}".format(
				self.shortfall_amount, self.against_loan
			)
		else:
			remarks = "Repayment against loan " + self.against_loan

		if self.reference_number:
			remarks += "with reference no. {}".format(self.reference_number)

		if hasattr(self, "repay_from_salary") and self.repay_from_salary:
			payment_account = self.payroll_payable_account
		else:
			payment_account = self.payment_account

		payment_party_type = ""
		payment_party = ""

		if (
			hasattr(self, "process_payroll_accounting_entry_based_on_employee")
			and self.process_payroll_accounting_entry_based_on_employee
		):
			payment_party_type = "Employee"
			payment_party = self.applicant

		if self.total_penalty_paid:
			gle_map.append(
				self.get_gl_dict(
					{
						"account": self.loan_account,
						"against": payment_account,
						"debit": self.total_penalty_paid,
						"debit_in_account_currency": self.total_penalty_paid,
						"against_voucher_type": "Loan",
						"against_voucher": self.against_loan,
						"remarks": _("Penalty against loan:") + self.against_loan,
						"cost_center": self.cost_center,
						"party_type": self.applicant_type,
						"party": self.applicant,
						"posting_date": getdate(self.posting_date),
					}
				)
			)

			gle_map.append(
				self.get_gl_dict(
					{
						"account": self.penalty_income_account,
						"against": self.loan_account,
						"credit": self.total_penalty_paid,
						"credit_in_account_currency": self.total_penalty_paid,
						"against_voucher_type": "Loan",
						"against_voucher": self.against_loan,
						"remarks": _("Penalty against loan:") + self.against_loan,
						"cost_center": self.cost_center,
						"posting_date": getdate(self.posting_date),
					}
				)
			)

		gle_map.append(
			self.get_gl_dict(
				{
					"account": payment_account,
					"against": self.loan_account + ", " + self.penalty_income_account,
					"debit": self.amount_paid,
					"debit_in_account_currency": self.amount_paid,
					"against_voucher_type": "Loan",
					"against_voucher": self.against_loan,
					"remarks": _(remarks),
					"cost_center": self.cost_center,
					"posting_date": getdate(self.posting_date),
					"party_type": payment_party_type,
					"party": payment_party,
				}
			)
		)

		gle_map.append(
			self.get_gl_dict(
				{
					"account": self.loan_account,
					"party_type": self.applicant_type,
					"party": self.applicant,
					"against": payment_account,
					"credit": self.amount_paid,
					"credit_in_account_currency": self.amount_paid,
					"against_voucher_type": "Loan",
					"against_voucher": self.against_loan,
					"remarks": _(remarks),
					"cost_center": self.cost_center,
					"posting_date": getdate(self.posting_date),
				}
			)
		)

		if gle_map:
			make_gl_entries(gle_map, cancel=cancel, adv_adj=adv_adj, merge_entries=False)


def create_repayment_entry(
	loan,
	applicant,
	company,
	posting_date,
	loan_type,
	payment_type,
	interest_payable,
	payable_principal_amount,
	amount_paid,
	penalty_amount=None,
	payroll_payable_account=None,
	process_payroll_accounting_entry_based_on_employee=0,
):

	lr = frappe.get_doc(
		{
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
			"loan_type": loan_type,
			"payroll_payable_account": payroll_payable_account,
			"process_payroll_accounting_entry_based_on_employee": process_payroll_accounting_entry_based_on_employee,
		}
	).insert()

	return lr


def get_accrued_interest_entries(against_loan, posting_date=None):
	if not posting_date:
		posting_date = getdate()

	precision = cint(frappe.db.get_default("currency_precision")) or 2

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
		""",
		(against_loan, posting_date),
		as_dict=1,
	)

	# Skip entries with zero interest amount & payable principal amount
	unpaid_accrued_entries = [
		d
		for d in unpaid_accrued_entries
		if flt(d.interest_amount, precision) > 0 or flt(d.payable_principal_amount, precision) > 0
	]

	return unpaid_accrued_entries


def get_penalty_details(against_loan):
	penalty_details = frappe.db.sql(
		"""
		SELECT posting_date, (penalty_amount - total_penalty_paid) as pending_penalty_amount
		FROM `tabLoan Repayment` where posting_date >= (SELECT MAX(posting_date) from `tabLoan Repayment`
		where against_loan = %s) and docstatus = 1 and against_loan = %s
	""",
		(against_loan, against_loan),
	)

	if penalty_details:
		return penalty_details[0][0], flt(penalty_details[0][1])
	else:
		return None, 0


def regenerate_repayment_schedule(loan, cancel=0):
	from erpnext.loan_management.doctype.loan.loan import (
		add_single_month,
		get_monthly_repayment_amount,
	)

	loan_doc = frappe.get_doc("Loan", loan)
	next_accrual_date = None
	accrued_entries = 0
	last_repayment_amount = None
	last_balance_amount = None

	for term in reversed(loan_doc.get("repayment_schedule")):
		if not term.is_accrued:
			next_accrual_date = term.payment_date
			loan_doc.remove(term)
		else:
			accrued_entries += 1
			if last_repayment_amount is None:
				last_repayment_amount = term.total_payment
			if last_balance_amount is None:
				last_balance_amount = term.balance_loan_amount

	loan_doc.save()

	balance_amount = get_pending_principal_amount(loan_doc)

	if loan_doc.repayment_method == "Repay Fixed Amount per Period":
		monthly_repayment_amount = flt(
			balance_amount / len(loan_doc.get("repayment_schedule")) - accrued_entries
		)
	else:
		repayment_period = loan_doc.repayment_periods - accrued_entries
		if not cancel and repayment_period > 0:
			monthly_repayment_amount = get_monthly_repayment_amount(
				balance_amount, loan_doc.rate_of_interest, repayment_period
			)
		else:
			monthly_repayment_amount = last_repayment_amount
			balance_amount = last_balance_amount

	payment_date = next_accrual_date

	while balance_amount > 0:
		interest_amount = flt(balance_amount * flt(loan_doc.rate_of_interest) / (12 * 100))
		principal_amount = monthly_repayment_amount - interest_amount
		balance_amount = flt(balance_amount + interest_amount - monthly_repayment_amount)
		if balance_amount < 0:
			principal_amount += balance_amount
			balance_amount = 0.0

		total_payment = principal_amount + interest_amount
		loan_doc.append(
			"repayment_schedule",
			{
				"payment_date": payment_date,
				"principal_amount": principal_amount,
				"interest_amount": interest_amount,
				"total_payment": total_payment,
				"balance_loan_amount": balance_amount,
			},
		)
		next_payment_date = add_single_month(payment_date)
		payment_date = next_payment_date

	loan_doc.save()


def get_pending_principal_amount(loan):
	if loan.status in ("Disbursed", "Closed") or loan.disbursed_amount >= loan.loan_amount:
		pending_principal_amount = (
			flt(loan.total_payment)
			+ flt(loan.debit_adjustment_amount)
			- flt(loan.credit_adjustment_amount)
			- flt(loan.total_principal_paid)
			- flt(loan.total_interest_payable)
			- flt(loan.written_off_amount)
			+ flt(loan.refund_amount)
		)
	else:
		pending_principal_amount = (
			flt(loan.disbursed_amount)
			+ flt(loan.debit_adjustment_amount)
			- flt(loan.credit_adjustment_amount)
			- flt(loan.total_principal_paid)
			- flt(loan.total_interest_payable)
			- flt(loan.written_off_amount)
			+ flt(loan.refund_amount)
		)

	return pending_principal_amount


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
	final_due_date = ""
	due_date = ""

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

		if (
			no_of_late_days > 0
			and (
				not (hasattr(against_loan_doc, "repay_from_salary") and against_loan_doc.repay_from_salary)
			)
			and entry.accrual_type == "Regular"
		):
			penalty_amount += (
				entry.interest_amount * (loan_type_details.penalty_interest_rate / 100) * no_of_late_days
			)

		total_pending_interest += entry.interest_amount
		payable_principal_amount += entry.payable_principal_amount

		pending_accrual_entries.setdefault(
			entry.name,
			{
				"interest_amount": flt(entry.interest_amount, precision),
				"payable_principal_amount": flt(entry.payable_principal_amount, precision),
			},
		)

		if due_date and not final_due_date:
			final_due_date = add_days(due_date, loan_type_details.grace_period_in_days)

	pending_principal_amount = get_pending_principal_amount(against_loan_doc)

	unaccrued_interest = 0
	if due_date:
		pending_days = date_diff(posting_date, due_date) + 1
	else:
		last_accrual_date = get_last_accrual_date(against_loan_doc.name, posting_date)
		pending_days = date_diff(posting_date, last_accrual_date) + 1

	if pending_days > 0:
		principal_amount = flt(pending_principal_amount, precision)
		per_day_interest = get_per_day_interest(
			principal_amount, loan_type_details.rate_of_interest, posting_date
		)
		unaccrued_interest += pending_days * per_day_interest

	amounts["pending_principal_amount"] = flt(pending_principal_amount, precision)
	amounts["payable_principal_amount"] = flt(payable_principal_amount, precision)
	amounts["interest_amount"] = flt(total_pending_interest, precision)
	amounts["penalty_amount"] = flt(penalty_amount + pending_penalty_amount, precision)
	amounts["payable_amount"] = flt(
		payable_principal_amount + total_pending_interest + penalty_amount, precision
	)
	amounts["pending_accrual_entries"] = pending_accrual_entries
	amounts["unaccrued_interest"] = flt(unaccrued_interest, precision)
	amounts["written_off_amount"] = flt(against_loan_doc.written_off_amount, precision)

	if final_due_date:
		amounts["due_date"] = final_due_date

	return amounts


@frappe.whitelist()
def calculate_amounts(against_loan, posting_date, payment_type=""):
	amounts = {
		"penalty_amount": 0.0,
		"interest_amount": 0.0,
		"pending_principal_amount": 0.0,
		"payable_principal_amount": 0.0,
		"payable_amount": 0.0,
		"unaccrued_interest": 0.0,
		"due_date": "",
	}

	amounts = get_amounts(amounts, against_loan, posting_date)

	# update values for closure
	if payment_type == "Loan Closure":
		amounts["payable_principal_amount"] = amounts["pending_principal_amount"]
		amounts["interest_amount"] += amounts["unaccrued_interest"]
		amounts["payable_amount"] = (
			amounts["payable_principal_amount"] + amounts["interest_amount"] + amounts["penalty_amount"]
		)

	return amounts
