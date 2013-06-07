import webnotes

def execute():
	for p in webnotes.conn.sql_list("""select name from tabProject"""):
		webnotes.bean("Project", p).controller.update_percent_complete()