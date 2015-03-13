# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, throw
from frappe.utils import flt

def get_company_currency(company):
	currency = frappe.db.get_value("Company", company, "default_currency")
	if not currency:
		currency = frappe.db.get_default("currency")
	if not currency:
		throw(_('Please specify Default Currency in Company Master and Global Defaults'))

	return currency

def get_root_of(doctype):
	"""Get root element of a DocType with a tree structure"""
	result = frappe.db.sql_list("""select name from `tab%s`
		where lft=1 and rgt=(select max(rgt) from `tab%s` where docstatus < 2)""" %
		(doctype, doctype))
	return result[0] if result else None

def get_ancestors_of(doctype, name):
	"""Get ancestor elements of a DocType with a tree structure"""
	lft, rgt = frappe.db.get_value(doctype, name, ["lft", "rgt"])
	result = frappe.db.sql_list("""select name from `tab%s`
		where lft<%s and rgt>%s order by lft desc""" % (doctype, "%s", "%s"), (lft, rgt))
	return result or []

def before_tests():
	frappe.clear_cache()
	# complete setup if missing
	from erpnext.setup.page.setup_wizard.setup_wizard import setup_account
	if not frappe.get_list("Company"):
		setup_account({
			"currency"			:"USD",
			"first_name"		:"Test",
			"last_name"			:"User",
			"company_name"		:"Wind Power LLC",
			"timezone"			:"America/New_York",
			"company_abbr"		:"WP",
			"industry"			:"Manufacturing",
			"country"			:"United States",
			"fy_start_date"		:"2014-01-01",
			"fy_end_date"		:"2014-12-31",
			"language"			:"english",
			"company_tagline"	:"Testing",
			"email"				:"test@erpnext.com",
			"password"			:"test",
			"chart_of_accounts" : "Standard"
		})

	frappe.db.sql("delete from `tabLeave Allocation`")
	frappe.db.sql("delete from `tabLeave Application`")
	frappe.db.sql("delete from `tabSalary Slip`")
	frappe.db.sql("delete from `tabItem Price`")
	frappe.db.commit()

def get_exchange_rate(from_currency, to_currency):
	exchange = "%s-%s" % (from_currency, to_currency)
	return flt(frappe.db.get_value("Currency Exchange", exchange, "exchange_rate"))
