import frappe

def execute():
	frappe.reload_doctype('Contact')
	frappe.reload_doctype('Address')
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
						doc.save()
