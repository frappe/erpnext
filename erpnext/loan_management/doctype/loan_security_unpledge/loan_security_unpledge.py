# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, flt, getdate
import json
from six import iteritems
from erpnext.loan_management.doctype.loan_security_price.loan_security_price import get_loan_security_price

class LoanSecurityUnpledge(Document):
	def validate(self):
		self.validate_duplicate_securities()
		self.validate_unpledge_qty()

	def on_cancel(self):
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
		from erpnext.loan_management.doctype.loan_security_shortfall.loan_security_shortfall import get_ltv_ratio

		pledge_qty_map = get_pledged_security_qty(self.loan)

		ltv_ratio_map = frappe._dict(frappe.get_all("Loan Security Type",
			fields=["name", "loan_to_value_ratio"], as_list=1))

		loan_security_price_map = frappe._dict(frappe.get_all("Loan Security Price",
			fields=["loan_security", "loan_security_price"],
			filters = {
				"valid_from": ("<=", get_datetime()),
				"valid_upto": (">=", get_datetime())
			}, as_list=1))

		loan_details = frappe.get_value("Loan", self.loan, ['total_payment', 'total_principal_paid',
			'total_interest_payable', 'written_off_amount', 'disbursed_amount', 'status'], as_dict=1)

		if loan_details.status == 'Disbursed':
			pending_principal_amount = flt(loan_details.total_payment) - flt(loan_details.total_interest_payable) \
				- flt(loan_details.total_principal_paid) - flt(loan_details.written_off_amount)
		else:
			pending_principal_amount = flt(loan_details.disbursed_amount) - flt(loan_details.total_interest_payable) \
				- flt(loan_details.total_principal_paid) - flt(loan_details.written_off_amount)

		security_value = 0
		unpledge_qty_map = {}
		ltv_ratio = 0

		for security in self.securities:
			pledged_qty = pledge_qty_map.get(security.loan_security, 0)
			if security.qty > pledged_qty:
				msg = _("Row {0}: {1} {2} of {3} is pledged against Loan {4}.").format(security.idx, pledged_qty, security.uom,
					frappe.bold(security.loan_security), frappe.bold(self.loan))
				msg += "<br>"
				msg += _("You are trying to unpledge more.")
				frappe.throw(msg, title=_("Loan Security Unpledge Error"))

			unpledge_qty_map.setdefault(security.loan_security, 0)
			unpledge_qty_map[security.loan_security] += security.qty

		for security in pledge_qty_map:
			if not ltv_ratio:
				ltv_ratio = get_ltv_ratio(security)

			qty_after_unpledge = pledge_qty_map.get(security, 0) - unpledge_qty_map.get(security, 0)
			current_price = loan_security_price_map.get(security)
			security_value += qty_after_unpledge * current_price

		if not security_value and flt(pending_principal_amount, 2) > 0:
			self._throw(security_value, pending_principal_amount, ltv_ratio)

		if security_value and flt(pending_principal_amount/security_value) * 100 > ltv_ratio:
			self._throw(security_value, pending_principal_amount, ltv_ratio)

	def _throw(self, security_value, pending_principal_amount, ltv_ratio):
		msg = _("Loan Security Value after unpledge is {0}").format(frappe.bold(security_value))
		msg += '<br>'
		msg += _("Pending principal amount is {0}").format(frappe.bold(flt(pending_principal_amount, 2)))
		msg += '<br>'
		msg += _("Loan To Security Value ratio must always be {0}").format(frappe.bold(ltv_ratio))
		frappe.throw(msg, title=_("Loan To Value ratio breach"))

	def on_update_after_submit(self):
		self.approve()

	def approve(self):
		if self.status == "Approved" and not self.unpledge_time:
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
				frappe.db.set_value('Loan', self.loan,
					{
						'status': 'Closed',
						'closure_date': getdate()
					})

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





