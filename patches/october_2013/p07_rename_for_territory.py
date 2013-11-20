# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes, os

def execute():
	from webnotes.utils import get_base_path
	import shutil
	webnotes.reload_doc("core", "doctype", "doctype")

	tables = webnotes.conn.sql_list("show tables")
	
	if "tabApplicable Territory" not in tables:
		webnotes.rename_doc("DocType", "For Territory", "Applicable Territory", force=True)
	
	webnotes.reload_doc("setup", "doctype", "applicable_territory")
	
	path = os.path.join(get_base_path(), "app", "setup", "doctype", "for_territory")
	if os.path.exists(path):
		shutil.rmtree(path)
	
	if webnotes.conn.exists("DocType", "For Territory"):
		webnotes.delete_doc("DocType", "For Territory")
