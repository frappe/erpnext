import webnotes

def execute():
	webnotes.reload_doc("hr", "doctype", "leave_application")
	
	if not webnotes.get_doctype("Leave Application").get({"doctype": "DocField", 
			"parent": "Leave Application", "permlevel": 2}):
		webnotes.conn.sql("""update `tabDocPerm` set permlevel=1 
			where parent="Leave Application" and permlevel=2""")