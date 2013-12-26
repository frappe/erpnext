# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint
import json

def get_company_currency(company):
	currency = webnotes.conn.get_value("Company", company, "default_currency")
	if not currency:
		currency = webnotes.conn.get_default("currency")
	if not currency:
		msgprint(_('Please specify Default Currency in Company Master \
			and Global Defaults'), raise_exception=True)
		
	return currency

def get_root_of(doctype):
	"""Get root element of a DocType with a tree structure"""
	result = webnotes.conn.sql_list("""select name from `tab%s` 
		where lft=1 and rgt=(select max(rgt) from `tab%s` where docstatus < 2)""" % 
		(doctype, doctype))
	return result[0] if result else None
	
def get_ancestors_of(doctype, name):
	"""Get ancestor elements of a DocType with a tree structure"""
	lft, rgt = webnotes.conn.get_value(doctype, name, ["lft", "rgt"])
	result = webnotes.conn.sql_list("""select name from `tab%s` 
		where lft<%s and rgt>%s order by lft desc""" % (doctype, "%s", "%s"), (lft, rgt))
	return result or []

@webnotes.whitelist()
def get_price_list_currency(price_list):
	return {"price_list_currency": webnotes.conn.get_value("Price List", price_list, 
		"currency")}