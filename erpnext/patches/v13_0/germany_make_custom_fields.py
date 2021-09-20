# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

from erpnext.regional.germany.setup import make_custom_fields


def condition():
	company_list = frappe.get_all('Company', filters = {'country': 'Germany'})
	return bool(company_list)



def execute():
	"""Execute the make_custom_fields method for german companies.

	It is usually run once at setup of a new company. Since it's new, run it
	once for existing companies as well.
	"""
	make_custom_fields()
