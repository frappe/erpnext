# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	frappe.reload_doc('support', 'doctype', 'service_level_agreement')
	if frappe.db.has_column('Service Level Agreement', 'enable'):
		rename_field('Service Level Agreement', 'enable', 'enabled')

	for sla in frappe.get_all('Service Level Agreement'):
		frappe.db.set_value('Service Level Agreement', sla.name, 'document_type', 'Issue')