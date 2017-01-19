import frappe
from frappe.core.doctype.dynamic_link.dynamic_link import deduplicate_dynamic_links

def execute():
	frappe.reload_doc('core', 'doctype', 'dynamic_link')
	frappe.reload_doc('email', 'doctype', 'contact')
	frappe.reload_doc('geo', 'doctype', 'address')
	map_fields = (
		('Customer', 'customer'),
		('Supplier', 'supplier'),
		('Load', 'lead'),
		('Sales Partner', 'sales_partner')
	)
	for doctype in ('Contact', 'Address'):
		if frappe.db.has_column(doctype, 'customer'):
			for doc in frappe.get_all(doctype, fields='*'):
				doc.doctype = doctype
				doc = frappe.get_doc(doc)
				dirty = False
				for field in map_fields:
					if doc.get(field[1]):
						doc.append('links', dict(link_doctype=field[0], link_name=doc.get(field[1])))
						dirty = True

					if dirty:
						deduplicate_dynamic_links(doc)
						doc.update_children()
