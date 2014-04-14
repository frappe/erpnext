# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
"""Global Defaults"""
import frappe
from frappe import _
import frappe.defaults
from frappe.utils import cint

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

from frappe.model.document import Document

class GlobalDefaults(Document):

	def on_update(self):
		"""update defaults"""
		self.validate_session_expiry()
		self.set_country_and_timezone()

		for key in keydict:
			frappe.db.set_default(key, self.get(keydict[key], ''))

		# update year start date and year end date from fiscal_year
		year_start_end_date = frappe.db.sql("""select year_start_date, year_end_date
			from `tabFiscal Year` where name=%s""", self.current_fiscal_year)

		ysd = year_start_end_date[0][0] or ''
		yed = year_start_end_date[0][1] or ''

		if ysd and yed:
			frappe.db.set_default('year_start_date', ysd.strftime('%Y-%m-%d'))
			frappe.db.set_default('year_end_date', yed.strftime('%Y-%m-%d'))

		# enable default currency
		if self.default_currency:
			frappe.db.set_value("Currency", self.default_currency, "enabled", 1)

		# clear cache
		frappe.clear_cache()

	def validate_session_expiry(self):
		if self.session_expiry:
			parts = self.session_expiry.split(":")
			if len(parts)!=2 or not (cint(parts[0]) or cint(parts[1])):
				frappe.throw(_("Session Expiry must be in format {0}").format("hh:mm"))

	def set_country_and_timezone(self):
		frappe.db.set_default("country", self.country)
		frappe.db.set_default("time_zone", self.time_zone)

	def get_defaults(self):
		return frappe.defaults.get_defaults()
