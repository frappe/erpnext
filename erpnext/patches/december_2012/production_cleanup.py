# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	delete_doctypes()
	rename_module()
	cleanup_bom()
	rebuild_exploded_bom()
	
def delete_doctypes():
	from webnotes.model import delete_doc
	delete_doc("DocType", "Production Control")
	delete_doc("DocType", "BOM Control")
	
	
def rename_module():
	webnotes.reload_doc("core", "doctype", "role")
	webnotes.reload_doc("core", "doctype", "page")
	webnotes.reload_doc("core", "doctype", "module_def")

	if webnotes.conn.exists("Role", "Production User"):
		webnotes.rename_doc("Role", "Production User", "Manufacturing User")
	if webnotes.conn.exists("Role", "Production Manager"):
		webnotes.rename_doc("Role", "Production Manager", "Manufacturing Manager")

	if webnotes.conn.exists("Page", "manufacturing-home"):
		webnotes.delete_doc("Page", "production-home")
	else:
		webnotes.rename_doc("Page", "production-home", "manufacturing-home")

	if webnotes.conn.exists("Module Def", "Production"):
		webnotes.rename_doc("Module Def", "Production", "Manufacturing")
	
	modules_list = webnotes.conn.get_global('modules_list')
	if modules_list:
		webnotes.conn.set_global("modules_list", modules_list.replace("Production", 
			"Manufacturing"))
		
	# set end of life to null if "0000-00-00"
	webnotes.conn.sql("""update `tabItem` set end_of_life=null where end_of_life='0000-00-00'""")
	
def rebuild_exploded_bom():
	from webnotes.model.code import get_obj
	for bom in webnotes.conn.sql("""select name from `tabBOM` where docstatus < 2"""):
		get_obj("BOM", bom[0], with_children=1).on_update()

def cleanup_bom():
	webnotes.conn.sql("""UPDATE `tabBOM` SET is_active = 1 where ifnull(is_active, 'No') = 'Yes'""")
	webnotes.conn.sql("""UPDATE `tabBOM` SET is_active = 0 where ifnull(is_active, 'No') = 'No'""")
	webnotes.reload_doc("manufacturing", "doctype", "bom")
	webnotes.conn.sql("""update `tabBOM` set with_operations = 1""")
	