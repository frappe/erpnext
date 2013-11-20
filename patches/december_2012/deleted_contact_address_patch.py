# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	"""finds references of deleted addresses and contacts and deletes these references"""
	import webnotes.model

	for dt in ["Address", "Contact"]:
		link_fields = webnotes.model.get_link_fields(dt)
		for parent, lf in link_fields:
			webnotes.conn.sql("""update `tab%s` ref set `%s`=null
				where ifnull(`%s`, '')!='' and not exists (
					select * from `tab%s` where name=ref.`%s`)""" % \
				(parent, lf, lf, dt, lf))