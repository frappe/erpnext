# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes, os
	
	webnotes.delete_doc('Page', 'stock-ledger')
	webnotes.delete_doc('Page', 'stock-ageing')
	webnotes.delete_doc('Page', 'stock-level')
	webnotes.delete_doc('Page', 'general-ledger')
	
	os.system("rm -rf app/stock/page/stock_ledger")
	os.system("rm -rf app/stock/page/stock_ageing")
	os.system("rm -rf app/stock/page/stock_level")
	os.system("rm -rf app/accounts/page/general_ledger")