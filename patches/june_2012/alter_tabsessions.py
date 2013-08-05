# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.commit()
	webnotes.conn.sql("alter table `tabSessions` modify user varchar(180)")
	webnotes.conn.begin()