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
		create_customer(self)
		self.reload()
	def	onload(self):
		load_address_and_contact(self)
def create_customer(doc):
	customer_group = frappe.db.exists('Customer Group',{
	'customer_group_name': 'Healthcare Insurance Company'})
	if not customer_group:
		customer_group=frappe.get_doc({
		'customer_group_name': 'Healthcare Insurance Company',
		'parent_customer_group': 'All Customer Groups',
		'doctype': 'Customer Group'
		}).insert().name
	territory = frappe.get_value('Selling Settings', None, 'territory')
	if not (territory):
		territory = 'Rest Of The World'
		frappe.msgprint(_('Please set default  territory in Selling Settings'), alert=True)
	customer = frappe.new_doc('Customer')
	customer.customer_name = doc.insurance_company_name
	customer.customer_group = customer_group
	customer.territory = territory
	customer.customer_type = 'Company'
	if doc.insurance_company_receivable_account:
		accounts = []
		accounts.append({
			'account': doc.insurance_company_receivable_account,
			'company': doc.company
		})
		customer.set('accounts', accounts)
	customer.save(ignore_permissions = True)
	frappe.db.set_value('Healthcare Insurance Company', doc.name, 'customer', customer.name)
	frappe.msgprint(_('Customer {0} is created.').format(customer.name), alert=True)
