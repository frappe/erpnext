import webnotes

def execute():
	webnotes.reload_doc("support", "doctype", "communication")
	webnotes.conn.sql("""update tabCommunication set sender=email_address 
		where ifnull(support_ticket,'') != ''""")
	webnotes.conn.sql("""update tabCommunication set recipients=email_address where
		ifnull(sender,'')=''""")