# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
def get_price_list_currency(price_list_name):
	return {"price_list_currency": webnotes.conn.get_value("Price List", price_list_name, 
		"currency")}