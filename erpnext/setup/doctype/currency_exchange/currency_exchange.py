# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime_str, formatdate, nowdate

class CurrencyExchange(Document):
	def autoname(self):
		if not self.date:
			self.date = nowdate()
		self.name = '{0}-{1}-{2}'.format(formatdate(get_datetime_str(self.date), "yyyy-MM-dd"),
			self.from_currency, self.to_currency)

	def validate(self):
		self.validate_value("exchange_rate", ">", 0)

		if self.from_currency == self.to_currency:
			frappe.throw(_("From Currency and To Currency cannot be same"))
