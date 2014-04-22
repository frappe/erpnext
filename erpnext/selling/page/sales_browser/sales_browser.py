# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe


@frappe.whitelist()
def get_children():
	ctype = frappe.local.form_dict.get('ctype')
	frappe.local.form_dict['parent_field'] = 'parent_' + ctype.lower().replace(' ', '_')
	if not frappe.form_dict.get('parent'):
		frappe.local.form_dict['parent'] = ''

	return frappe.db.sql("""select name as value,
		if(is_group='Yes', 1, 0) as expandable
		from `tab%(ctype)s`
		where docstatus < 2
		and ifnull(%(parent_field)s,'') = "%(parent)s"
		order by name""" % frappe.local.form_dict, as_dict=1)

@frappe.whitelist()
def add_node():
	ctype = frappe.form_dict.get('ctype')
	parent_field = 'parent_' + ctype.lower().replace(' ', '_')
	name_field = ctype.lower().replace(' ', '_') + '_name'

	doc = frappe.new_doc(ctype)
	doc.update({
		name_field: frappe.form_dict['name_field'],
		parent_field: frappe.form_dict['parent'],
		"is_group": frappe.form_dict['is_group']
	})
	if ctype == "Sales Person":
		doc.employee = frappe.form_dict.get('employee')

	doc.save()
