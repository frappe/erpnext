import webnotes

def execute():
	webnotes.reload_doc("core", "doctype", "doctype")
	webnotes.rename_doc("DocType", "Purchase Request Item", "Material Request Item", force=True)
	webnotes.rename_doc("DocType", "Purchase Request", "Material Request", force=True)