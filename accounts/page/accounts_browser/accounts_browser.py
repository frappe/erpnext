# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
import webnotes.defaults
from webnotes.utils import flt
from accounts.utils import get_balance_on

@webnotes.whitelist()
def get_companies():
	"""get a list of companies based on permission"""
	return [d.name for d in webnotes.get_list("Company", fields=["name"], 
		order_by="name")]

@webnotes.whitelist()
def get_children():
	args = webnotes.local.form_dict
	ctype, company = args['ctype'], args['comp']
	
	# root
	if args['parent'] in ("Accounts", "Cost Centers"):
		acc = webnotes.conn.sql(""" select 
			name as value, if(group_or_ledger='Group', 1, 0) as expandable
			from `tab%s`
			where ifnull(parent_%s,'') = ''
			and `company` = %s	and docstatus<2 
			order by name""" % (ctype, ctype.lower().replace(' ','_'), '%s'),
				company, as_dict=1)
	else:	
		# other
		acc = webnotes.conn.sql("""select 
			name as value, if(group_or_ledger='Group', 1, 0) as expandable
	 		from `tab%s` 
			where ifnull(parent_%s,'') = %s
			and docstatus<2 
			order by name""" % (ctype, ctype.lower().replace(' ','_'), '%s'),
				args['parent'], as_dict=1)
				
	if ctype == 'Account':
		currency = webnotes.conn.sql("select default_currency from `tabCompany` where name = %s", company)[0][0]
		for each in acc:
			bal = get_balance_on(each.get("value"))
			each["currency"] = currency
			each["balance"] = flt(bal)
		
	return acc
