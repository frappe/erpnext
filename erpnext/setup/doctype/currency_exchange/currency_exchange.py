# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.model.controller import DocListController

class CurrencyExchange(DocListController):
		
	def autoname(self):
		self.name = self.from_currency + "-" + self.to_currency
		
	def validate(self):
		self.validate_value("exchange_rate", ">", 0)
		
		if self.from_currency == self.to_currency:
			msgprint(_("From Currency and To Currency cannot be same"), raise_exception=True)