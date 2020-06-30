# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
	frappe.reload_doc('support', 'doctype', 'service_level_agreement')

	for sla in frappe.get_all("Service Level Agreement"):
		frappe.db.set_value("Issue", sla.name, "document_type", "Issue")