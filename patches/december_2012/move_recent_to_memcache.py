# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes, json

def execute():
	for p in webnotes.conn.sql("""select name, recent_documents from 
		tabProfile where ifnull(recent_documents,'')!=''"""):
		if not '~~~' in p[1] and p[1][0]=='[':
			webnotes.cache().set_value("recent:" + p[0], json.loads(p[1]))