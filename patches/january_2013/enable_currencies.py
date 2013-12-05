# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	# get all currencies
	webnotes.reload_doc("setup", "doctype", "currency")
	clist = [webnotes.conn.get_default("currency")]
	for f in webnotes.conn.sql("""select parent, fieldname from tabDocField 
		where options in ('Currency', 'link:Currency')""", as_dict=1):
		if not webnotes.conn.get_value("DocType", f.parent, "issingle"):
			clist += [c[0] for c in webnotes.conn.sql("""select distinct `%s`
				from `tab%s`""" % (f.fieldname, f.parent))]

	clist = list(set(clist))
	for c in clist:
		if c:
			webnotes.conn.sql("""update tabCurrency set `enabled`=1 where name=%s""", c)
