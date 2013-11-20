# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("projects", "doctype", "project")
	for p in webnotes.conn.sql_list("""select name from tabProject"""):
		webnotes.bean("Project", p).make_controller().update_percent_complete()