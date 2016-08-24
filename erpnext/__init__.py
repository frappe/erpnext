# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

__version__ = '7.1.0-beta'

def get_default_company(user=None):
	'''Get default company for user'''
	from frappe.defaults import get_user_default_as_list

	if not user:
		user = frappe.session.user

	companies = get_user_default_as_list(user, 'company')
	if companies:
		default_company = companies[0]
	else:
		default_company = frappe.db.get_single_value('Global Defaults', 'default_company')

	return default_company

def get_default_currency():
	'''Returns the currency of the default company'''
	company = get_default_company()
	if company:
		return frappe.db.get_value('Company', company, 'default_currency')
