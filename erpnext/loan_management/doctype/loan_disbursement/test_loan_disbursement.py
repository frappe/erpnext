# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import (
	add_days,
	add_to_date,
	date_diff,
	flt,
	get_datetime,
	get_first_day,
	get_last_day,
	nowdate,
)

from erpnext.loan_management.doctype.loan.test_loan import (
	create_demand_loan,
	create_loan_accounts,
	create_loan_application,
	create_loan_security,
	create_loan_security_pledge,
	create_loan_security_price,
	create_loan_security_type,
	create_loan_type,
	create_repayment_entry,
	make_loan_disbursement_entry,
)
from erpnext.loan_management.doctype.loan_application.loan_application import create_pledge
from erpnext.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import (
	days_in_year,
	get_per_day_interest,
)
from erpnext.loan_management.doctype.loan_repayment.loan_repayment import calculate_amounts
from erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import (
	process_loan_interest_accrual_for_demand_loans,
)
from erpnext.selling.doctype.customer.test_customer import get_customer_dict


class TestLoanDisbursement(unittest.TestCase):

	def setUp(self):
		create_loan_accounts()

		create_loan_type("Demand Loan", 2000000, 13.5, 25, 0, 5, 'Cash', 'Payment Account - _TC', 'Loan Account - _TC',
			'Interest Income Account - _TC', 'Penalty Income Account - _TC')

		create_loan_security_type()
		create_loan_security()

		create_loan_security_price("Test Security 1", 500, "Nos", get_datetime() , get_datetime(add_to_date(nowdate(), hours=24)))
		create_loan_security_price("Test Security 2", 250, "Nos", get_datetime() , get_datetime(add_to_date(nowdate(), hours=24)))

		if not frappe.db.exists("Customer", "_Test Loan Customer"):
			frappe.get_doc(get_customer_dict('_Test Loan Customer')).insert(ignore_permissions=True)

		self.applicant = frappe.db.get_value("Customer", {'name': '_Test Loan Customer'}, 'name')

	def test_loan_topup(self):
		pledge = [{
			"loan_security": "Test Security 1",
			"qty": 4000.00
		}]

		loan_application = create_loan_application('_Test Company', self.applicant, 'Demand Loan', pledge)
		create_pledge(loan_application)

		loan = create_demand_loan(self.applicant, "Demand Loan", loan_application, posting_date=get_first_day(nowdate()))

		loan.submit()

		first_date = get_first_day(nowdate())
		last_date = get_last_day(nowdate())

		no_of_days = date_diff(last_date, first_date) + 1

		accrued_interest_amount = (loan.loan_amount * loan.rate_of_interest * no_of_days) \
			/ (days_in_year(get_datetime().year) * 100)

		make_loan_disbursement_entry(loan.name, loan.loan_amount, disbursement_date=first_date)

		process_loan_interest_accrual_for_demand_loans(posting_date=add_days(last_date, 1))

		# Should not be able to create loan disbursement entry before repayment
		self.assertRaises(frappe.ValidationError, make_loan_disbursement_entry, loan.name,
			500000, first_date)

		repayment_entry = create_repayment_entry(loan.name, self.applicant, add_days(get_last_day(nowdate()), 5), 611095.89)

		repayment_entry.submit()
		loan.reload()

		# After repayment loan disbursement entry should go through
		make_loan_disbursement_entry(loan.name, 500000, disbursement_date=add_days(last_date, 16))

		# check for disbursement accrual
		loan_interest_accrual = frappe.db.get_value('Loan Interest Accrual', {'loan': loan.name,
			'accrual_type': 'Disbursement'})

		self.assertTrue(loan_interest_accrual)

	def test_loan_topup_with_additional_pledge(self):
		pledge = [{
			"loan_security": "Test Security 1",
			"qty": 4000.00
		}]

		loan_application = create_loan_application('_Test Company', self.applicant, 'Demand Loan', pledge)
		create_pledge(loan_application)

		loan = create_demand_loan(self.applicant, "Demand Loan", loan_application, posting_date='2019-10-01')
		loan.submit()

		self.assertEqual(loan.loan_amount, 1000000)

		first_date = '2019-10-01'
		last_date = '2019-10-30'

		# Disbursed 10,00,000 amount
		make_loan_disbursement_entry(loan.name, loan.loan_amount, disbursement_date=first_date)
		process_loan_interest_accrual_for_demand_loans(posting_date = last_date)
		amounts = calculate_amounts(loan.name, add_days(last_date, 1))

		previous_interest = amounts['interest_amount']

		pledge1 = [{
			"loan_security": "Test Security 1",
			"qty": 2000.00
		}]

		create_loan_security_pledge(self.applicant, pledge1, loan=loan.name)

		# Topup 500000
		make_loan_disbursement_entry(loan.name, 500000, disbursement_date=add_days(last_date, 1))
		process_loan_interest_accrual_for_demand_loans(posting_date = add_days(last_date, 15))
		amounts = calculate_amounts(loan.name, add_days(last_date, 15))

		per_day_interest = get_per_day_interest(1500000, 13.5, '2019-10-30')
		interest = per_day_interest * 15

		self.assertEqual(amounts['pending_principal_amount'], 1500000)
		self.assertEqual(amounts['interest_amount'], flt(interest + previous_interest, 2))
