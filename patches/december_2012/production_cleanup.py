import webnotes

def execute():
	delete_doctypes()
	rename_module()
	
def delete_doctypes():
	from webnotes.model import delete_doc
	delete_doc("DocType", "Production Control")
	delete_doc("DocType", "BOM Control")
	
def rename_module():
	webnotes.reload_doc("core", "doctype", "role")
	webnotes.reload_doc("core", "doctype", "page")
	webnotes.reload_doc("core", "doctype", "module_def")

	webnotes.rename_doc("Role", "Production User", "Manufacturing User")
	webnotes.rename_doc("Role", "Production Manager", "Manufacturing Manager")

	if webnotes.conn.exists("Page", "manufacturing-home"):
		webnotes.delete_doc("Page", "production-home")
	else:
		webnotes.rename_doc("Page", "production-home", "manufacturing-home")

	webnotes.rename_doc("Module Def", "Production", "Manufacturing")
	
	webnotes.conn.set_global("modules_list",
		webnotes.conn.get_global('modules_list').replace("Production", "Manufacturing"))
	
	