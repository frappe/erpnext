# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, flt
import json
from erpnext.loan_management.doctype.loan_security_price.loan_security_price import get_loan_security_price

class LoanSecurityUnpledge(Document):
	def validate(self):
		self.validate_pledges()
		self.validate_duplicate_securities()

	def on_cancel(self):
		self.update_loan_security_pledge(cancel=1)
		self.update_loan_status(cancel=1)
		self.db_set('status', 'Requested')

	def validate_duplicate_securities(self):
		security_list = []
		for d in self.securities:
			security = [d.loan_security, d.against_pledge]
			if security not in security_list:
				security_list.append(security)
			else:
				frappe.throw(_("Row {0}: Loan Security {1} against Loan Security Pledge {2} added multiple times").format(
					d.idx, frappe.bold(d.loan_security), frappe.bold(d.against_pledge)))

	def validate_pledges(self):
		pledge_qty_map = self.get_pledge_details()
		loan = frappe.get_doc("Loan", self.loan)

		remaining_qty = 0
		unpledge_value = 0

		for security in self.securities:
			pledged_qty = pledge_qty_map.get((security.against_pledge, security.loan_security), 0)
			if not pledged_qty:
				frappe.throw(_("Zero qty of {0} pledged against loan {1}").format(frappe.bold(security.loan_security),
					frappe.bold(self.loan)))

			unpledge_qty = pledged_qty - security.qty
			security_price = security.qty * get_loan_security_price(security.loan_security)

			if unpledge_qty < 0:
				frappe.throw(_("""Row {0}: Cannot unpledge more than {1} qty of {2} against
					Loan Security Pledge {3}""").format(security.idx, frappe.bold(pledged_qty),
					frappe.bold(security.loan_security), frappe.bold(security.against_pledge)))

			remaining_qty += unpledge_qty
			unpledge_value += security_price - flt(security_price * security.haircut/100)

		if unpledge_value > loan.total_principal_paid:
			frappe.throw(_("Cannot Unpledge, loan security value is greater than the repaid amount"))

	def get_pledge_details(self):
		pledge_qty_map = {}

		pledge_details = frappe.db.sql("""
			SELECT p.parent, p.loan_security, p.qty FROM
				`tabLoan Security Pledge` lsp,
				`tabPledge` p
			WHERE
				p.parent = lsp.name
				AND lsp.loan = %s
				AND lsp.docstatus = 1
				AND lsp.status in ('Pledged', 'Partially Pledged')
		""", (self.loan), as_dict=1)

		for pledge in pledge_details:
			pledge_qty_map.setdefault((pledge.parent, pledge.loan_security), pledge.qty)

		return pledge_qty_map

	def on_update_after_submit(self):
		if self.status == "Approved":
			self.update_loan_security_pledge()
			self.update_loan_status()

	def update_loan_security_pledge(self, cancel=0):
		if cancel:
			new_qty = 'p.qty + u.qty'
		else:
			new_qty = 'p.qty - u.qty'

		frappe.db.sql("""
			UPDATE
				`tabPledge` p, `tabUnpledge` u, `tabLoan Security Pledge` lsp, `tabLoan Security Unpledge` lsu
					SET p.qty = {new_qty}
			WHERE
				lsp.loan = %s
				AND p.parent = u.against_pledge
				AND p.parent = lsp.name
				AND lsp.docstatus = 1
				AND p.loan_security = u.loan_security""".format(new_qty=new_qty),(self.loan))

	def update_loan_status(self, cancel=0):
		if cancel:
			loan_status = frappe.get_value('Loan', self.loan, 'status')
			if loan_status == 'Closed':
				frappe.db.set_value('Loan', self.loan, 'status', 'Loan Closure Requested')
		else:
			pledge_qty = frappe.db.sql("""SELECT SUM(c.qty)
				FROM `tabLoan Security Pledge` p, `tabPledge` c
				WHERE p.loan = %s AND c.parent = p.name""", (self.loan))[0][0]

			if not pledge_qty:
				frappe.db.set_value('Loan', self.loan, 'status', 'Closed')

