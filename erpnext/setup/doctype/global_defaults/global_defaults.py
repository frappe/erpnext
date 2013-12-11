# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
"""Global Defaults"""
import webnotes
import webnotes.defaults
from webnotes.utils import cint

keydict = {
	# "key in defaults": "key in Global Defaults"
	"print_style": "print_style",
	"fiscal_year": "current_fiscal_year",
	'company': 'default_company',
	'currency': 'default_currency',
	'hide_currency_symbol':'hide_currency_symbol',
	'date_format': 'date_format',
	'number_format': 'number_format',
	'float_precision': 'float_precision',
	'account_url':'account_url',
	'session_expiry': 'session_expiry',
	'disable_rounded_total': 'disable_rounded_total',
}

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def on_update(self):
		"""update defaults"""
		self.validate_session_expiry()
		self.update_control_panel()
		
		for key in keydict:
			webnotes.conn.set_default(key, self.doc.fields.get(keydict[key], ''))
			
		# update year start date and year end date from fiscal_year
		year_start_end_date = webnotes.conn.sql("""select year_start_date, year_end_date 
			from `tabFiscal Year` where name=%s""", self.doc.current_fiscal_year)

		ysd = year_start_end_date[0][0] or ''
		yed = year_start_end_date[0][1] or ''

		if ysd and yed:
			webnotes.conn.set_default('year_start_date', ysd.strftime('%Y-%m-%d'))
			webnotes.conn.set_default('year_end_date', yed.strftime('%Y-%m-%d'))
		
		# enable default currency
		if self.doc.default_currency:
			webnotes.conn.set_value("Currency", self.doc.default_currency, "enabled", 1)
		
		# clear cache
		webnotes.clear_cache()
	
	def validate_session_expiry(self):
		if self.doc.session_expiry:
			parts = self.doc.session_expiry.split(":")
			if len(parts)!=2 or not (cint(parts[0]) or cint(parts[1])):
				webnotes.msgprint("""Session Expiry must be in format hh:mm""",
					raise_exception=1)

	def update_control_panel(self):
		cp_bean = webnotes.bean("Control Panel")
		if self.doc.country:
			cp_bean.doc.country = self.doc.country
		if self.doc.time_zone:
			cp_bean.doc.time_zone = self.doc.time_zone
		cp_bean.ignore_permissions = True
		cp_bean.save()

	def get_defaults(self):
		return webnotes.defaults.get_defaults()
