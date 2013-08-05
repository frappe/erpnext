# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	"""delete entries of child table having parent like old_par%% or ''"""
	import webnotes
	res = webnotes.conn.sql("""\
		select dt.name from `tabDocType` dt
		where ifnull(dt.istable, 0)=1 and
		exists (
			select * from `tabDocField` df
			where df.fieldtype='Table' and
			df.options=dt.name
		)""")
	for r in res:
		if r[0]:
			webnotes.conn.sql("""\
				delete from `tab%s`
				where (ifnull(parent, '')='' or parent like "old_par%%") and
				ifnull(parenttype, '')!=''""" % r[0])