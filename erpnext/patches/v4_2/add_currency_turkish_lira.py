# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.country_info import get_country_info
from erpnext.setup.install import add_country_and_currency

def execute():
	country = get_country_info(country="Turkey")
	add_country_and_currency("Turkey", country)
