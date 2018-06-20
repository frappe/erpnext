# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.rename_doc import rename_doc
from frappe.model.utils.rename_field import rename_field


def execute():
	# Rename and reload the Land Unit and Linked Land Unit doctypes
	if frappe.db.table_exists('Land Unit') and not frappe.db.table_exists('Location'):
		rename_doc('DocType', 'Land Unit', 'Location', force=True)

	frappe.reload_doc('assets', 'doctype', 'location')

	if frappe.db.table_exists('Linked Land Unit') and not frappe.db.table_exists('Linked Location'):
		rename_doc('DocType', 'Linked Land Unit', 'Linked Location', force=True)

	frappe.reload_doc('assets', 'doctype', 'linked_location')

	# Rename the fields in related doctypes
	if 'lanked_land_unit' in frappe.db.get_table_columns('Crop Cycle'):
		rename_field('Crop Cycle', 'linked_land_unit', 'linked_location')

	if 'land_unit' in frappe.db.get_table_columns('Linked Location'):
		rename_field('Linked Location', 'land_unit', 'location')

	# TODO: Move Land Unit records to Location
	if frappe.db.table_exists('Land Unit'):
		land_units = frappe.get_all('Land Unit', fields=['*'])

		for land_unit in land_units:
			if not frappe.db.exists('Location', land_unit.get('land_unit_name')):
				doc = frappe.get_doc({
					'doctype': 'Location',
					'location_name': land_unit.get('land_unit_name')
				}).insert(ignore_permissions=True)

	# frappe.db.sql("""update `tabDesktop Icon` set label='Location', module_name='Location' where label='Land Unit'""")
	frappe.db.sql("""update `tabDesktop Icon` set link='List/Location' where link='List/Land Unit'""")

	# Delete the Land Unit and Linked Land Unit doctypes
	if frappe.db.table_exists('Land Unit'):
		frappe.delete_doc('DocType', 'Land Unit', force=1)

	if frappe.db.table_exists('Linked Land Unit'):
		frappe.delete_doc('DocType', 'Linked Land Unit', force=1)
