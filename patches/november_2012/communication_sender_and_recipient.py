# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("core", "doctype", "communication")
	webnotes.conn.sql("""update tabCommunication set sender=email_address 
		where ifnull(support_ticket,'') != ''""")
	webnotes.conn.sql("""update tabCommunication set recipients=email_address where
		ifnull(sender,'')=''""")