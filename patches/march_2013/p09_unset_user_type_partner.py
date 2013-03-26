import webnotes

def execute():
	webnotes.conn.sql("""update `tabProfile` set user_type='System User'
		where user_type='Partner' and exists (select name from `tabUserRole`
			where parent=`tabProfile`.name)""")