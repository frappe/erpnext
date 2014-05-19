# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe.model.document import Document

class Feed(Document):
	pass

def on_doctype_update():
	if not frappe.db.sql("""show index from `tabFeed`
		where Key_name="feed_doctype_docname_index" """):
		frappe.db.commit()
		frappe.db.sql("""alter table `tabFeed`
			add index feed_doctype_docname_index(doc_type, doc_name)""")

def get_permission_query_conditions():
	restrictions = frappe.defaults.get_restrictions()
	can_read = frappe.user.get_can_read()
	ignore_restrictions = frappe.user.ignore_restrictions

	can_read_doctypes = ['"{}"'.format(doctype) for doctype in
		list(set(can_read) + set(ignore_restrictions) - set(restrictions.keys()))]

	if not can_read_doctypes:
		return ""

	conditions = [
		"tabFeed.doc_type in ({})".format(", ".join(can_read_doctypes)),

		'(tabFeed.owner = "{}" and tabFeed.doc_type in ({}))'.format(frappe.session.user,
			", ".join(['"{}"'.format(doctype) for doctype in can_read]))
	]

	if restrictions:
		can_read_docs = []
		for doctype, names in restrictions.items():
			if doctype in ignore_restrictions:
				continue

			for n in names:
				can_read_docs.append('"{}|{}"'.format(doctype, n))

		if can_read_docs:
			conditions.append("concat_ws('|', tabFeed.doc_type, tabFeed.doc_name) in ({})".format(
				", ".join(can_read_docs)))

	return "(" + " or ".join(conditions) + ")"

def has_permission(doc):
	return frappe.has_permission(doc.doc_type, "read", doc.doc_name)
