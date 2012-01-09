import webnotes
def execute():
	webnotes.conn.sql("""\
		DELETE FROM `tabProperty Setter`
		WHERE property='previous_field'
	""")
