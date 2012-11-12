import webnotes

def execute():
	webnotes.conn.sql("""delete from `tabSearch Criteria` 
		where name ='employee_leave_balance_report1'""")
	webnotes.conn.sql("""delete from `tabSearch Criteria` 
		where name ='employee_leave_balance_report2'""")