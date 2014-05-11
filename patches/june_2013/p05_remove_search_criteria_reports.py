# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	try:
		webnotes.conn.sql("""delete from `tabSearch Criteria` where ifnull(standard, 'No') = 'Yes'""")
	except Exception, e:
		pass