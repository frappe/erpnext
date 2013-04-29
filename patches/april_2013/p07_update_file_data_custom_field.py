import webnotes
def execute():
	from patches.april_2013.p05_update_file_data import update_file_list, get_single_doctypes
	singles = get_single_doctypes()
	for doctype in webnotes.conn.sql("""select parent from `tabCustom Field` where 
		fieldname='file_list' and fieldtype='Text'"""):
			update_file_list(doctype, singles)
			
			webnotes.conn.sql("""delete from `tabCustom Field` where fieldname='file_list'
					and parent=%s""", doctype)
	