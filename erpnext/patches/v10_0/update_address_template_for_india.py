# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.regional.india.setup import update_address_template

def execute():
	if frappe.db.get_value('Company', {'country': 'India'}, 'name'):
		update_address_template()