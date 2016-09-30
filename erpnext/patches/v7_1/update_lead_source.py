import frappe
from frappe import _

def execute():
	from erpnext.setup.setup_wizard.install_fixtures import default_lead_sources

	frappe.reload_doc('selling', 'doctype', 'lead_source')

	frappe.local.lang = frappe.db.get_default("lang") or 'en'

	for s in default_lead_sources:
		insert_lead_source(_(s))

	# get lead sources in existing forms (customized)
	# and create a document if not created
	for d in ['Lead', 'Opportunity', 'Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice']:
		sources = frappe.db.sql_list('select distinct source from `tab{0}`'.format(d))
		for s in sources:
			if s and s not in default_lead_sources:
				insert_lead_source(s)

		# remove customization for source
		for p in frappe.get_all('Property Setter', {'doc_type':d, 'field_name':'source', 'property':'options'}):
			frappe.delete_doc('Property Setter', p.name)

def insert_lead_source(s):
	if not frappe.db.exists('Lead Source', s):
		frappe.get_doc(dict(doctype='Lead Source', source_name=s)).insert()
