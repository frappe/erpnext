import webnotes

@webnotes.whitelist()
def get_chart():
	company = webnotes.form_dict.get('company')
	res = {}
	res["chart"] = webnotes.conn.sql("""select name, parent_account, 
		if(debit_or_credit="Debit", "D", ""), 
		if(is_pl_account="Yes", "Y", "") from 
		tabAccount where company=%s and docstatus < 2 order by lft""", (company, ))