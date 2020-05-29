# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, flt
import json
from six import iteritems
from erpnext.loan_management.doctype.loan_security_price.loan_security_price import get_loan_security_price

class LoanSecurityUnpledge(Document):
	def validate(self):
		self.validate_duplicate_securities()
		self.validate_unpledge_qty()

	def on_cancel(self):
		self.update_loan_security_pledge(cancel=1)
		self.update_loan_status(cancel=1)
		self.db_set('status', 'Requested')

	def validate_duplicate_securities(self):
		security_list = []
		for d in self.securities:
			if d.loan_security not in security_list:
				security_list.append(d.loan_security)
			else:
				frappe.throw(_("Row {0}: Loan Security {1} added multiple times").format(
					d.idx, frappe.bold(d.loan_security)))

	def validate_unpledge_qty(self):
		pledge_qty_map = get_pledged_security_qty(self.loan)

		ltv_ratio_map = frappe._dict(frappe.get_all("Loan Security Type",
			fields=["name", "loan_to_value_ratio"], as_list=1))

		loan_security_price_map = frappe._dict(frappe.get_all("Loan Security Price",
			fields=["loan_security", "loan_security_price"],
			filters = {
				"valid_from": ("<=", get_datetime()),
				"valid_upto": (">=", get_datetime())
			}, as_list=1))

		loan_amount, principal_paid = frappe.get_value("Loan", self.loan, ['loan_amount', 'total_principal_paid'])
		pending_principal_amount = loan_amount - principal_paid
		security_value = 0

		for security in self.securities:
			pledged_qty = pledge_qty_map.get(security.loan_security)

			if security.qty > pledged_qty:
				frappe.throw(_("""Row {0}: {1} {2} of {3} is pledged against Loan {4}.
					You are trying to unpledge more""").format(security.idx, pledged_qty, security.uom,
					frappe.bold(security.loan_security), frappe.bold(self.loan)))

			qty_after_unpledge = pledged_qty - security.qty
			ltv_ratio = ltv_ratio_map.get(security.loan_security_type)

			security_value += qty_after_unpledge * loan_security_price_map.get(security.loan_security)

		if not security_value and pending_principal_amount > 0:
			frappe.throw("Cannot Unpledge, loan to value ratio is breaching")

		if security_value and (pending_principal_amount/security_value) * 100 > ltv_ratio:
			frappe.throw("Cannot Unpledge, loan to value ratio is breaching")

	def on_update_after_submit(self):
		if self.status == "Approved":
			self.update_loan_status()
			self.db_set('unpledge_time', get_datetime())

	def update_loan_status(self, cancel=0):
		if cancel:
			loan_status = frappe.get_value('Loan', self.loan, 'status')
			if loan_status == 'Closed':
				frappe.db.set_value('Loan', self.loan, 'status', 'Loan Closure Requested')
		else:
			pledged_qty = 0
			current_pledges = get_pledged_security_qty(self.loan)

			for security, qty in iteritems(current_pledges):
				pledged_qty += qty

			if not pledged_qty:
				frappe.db.set_value('Loan', self.loan, 'status', 'Closed')

@frappe.whitelist()
def get_pledged_security_qty(loan):

	current_pledges = {}

	unpledges = frappe._dict(frappe.db.sql("""
		SELECT u.loan_security, sum(u.qty) as qty
		FROM `tabLoan Security Unpledge` up, `tabUnpledge` u
		WHERE up.loan = %s
		AND u.parent = up.name
		AND up.status = 'Approved'
		GROUP BY u.loan_security
	""", (loan)))

	pledges = frappe._dict(frappe.db.sql("""
		SELECT p.loan_security, sum(p.qty) as qty
		FROM `tabLoan Security Pledge` lp, `tabPledge`p
		WHERE lp.loan = %s
		AND p.parent = lp.name
		AND lp.status = 'Pledged'
		GROUP BY p.loan_security
	""", (loan)))

	for security, qty in iteritems(pledges):
		current_pledges.setdefault(security, qty)
		current_pledges[security] -= unpledges.get(security, 0.0)

	return current_pledges





