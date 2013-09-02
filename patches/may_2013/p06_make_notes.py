# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

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

				similar_questions = webnotes.conn.sql_list("""select name from `tabQuestion`
					where question like %s""", "%s%%" % name)
				answers = [markdown2.markdown(c) for c in webnotes.conn.sql_list("""
						select answer from tabAnswer where question in (%s)""" % \
						", ".join(["%s"]*len(similar_questions)), similar_questions)]

				webnotes.bean({
					"doctype":"Note",
					"title": name,
					"content": "<hr>".join(answers),
					"owner": question.owner,
					"creation": question.creation,
					"public": 1
				}).insert()
			
			except NameError:
				pass
			except Exception, e:
				if e.args[0] != 1062:
					raise e

	webnotes.delete_doc("DocType", "Question")
	webnotes.delete_doc("DocType", "Answer")
	webnotes.bean("Style Settings").save()
	
	# update comment delete
	webnotes.conn.sql("""update tabDocPerm \
		set cancel=1 where parent='Comment' and role='System Manager'""")
