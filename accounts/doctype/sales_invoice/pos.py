# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

@webnotes.whitelist()
def get_items(item_group=None):
	condition = ""
	
	if item_group and item_group != "All Item Groups":
		condition = "where item_group='%s'" % item_group

	return webnotes.conn.sql("""select name, item_name, image, sales_rate, barcode 
		from `tabItem` %s""" % (condition), as_dict=1)