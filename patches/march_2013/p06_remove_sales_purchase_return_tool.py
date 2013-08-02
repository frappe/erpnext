# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.delete_doc("DocType", "Sales and Purchase Return Item")
	webnotes.delete_doc("DocType", "Sales and Purchase Return Tool")