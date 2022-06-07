# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup(company=None, patch=True):
	make_custom_fields()
	add_custom_roles_for_reports()


def make_custom_fields():
	custom_fields = {
		"Company": [
			dict(fieldname="siren_number", label="SIREN Number", fieldtype="Data", insert_after="is_group"),
			dict(
				fieldname="siret_number", label="SIRET Number", fieldtype="Data", insert_after="siren_number"
			),
			dict(fieldname="naf_code", label="APE NAF Code", fieldtype="Data", insert_after="siret_number"),
		],
		"Customer": [
			dict(fieldname="siren_number", label="SIREN Number", fieldtype="Data", insert_after="tax_id"),
			dict(
				fieldname="siret_number", label="SIRET Number", fieldtype="Data", insert_after="siren_number"
			),
			dict(fieldname="naf_code", label="APE NAF Code", fieldtype="Data", insert_after="siret_number"),
			dict(fieldname="incoterm", label="Incoterm", fieldtype="Data", insert_after="lead_name"),
		],
		"Supplier": [
			dict(fieldname="siren_number", label="SIREN Number", fieldtype="Data", insert_after="website"),
			dict(
				fieldname="siret_number", label="SIRET Number", fieldtype="Data", insert_after="siren_number"
			),
			dict(fieldname="naf_code", label="APE NAF Code", fieldtype="Data", insert_after="siren_number"),
		],
		"Supplier": [
			dict(fieldname="siren_number", label="SIREN Number", fieldtype="Data", insert_after="website"),
			dict(
				fieldname="siret_number", label="SIRET Number", fieldtype="Data", insert_after="siren_number"
			),
			dict(fieldname="naf_code", label="APE NAF Code", fieldtype="Data", insert_after="siren_number"),
		],
	}

	create_custom_fields(custom_fields)


def add_custom_roles_for_reports():
	report_name = "Fichier des Ecritures Comptables [FEC]"

	if not frappe.db.get_value("Custom Role", dict(report=report_name)):
		frappe.get_doc(
			dict(doctype="Custom Role", report=report_name, roles=[dict(role="Accounts Manager")])
		).insert()
