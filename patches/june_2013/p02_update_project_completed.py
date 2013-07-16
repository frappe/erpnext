import webnotes

def execute():
	webnotes.reload_doc("projects", "doctype", "project")
	for p in webnotes.conn.sql_list("""select name from tabProject"""):
		webnotes.bean("Project", p).controller.update_percent_complete()