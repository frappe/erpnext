# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
from accounts.utils import get_fiscal_year, FiscalYearError

def execute():
	webnotes.reload_doc("stock", "doctype", "stock_entry")
	webnotes.reload_doc("stock", "doctype", "stock_reconciliation")
	
	for doctype in ["Stock Entry", "Stock Reconciliation"]:
		for name, posting_date in webnotes.conn.sql("""select name, posting_date from `tab%s`
				where ifnull(fiscal_year,'')='' and docstatus=1""" % doctype):
			try:
				fiscal_year = get_fiscal_year(posting_date, 0)[0]
				webnotes.conn.sql("""update `tab%s` set fiscal_year=%s where name=%s""" % \
					(doctype, "%s", "%s"), (fiscal_year, name))
			except FiscalYearError:
				pass
			
	