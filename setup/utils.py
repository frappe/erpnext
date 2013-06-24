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
		where lft=1 and rgt=(select max(rgt) from `tab%s`)""" % (doctype, doctype))
	return result[0] if result else None
	
def get_ancestors_of(doctype, name):
	"""Get ancestor elements of a DocType with a tree structure"""
	lft, rgt = webnotes.conn.get_value(doctype, name, ["lft", "rgt"])
	result = webnotes.conn.sql_list("""select name from `tab%s` 
		where lft<%s and rgt>%s""" % (doctype, "%s", "%s"), (lft, rgt))
	return result or None

@webnotes.whitelist()
def get_price_list_currency(args):
	"""
		args = {
			"price_list_name": "Something",
			"buying_or_selling": "Buying" or "Selling"
		}
	"""
	if isinstance(args, basestring):
		args = json.loads(args)
	
	result = webnotes.conn.sql("""select distinct ref_currency from `tabItem Price`
		where price_list_name=%s and buying_or_selling=%s""",
		(args.get("price_list_name"), args.get("buying_or_selling")))
	if result and len(result)==1:
		return {"price_list_currency": result[0][0]}
	else:
		return {}