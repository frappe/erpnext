import webnotes
def execute():
	from patches.april_2013.p05_update_file_data import update_file_list, get_single_doctypes
	
	singles = get_single_doctypes()
	for doctype in webnotes.conn.sql_list("""select table_name from `information_schema`.`columns`
		where table_schema=%s and column_name='file_list'""", webnotes.conn.cur_db_name):
			doctype = doctype[3:]
			
			if not webnotes.conn.exists("DocType", doctype): continue
			
			update_file_list(doctype, singles)
			
			webnotes.conn.sql("""delete from `tabCustom Field` where fieldname='file_list'
				and parent=%s""", doctype)
	