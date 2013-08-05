# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.conn.commit()
	try:
		webnotes.conn.sql("""alter table `tabStock Ledger Entry` add index posting_sort_index(posting_date, posting_time, name)""")
		webnotes.conn.commit()
	except Exception, e:
		if e.args[0]!=1061: raise e
	webnotes.conn.begin()
	