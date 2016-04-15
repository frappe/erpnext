# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe


@frappe.whitelist()
def get_children():
	ctype = frappe.local.form_dict.get('ctype')
	parent_field = 'parent_' + ctype.lower().replace(' ', '_')
	parent = frappe.form_dict.get("parent") or ""

	return frappe.db.sql("""select name as value,
		if(is_group='Yes', 1, 0) as expandable
		from `tab{ctype}`
		where docstatus < 2
		and ifnull(`{parent_field}`,'') = %s
		order by name""".format(ctype=frappe.db.escape(ctype), parent_field=frappe.db.escape(parent_field)),
		parent, as_dict=1)

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
