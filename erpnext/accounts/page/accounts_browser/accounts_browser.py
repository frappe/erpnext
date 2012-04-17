import webnotes

@webnotes.whitelist()
def get_companies():
	return [r[0] for r in webnotes.conn.sql("""select name from tabCompany where docstatus!=2""")]
	
@webnotes.whitelist()
def get_children():
	args = webnotes.form_dict
	ctype = args['ctype']
	company_field = ctype=='Account' and 'company' or 'company_name'
	
	# root
	if args['parent'] in get_companies():
		return webnotes.conn.sql("""select 
			name as value, if(group_or_ledger='Group', 1, 0) as expandable
			from `tab%s`
			where ifnull(parent_%s,'') = ''
			and %s = %s
			and docstatus<2 
			order by name""" % (ctype, ctype.lower().replace(' ','_'), company_field, '%s'),
				args['parent'], as_dict=1)
	
	# other
	return webnotes.conn.sql("""select 
		name as value, if(group_or_ledger='Group', 1, 0) as expandable
	 	from `tab%s` 
		where ifnull(parent_%s,'') = %s
		and docstatus<2 
		order by name""" % (ctype, ctype.lower().replace(' ','_'), '%s'),
			args['parent'], as_dict=1)