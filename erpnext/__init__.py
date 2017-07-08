# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

__version__ = '8.3.5'

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


def get_company_currency(company):
	'''Returns the default company currency'''
	if not frappe.flags.company_currency:
		frappe.flags.company_currency = {}
	if not company in frappe.flags.company_currency:
		frappe.flags.company_currency[company] = frappe.db.get_value('Company', company, 'default_currency')
	return frappe.flags.company_currency[company]

def set_perpetual_inventory(enable=1, company=None):
	if not company:
		company = "_Test Company" if frappe.flags.in_test else get_default_company()

	company = frappe.get_doc("Company", company)
	company.enable_perpetual_inventory = enable
	company.save()

def encode_company_abbr(name, company):
	'''Returns name encoded with company abbreviation'''
	company_abbr = frappe.db.get_value("Company", company, "abbr")
	parts = name.rsplit(" - ", 1)

	if parts[-1].lower() != company_abbr.lower():
		parts.append(company_abbr)

	return " - ".join(parts)

def is_perpetual_inventory_enabled(company):
	if not company:
		company = "_Test Company" if frappe.flags.in_test else get_default_company()

	if not hasattr(frappe.local, 'enable_perpetual_inventory'):
		frappe.local.enable_perpetual_inventory = {}

	if not company in frappe.local.enable_perpetual_inventory:
		frappe.local.enable_perpetual_inventory[company] = frappe.db.get_value("Company",
			company, "enable_perpetual_inventory") or 0

	return frappe.local.enable_perpetual_inventory[company]
