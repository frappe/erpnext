# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.regional.italy.setup import add_permissions

def execute():
	countries = frappe.get_all("Company", fields="country")
	countries = [country["country"] for country in countries]
	if "Italy" in countries:
		add_permissions()