import webnotes
def execute():
	webnotes.conn.sql("""delete from tabDocPerm where parent='Appraisal'""")
	from webnotes.model.sync import sync
	sync("hr", "appraisal", force=True)