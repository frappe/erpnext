# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes

def execute():
	from webnotes.country_info import get_all
	data = get_all()

	webnotes.reload_doc("setup", "doctype", "currency")	
	
	for c in data:
		info = webnotes._dict(data[c])
		if webnotes.conn.exists("Currency", info.currency):
			doc = webnotes.doc("Currency", info.currency)
			doc.fields.update({
				"number_format": info.number_format,
			})
			doc.save()
