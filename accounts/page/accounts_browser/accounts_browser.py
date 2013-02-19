from __future__ import unicode_literals
import webnotes
import webnotes.defaults

from accounts.utils import get_balance_on

@webnotes.whitelist()
def get_companies():
	"""get a list of companies based on permission"""
	
	# check if match permission exists
	res = webnotes.conn.sql("""select role, `match` from `tabDocPerm`
		where parent='Account' and permlevel=0 and `read`=1""", as_dict=1)
	
	roles = webnotes.user.get_roles()
	match = any((r["match"] for r in res 
		if r["role"] in roles and r["match"]=="company"))
	
	# if match == company is specified and companies are specified in user defaults
	if match:
		return webnotes.defaults.get_user_default_as_list("company")
	else:
		return [r[0] for r in webnotes.conn.sql("""select name from tabCompany
			where docstatus!=2""")]

@webnotes.whitelist()
def get_children():
	args = webnotes.form_dict
	ctype, company = args['ctype'], args['comp']
	
	company_field = ctype=='Account' and 'company' or 'company_name'

	# root
	if args['parent'] == company:
		acc = webnotes.conn.sql(""" select 
			name as value, if(group_or_ledger='Group', 1, 0) as expandable
			from `tab%s`
			where ifnull(parent_%s,'') = ''
			and %s = %s	and docstatus<2 
			order by name""" % (ctype, ctype.lower().replace(' ','_'), company_field, '%s'),
				args['parent'], as_dict=1)
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
			each['balance'] = currency + ' ' + str(bal or 0)
		
	return acc
