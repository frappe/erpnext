import webnotes, markdown2

def execute():
	webnotes.reload_doc("utilities", "doctype", "note")
	webnotes.reload_doc("utilities", "doctype", "note_user")
	
	for question in webnotes.conn.sql("""select * from tabQuestion""", as_dict=True):
		if question.question:
			try:
				name = question.question[:180]
				if webnotes.conn.exists("Note", name):
					webnotes.delete_doc("Note", name)
				note = webnotes.bean({
					"doctype":"Note",
					"title": name,
					"content": "<hr>".join([markdown2.markdown(c) for c in webnotes.conn.sql_list("""
						select answer from tabAnswer where question=%s""", question.name)]),
					"owner": question.owner,
					"creation": question.creation,
					"public": 1
				}).insert()
			except NameError:
				pass

	webnotes.delete_doc("DocType", "Question")
	webnotes.delete_doc("DocType", "Answer")
	webnotes.bean("Style Settings").save()
	
	# update comment delete
	webnotes.conn.sql("""update tabDocPerm \
		set cancel=1 where parent='Comment' and role='System Manager'""")
