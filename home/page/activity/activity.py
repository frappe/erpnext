# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

@webnotes.whitelist()
def get_feed(arg=None):
	"""get feed"""	
	return webnotes.conn.sql("""select
		distinct t1.name, t1.feed_type, t1.doc_type, t1.doc_name, t1.subject, t1.owner,
		t1.modified
		from tabFeed t1, tabDocPerm t2
		where t1.doc_type = t2.parent
		and t2.role in ('%s')
		and t2.permlevel = 0
		and ifnull(t2.`read`,0) = 1
		order by t1.modified desc
		limit %s, %s""" % ("','".join(webnotes.get_roles()), 
			webnotes.form_dict['limit_start'], webnotes.form_dict['limit_page_length']), 
			as_dict=1)