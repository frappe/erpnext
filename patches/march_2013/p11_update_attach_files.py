# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	for f in webnotes.conn.sql("""select parent, fieldname 
		from tabDocField where options="attach_files:" """, as_dict=1):
		if webnotes.conn.get_value("DocType", f.parent, "issingle"):
			fname = webnotes.conn.get_value(f.parent, None, f.fieldname)
			if fname:
				if not (fname.startswith("http") or fname.startswith("files")):
					webnotes.conn.set_value(f.parent, None, f.fieldname, "files/" + fname)
		else:
			webnotes.conn.sql("""update `tab%(parent)s`
				set %(fieldname)s = 
					if(substr(%(fieldname)s,1,4)='http' or substr(%(fieldname)s,1,5)='files',
					 	%(fieldname)s, 
						concat('files/', %(fieldname)s))""" % f)