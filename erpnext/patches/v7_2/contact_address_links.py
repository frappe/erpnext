from __future__ import unicode_literals
import frappe
from frappe.core.doctype.dynamic_link.dynamic_link import deduplicate_dynamic_links
from frappe.utils import update_progress_bar

def execute():
	frappe.reload_doc('core', 'doctype', 'dynamic_link')
	frappe.reload_doc('contacts', 'doctype', 'contact')
	frappe.reload_doc('contacts', 'doctype', 'address')
	map_fields = (
		('Customer', 'customer'),
		('Supplier', 'supplier'),
		('Lead', 'lead'),
		('Sales Partner', 'sales_partner')
	)
	for doctype in ('Contact', 'Address'):
		if frappe.db.has_column(doctype, 'customer'):
			items = frappe.get_all(doctype)
			for i, doc in enumerate(items):
				doc = frappe.get_doc(doctype, doc.name)
				dirty = False
				for field in map_fields:
					if doc.get(field[1]):
						doc.append('links', dict(link_doctype=field[0], link_name=doc.get(field[1])))
						dirty = True

					if dirty:
						deduplicate_dynamic_links(doc)
						doc.update_children()

					update_progress_bar('Updating {0}'.format(doctype), i, len(items))
			print