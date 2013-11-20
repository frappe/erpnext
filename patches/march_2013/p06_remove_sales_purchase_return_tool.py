# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	if webnotes.conn.exists("DocType", "Sales and Purchase Return Item"):
		webnotes.delete_doc("DocType", "Sales and Purchase Return Item")
	if webnotes.conn.exists("DocType", "Sales and Purchase Return Tool"):
		webnotes.delete_doc("DocType", "Sales and Purchase Return Tool")