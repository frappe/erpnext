# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, _

from frappe.model.document import Document

class Currency(Document):
		
def validate_conversion_rate(currency, conversion_rate, conversion_rate_label, company):
	"""common validation for currency and price list currency"""

	company_currency = frappe.db.get_value("Company", company, "default_currency")

	if not conversion_rate:
		throw(_('%(conversion_rate_label)s is mandatory. Maybe Currency Exchange record is not created for %(from_currency)s to %(to_currency)s') % {
			"conversion_rate_label": conversion_rate_label,
			"from_currency": currency,
			"to_currency": company_currency
		})