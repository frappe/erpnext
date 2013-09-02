import webnotes

def execute():
	for doctype in ("Contact", "Lead", "Job Applicant", "Supplier", "Customer", "Quotation", "Sales Person", "Support Ticket"):
		fieldname = doctype.replace(" ", '_').lower()
		webnotes.conn.sql("""update tabCommunication
			set parenttype=%s, parentfield='communications', 
			parent=`%s` 
			where ifnull(`%s`, '')!=''""" % ("%s", fieldname, fieldname), doctype)
			
		webnotes.reload_doc("core", "doctype", "communication")
			
		webnotes.conn.sql("""update tabCommunication set communication_date = creation where 
			ifnull(communication_date, '')='' """)
	