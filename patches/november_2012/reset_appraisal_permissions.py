import webnotes
def execute():
	webnotes.conn.sql("""delete from tabDocPerm where parent='Appraisal'""")