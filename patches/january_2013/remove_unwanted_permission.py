# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	for dt in webnotes.conn.sql("""select name, issingle from tabDocType"""):
		if dt[1]:
			webnotes.conn.sql("""update tabDocPerm set report = 0 where parent = %s""", dt[0])
		
		
		doctype = webnotes.bean("DocType", dt[0])
		for pl in [1, 2, 3]:
			if not doctype.doclist.get({"doctype": "DocField", "permlevel": pl}):
				if doctype.doclist.get({"doctype":"DocPerm", "permlevel":pl}):
					webnotes.conn.sql("""delete from `tabDocPerm` 
						where parent = %s and permlevel = %s""", (dt[0], pl))