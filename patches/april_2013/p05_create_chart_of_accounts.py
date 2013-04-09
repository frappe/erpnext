import webnotes
def execute():
	for company in webnotes.conn.sql("select name from `tabCompany`"):
		if not webnotes.conn.sql("select * from `tabAccount` where company = %s", company[0]):
			webnotes.conn.sql("""update `tabCompany` set receivables_group = '', 
				payables_group = '' where name = %s""", company[0])
			webnotes.bean("Company", company[0]).save()