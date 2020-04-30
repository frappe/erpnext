# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from erpnext.setup.setup_wizard.operations.install_fixtures import add_dashboards

def execute():
	if frappe.db.exists('DocType', 'Patient Appointment'):
		add_dashboards()
