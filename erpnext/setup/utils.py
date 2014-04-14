# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, throw
import json

def get_company_currency(company):
	currency = frappe.db.get_value("Company", company, "default_currency")
	if not currency:
		currency = frappe.db.get_default("currency")
	if not currency:
		throw(_('Please specify Default Currency in Company Master \
			and Global Defaults'))

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

@frappe.whitelist()
def get_price_list_currency(price_list):
	price_list_currency = frappe.db.get_value("Price List", {"name": price_list,
		"enabled": 1}, "currency")

	if not price_list_currency:
		throw(_("Price List {0} is disabled").format(price_list))
	else:
		return {"price_list_currency": price_list_currency}
