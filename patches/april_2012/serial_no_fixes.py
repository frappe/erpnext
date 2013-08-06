# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.modules import reload_doc
	reload_doc('stock', 'doctype', 'serial_no')

	webnotes.conn.sql("update `tabSerial No` set sle_exists = 1")
