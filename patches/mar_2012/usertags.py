# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	doctype_list = webnotes.conn.sql("""SELECT name FROM `tabDocType`
		WHERE docstatus<2 AND IFNULL(issingle, 0)=0
		AND IFNULL(istable, 0)=0""")
	webnotes.conn.commit()
	for d in doctype_list:
		add_col = True
		desc = webnotes.conn.sql("DESC `tab%s`" % d[0], as_dict=1)
		for td in desc:
			if td.get('Field')=='_user_tags':
				add_col = False		

		if add_col:
			webnotes.conn.sql("alter table `tab%s` add column `_user_tags` varchar(180)" % d[0])
	webnotes.conn.begin()		

