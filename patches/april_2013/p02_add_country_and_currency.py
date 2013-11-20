# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	if not webnotes.conn.exists("Country", "Aruba"):
		webnotes.bean({
			"doctype": "Country",
			"country_name": "Aruba",
			"time_zones": "America/Aruba",
			"date_format": "mm-dd-yyyy"
		}).insert()
		
	if not webnotes.conn.exists("Currency", "AWG"):
		webnotes.bean({
			"doctype": "Currency",
			"currency_name": "AWG",
			"fraction": "Cent",
			"fraction_units": 100,
			"symbol": "Afl",
			"number_format": "#,###.##"
		}).insert()
	