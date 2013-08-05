# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocField` set `default` = '' where fieldname = 'cost_center' and parent = 'RV Detail' and `default` = 'Purchase - TC'")
