# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("support", "doctype", "sla_fulfilled_on_status")
	frappe.reload_doc("support", "doctype", "service_level_agreement")
	if frappe.db.has_column("Service Level Agreement", "enable"):
		rename_field("Service Level Agreement", "enable", "enabled")

	for sla in frappe.get_all("Service Level Agreement"):
		agreement = frappe.get_doc("Service Level Agreement", sla.name)
		agreement.db_set("document_type", "Issue")
		agreement.reload()
		agreement.apply_sla_for_resolution = 1
		agreement.append("sla_fulfilled_on", {"status": "Resolved"})
		agreement.append("sla_fulfilled_on", {"status": "Closed"})
		agreement.save()
