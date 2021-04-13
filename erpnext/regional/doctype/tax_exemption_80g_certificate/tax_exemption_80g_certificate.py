# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, flt, get_link_to_form
from erpnext.accounts.utils import get_fiscal_year
from frappe.contacts.doctype.address.address import get_company_address

class TaxExemption80GCertificate(Document):
	def validate(self):
		self.validate_date()
		self.validate_duplicates()
		self.validate_company_details()
		self.set_company_address()
		self.calculate_total()
		self.set_title()

	def validate_date(self):
		if self.recipient == 'Member':
			if getdate(self.date):
				fiscal_year = get_fiscal_year(fiscal_year=self.fiscal_year, as_dict=True)

				if not (fiscal_year.year_start_date <= getdate(self.date) \
					<= fiscal_year.year_end_date):
					frappe.throw(_('The Certificate Date is not in the Fiscal Year {0}').format(frappe.bold(self.fiscal_year)))

	def validate_duplicates(self):
		if self.recipient == 'Donor':
			certificate = frappe.db.exists(self.doctype, {
				'donation': self.donation,
				'name': ('!=', self.name)
			})
			if certificate:
				frappe.throw(_('An 80G Certificate {0} already exists for the donation {1}').format(
					get_link_to_form(self.doctype, certificate), frappe.bold(self.donation)
				), title=_('Duplicate Certificate'))

	def validate_company_details(self):
		fields = ['company_80g_number', 'with_effect_from', 'pan_details']
		company_details = frappe.db.get_value('Company', self.company, fields, as_dict=True)
		if not company_details.company_80g_number:
			frappe.throw(_('Please set the {0} for company {1}').format(frappe.bold('80G Number'),
				get_link_to_form('Company', self.company)))

		if not company_details.pan_details:
			frappe.throw(_('Please set the {0} for company {1}').format(frappe.bold('PAN Number'),
				get_link_to_form('Company', self.company)))

	@frappe.whitelist()
	def set_company_address(self):
		address = get_company_address(self.company)
		self.company_address = address.company_address
		self.company_address_display = address.company_address_display

	def calculate_total(self):
		if self.recipient == 'Donor':
			return

		total = 0
		for entry in self.payments:
			total += flt(entry.amount)
		self.total = total

	def set_title(self):
		if self.recipient == 'Member':
			self.title = self.member_name
		else:
			self.title = self.donor_name

	@frappe.whitelist()
	def get_payments(self):
		if not self.member:
			frappe.throw(_('Please select a Member first.'))

		fiscal_year = get_fiscal_year(fiscal_year=self.fiscal_year, as_dict=True)

		memberships = frappe.db.get_all('Membership', {
			'member': self.member,
			'from_date': ['between', (fiscal_year.year_start_date, fiscal_year.year_end_date)],
			'to_date': ['between', (fiscal_year.year_start_date, fiscal_year.year_end_date)],
			'membership_status': ('!=', 'Cancelled')
		}, ['from_date', 'amount', 'name', 'invoice', 'payment_id'], order_by='from_date')

		if not memberships:
			frappe.msgprint(_('No Membership Payments found against the Member {0}').format(self.member))

		total = 0
		self.payments = []

		for doc in memberships:
			self.append('payments', {
				'date': doc.from_date,
				'amount': doc.amount,
				'invoice_id': doc.invoice,
				'razorpay_payment_id': doc.payment_id,
				'membership': doc.name
			})
			total += flt(doc.amount)

		self.total = total
