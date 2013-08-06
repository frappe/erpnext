# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes, os

def execute():
	webnotes.delete_doc("DocType", "Product")
	webnotes.delete_doc("DocType", "Test")
	webnotes.delete_doc("Module Def", "Test")
	
	os.system("rm -rf app/test")
	os.system("rm -rf app/website/doctype/product")
	