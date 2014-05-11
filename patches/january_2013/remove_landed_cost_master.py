# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	webnotes.delete_doc("DocType", "Landed Cost Master")
	webnotes.delete_doc("DocType", "Landed Cost Master Detail")