import webnotes, os, webnotes.utils

def execute():
	files_path = webnotes.utils.get_path("public", "files")
	for f in webnotes.conn.sql("""select name, file_name from 
		`tabFile Data`""", as_dict=True):
		if f.file_name:
			filepath = os.path.join(files_path, f.file_name)
			if os.path.exists(filepath):
				webnotes.conn.set_value("File Data", f.name, "file_size", os.stat(filepath).st_size)
			
		