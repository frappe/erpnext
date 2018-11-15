# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import inspect
import frappe
from erpnext.hooks import regional_overrides
from frappe.utils import getdate

__version__ = '10.1.72'

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

def get_default_cost_center(company):
	'''Returns the default cost center of the company'''
	if not company:
		return None

	if not frappe.flags.company_cost_center:
		frappe.flags.company_cost_center = {}
	if not company in frappe.flags.company_cost_center:
		frappe.flags.company_cost_center[company] = frappe.db.get_value('Company', company, 'cost_center')
	return frappe.flags.company_cost_center[company]

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

def get_region(company=None):
	'''Return the default country based on flag, company or global settings

	You can also set global company flag in `frappe.flags.company`
	'''
	if company or frappe.flags.company:
		return frappe.db.get_value('Company',
			company or frappe.flags.company, 'country')
	elif frappe.flags.country:
		return frappe.flags.country
	else:
		return frappe.get_system_settings('country')

def allow_regional(fn):
	'''Decorator to make a function regionally overridable

	Example:
	@erpnext.allow_regional
	def myfunction():
	  pass'''
	def caller(*args, **kwargs):
		region = get_region()
		fn_name = inspect.getmodule(fn).__name__ + '.' + fn.__name__
		if region in regional_overrides and fn_name in regional_overrides[region]:
			return frappe.get_attr(regional_overrides[region][fn_name])(*args, **kwargs)
		else:
			return fn(*args, **kwargs)

	return caller

def get_last_membership():
	'''Returns last membership if exists'''
	last_membership = frappe.get_all('Membership', 'name,to_date,membership_type',
		dict(member=frappe.session.user, paid=1), order_by='to_date desc', limit=1)

	return last_membership and last_membership[0]

def is_member():
	'''Returns true if the user is still a member'''
	last_membership = get_last_membership()
	if last_membership and getdate(last_membership.to_date) > getdate():
		return True
	return False