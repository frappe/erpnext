# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("accounts", "doctype", "fiscal_year")

	webnotes.conn.sql("""update `tabFiscal Year` set year_end_date = 
		subdate(adddate(year_start_date, interval 1 year), interval 1 day)""")