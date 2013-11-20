# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes

def execute():
	from webnotes.country_info import get_all
	data = get_all()

	webnotes.reload_doc("setup", "doctype", "country")
	webnotes.reload_doc("setup", "doctype", "currency")	
	
	for c in webnotes.conn.sql("""select name from tabCountry"""):
		if c[0] in data:
			info = webnotes._dict(data[c[0]])
			doc = webnotes.doc("Country", c[0])
			doc.date_format = info.date_format or "dd-mm-yyyy"
			doc.time_zones = "\n".join(info.timezones or [])
			doc.save()
			
			if webnotes.conn.exists("Currency", info.currency):
				doc = webnotes.doc("Currency", info.currency)
				doc.fields.update({
					"fraction": info.currency_fraction,
					"symbol": info.currency_symbol,
					"fraction_units": info.currency_fraction_units
				})
				doc.save()
