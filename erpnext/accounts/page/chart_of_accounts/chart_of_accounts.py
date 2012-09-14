import webnotes

@webnotes.whitelist()
def get_chart():
	company = webnotes.form_dict.get('company')
	res = {}
	res["chart"] = webnotes.conn.sql("""select name, parent_account, 
		if(debit_or_credit="Debit", "D", ""), 
		if(is_pl_account="Yes", "Y", "") from 
		tabAccount where company=%s and docstatus < 2 order by lft""", (company, ))
		
	res["gl"] = webnotes.conn.sql("""select posting_date, account, ifnull(debit, 0), 
		ifnull(credit, 0), ifnull(is_opening, 'No')
		from `tabGL Entry` where company=%s and ifnull(is_cancelled, "No") = "No" 
		order by posting_date""", (company, ), as_list=1)

	idx_map = {}
	for i in xrange(len(res["chart"])):
		idx_map[res["chart"][i][0]] = i
	
	for d in res["gl"]:		
		d[1] = idx_map[d[1]]
		
	return res

@webnotes.whitelist()
def get_companies():
	"""get a list of companies based on permission"""
	
	# check if match permission exists
	res = webnotes.conn.sql("""select role, `match` from `tabDocPerm`
		where parent='Account' and permlevel=0 and `read`=1""", as_dict=1)
		
	match = any((r["match"] for r in res 
		if r["role"] in webnotes.user.roles and r["match"]=="company"))
	
	# if match == company is specified and companies are specified in user defaults
	res = {}
	if match and webnotes.user.get_defaults().get("company"):
		res["companies"] = webnotes.user.get_defaults().get("company")
	else:
		res["companies"] = [r[0] for r in webnotes.conn.sql("""select name from tabCompany
			where docstatus!=2""")]
	
	res["fiscal_years"] = webnotes.conn.sql("""select name, year_start_date, 
		adddate(year_start_date, interval 1 year)
		from `tabFiscal Year` where docstatus!=2 
		order by year_start_date asc""")
	return res
