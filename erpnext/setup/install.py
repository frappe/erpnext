# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

default_mail_footer = """<div style="padding: 7px; text-align: right; color: #888"><small>Sent via
	<a style="color: #888" href="http://erpnext.org">ERPNext</a></div>"""

def after_install():
	frappe.get_doc({'doctype': "Role", "role_name": "Analytics"}).insert()
	set_single_defaults()
	frappe.db.set_default('desktop:home_page', 'setup-wizard')
	feature_setup()
	from erpnext.setup.page.setup_wizard.setup_wizard import add_all_roles_to
	add_all_roles_to("Administrator")
	frappe.db.commit()

def feature_setup():
	"""save global defaults and features setup"""
	doc = frappe.get_doc("Features Setup", "Features Setup")
	doc.flags.ignore_permissions = True

	# store value as 1 for all these fields
	flds = ['fs_item_serial_nos', 'fs_item_batch_nos', 'fs_brands', 'fs_item_barcode',
		'fs_item_advanced', 'fs_packing_details', 'fs_item_group_in_details',
		'fs_exports', 'fs_imports', 'fs_discounts', 'fs_purchase_discounts',
		'fs_after_sales_installations', 'fs_projects', 'fs_sales_extras',
		'fs_recurring_invoice', 'fs_pos', 'fs_manufacturing', 'fs_quality',
		'fs_page_break', 'fs_more_info', 'fs_pos_view'
	]
	for f in flds:
		doc.set(f, 1)
	doc.save()

def set_single_defaults():
	for dt in frappe.db.sql_list("""select name from `tabDocType` where issingle=1"""):
		default_values = frappe.db.sql("""select fieldname, `default` from `tabDocField`
			where parent=%s""", dt)
		if default_values:
			try:
				b = frappe.get_doc(dt, dt)
				for fieldname, value in default_values:
					b.set(fieldname, value)
				b.save()
			except frappe.MandatoryError:
				pass

	frappe.db.set_default("date_format", "dd-mm-yyyy")
