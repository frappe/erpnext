# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact

class HealthcareInsuranceCompany(Document):
	def after_insert(self):
		self.create_customer()
		self.reload()

	def onload(self):
		load_address_and_contact(self)

	def create_customer(self):
		accounts = []

		if self.insurance_company_receivable_account:
			accounts.append({
				'account': self.insurance_company_receivable_account,
				'company': self.company
			})

		customer_group = frappe.db.exists('Customer Group', {'customer_group_name': _('Healthcare Insurance Company')})
		if not customer_group:
			customer_group = frappe.get_doc({
				'customer_group_name': 'Healthcare Insurance Company',
				'parent_customer_group': 'All Customer Groups',
				'doctype': 'Customer Group'
			}).insert(ignore_permissions=True, ignore_mandatory=True)

		customer = frappe.get_doc({
			'doctype': 'Customer',
			'customer_name': self.insurance_company_name,
			'customer_group': customer_group or frappe.db.get_single_value('Selling Settings', 'customer_group'),
			'territory': frappe.db.get_single_value('Selling Settings', 'territory'),
			'customer_type': 'Company',
			'accounts': accounts
		}).insert(ignore_permissions=True, ignore_mandatory=True)

		self.db_set('customer', customer.name)
		frappe.msgprint(_('Customer {0} is created.').format(customer.name), alert=True)