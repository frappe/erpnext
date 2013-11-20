# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	webnotes.reload_doc("setup", "doctype", "email_digest")
	webnotes.conn.sql('update `tabEmail Digest` set calendar_events=1, todo_list=1 where enabled=1')