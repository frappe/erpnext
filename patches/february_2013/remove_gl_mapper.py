# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	try:
		for mapper in webnotes.conn.sql("""select name from `tabGL Mapper`"""):
			webnotes.delete_doc("GL Mapper", mapper[0])
	except Exception, e:
		pass