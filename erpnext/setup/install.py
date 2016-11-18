# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

default_mail_footer = """<div style="padding: 7px; text-align: right; color: #888"><small>Sent via
	<a style="color: #888" href="http://erpnext.org">ERPNext</a></div>"""

def after_install():
	frappe.get_doc({'doctype': "Role", "role_name": "Analytics"}).insert()
	set_single_defaults()
	create_compact_item_print_custom_field()
	from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to
	add_all_roles_to("Administrator")
	frappe.db.commit()

def check_setup_wizard_not_completed():
	if frappe.db.get_default('desktop:home_page') == 'desktop':
		print
		print "ERPNext can only be installed on a fresh site where the setup wizard is not completed"
		print "You can reinstall this site (after saving your data) using: bench --site [sitename] reinstall"
		print
		return False

def set_single_defaults():
	for dt in ('Accounts Settings', 'Print Settings', 'HR Settings', 'Buying Settings',
		'Selling Settings', 'Stock Settings', 'Daily Work Summary Settings'):
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
			except frappe.ValidationError:
				pass

	frappe.db.set_default("date_format", "dd-mm-yyyy")

def create_compact_item_print_custom_field():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field
	create_custom_field('Print Settings', {
		'label': _('Compact Item Print'),
		'fieldname': 'compact_item_print',
		'fieldtype': 'Check',
		'default': 1,
		'insert_after': 'with_letterhead'
	})