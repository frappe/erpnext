# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	rename_field('Company', 'tax_id', 'tax_strn')
	rename_field('Company', 'tax_ntn_cnic', 'tax_id')