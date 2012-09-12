import webnotes

@webnotes.whitelist()
def get_chart():
	company = webnotes.form_dict.get('company')
	return webnotes.conn.sql("""select name, parent_account from 
		tabAccount where company=%s and docstatus < 2 order by lft""", company)

@webnotes.whitelist()
def get_companies():
	"""get a list of companies based on permission"""
	
	# check if match permission exists
	res = webnotes.conn.sql("""select role, `match` from `tabDocPerm`
		where parent='Account' and permlevel=0 and `read`=1""", as_dict=1)
		
	match = any((r["match"] for r in res 
		if r["role"] in webnotes.user.roles and r["match"]=="company"))
	
	# if match == company is specified and companies are specified in user defaults
	if match and webnotes.user.get_defaults().get("company"):
		return webnotes.user.get_defaults().get("company")
	else:
		return [r[0] for r in webnotes.conn.sql("""select name from tabCompany
			where docstatus!=2""")]
