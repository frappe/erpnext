import webnotes, os

def execute():
	webnotes.delete_doc("DocType", "Product")
	webnotes.delete_doc("DocType", "Test")
	webnotes.delete_doc("Module Def", "Test")
	
	os.system("rm -rf app/test")
	os.system("rm -rf app/website/doctype/product")
	