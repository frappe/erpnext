import webnotes
from webnotes.utils import get_defaults, cstr

@webnotes.whitelist()
def get_companies():
	return [r[0] for r in webnotes.conn.sql("""select name from tabCompany where docstatus!=2""")]
	
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
			bal = webnotes.conn.sql("select balance from `tabAccount Balance` \
				where account = %s and period = %s", (each.get('value'), get_defaults('fiscal_year')))
			bal = bal and bal[0][0] or 0
			each['balance'] = currency + ' ' + cstr(bal)
		
	return acc
	

@webnotes.whitelist()		
def get_account_balance():
	args = webnotes.form_dict
	acc = args['acc']
	return 'Rs. 100'