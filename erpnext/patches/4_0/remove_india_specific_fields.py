# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.core.doctype.custom_field.custom_field import create_custom_field_if_values_exist

def execute():
	frappe.db.sql("delete from tabDocField where parent='Salary Slip' and options='Grade'")
	docfields = {
		("Purchase Receipt", "challan_no"): frappe.get_meta("Purchase Receipt").get_field("challan_no"),
		("Purchase Receipt", "challan_date"): frappe.get_meta("Purchase Receipt").get_field("challan_date"),
		("Employee", "pf_number"): frappe.get_meta("Employee").get_field("pf_number"),
		("Employee", "pan_number"): frappe.get_meta("Employee").get_field("pan_number"),
		("Employee", "gratuity_lic_id"): frappe.get_meta("Employee").get_field("gratuity_lic_id"),
		("Employee", "esic_card_no"): frappe.get_meta("Employee").get_field("esic_card_no"),
		("Salary Slip", "esic_no"): frappe.get_meta("Salary Slip").get_field("esic_no"),
		("Salary Slip", "pf_no"): frappe.get_meta("Salary Slip").get_field("pf_no")
	}

	for (doctype, fieldname), df in docfields.items():
		if not df:
			continue
		opts = df.as_dict()
		if df.idx >= 2:
			opts["insert_after"] = frappe.get_meta(doctype).get("fields")[df.idx - 2].fieldname

		frappe.delete_doc("DocField", df.name)
		frappe.clear_cache(doctype=doctype)
		create_custom_field_if_values_exist(doctype, opts)
