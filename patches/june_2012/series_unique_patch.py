# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	"""add unique constraint to series table's name column"""
	import webnotes
	webnotes.conn.commit()
	webnotes.conn.sql("alter table `tabSeries` add unique (name)")
	webnotes.conn.begin()