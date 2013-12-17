# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes, os, shutil
	from webnotes.utils import get_base_path
	
	webnotes.delete_doc('Page', 'stock-ledger')
	webnotes.delete_doc('Page', 'stock-ageing')
	webnotes.delete_doc('Page', 'stock-level')
	webnotes.delete_doc('Page', 'general-ledger')
	
	for d in [["stock", "stock_ledger"], ["stock", "stock_ageing"],
		 	["stock", "stock_level"], ["accounts", "general_ledger"]]:
		path = os.path.join(get_base_path(), "app", d[0], "page", d[1])
		if os.path.exists(path):
			shutil.rmtree(path)