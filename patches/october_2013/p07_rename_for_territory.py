# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes, os

def execute():
	webnotes.reload_doc("core", "doctype", "doctype")

	tables = webnotes.conn.sql_list("show tables")
	
	if "tabApplicable Territory" not in tables:
		webnotes.rename_doc("DocType", "For Territory", "Applicable Territory", force=True)
	
	webnotes.reload_doc("setup", "doctype", "applicable_territory")
	
	if os.path.exists("app/setup/doctype/for_territory"):
		os.system("rm -rf app/setup/doctype/for_territory")
	
	if webnotes.conn.exists("DocType", "For Territory"):
			webnotes.delete_doc("DocType", "For Territory")