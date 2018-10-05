import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from erpnext.domains.healthcare import data
from frappe.modules import scrub, get_doctype_module

sales_invoice_referenced_doc = {
	"Patient Appointment": "sales_invoice",
	"Patient Encounter": "invoice",
	"Lab Test": "invoice",
	"Lab Prescription": "invoice",
	"Sample Collection": "invoice"
}

def execute():
	frappe.reload_doc('accounts', 'doctype', 'loyalty_program')
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice_item')

	if "Healthcare" not in frappe.get_active_domains():
		return

	healthcare_custom_field_in_sales_invoice()
	for si_ref_doc in sales_invoice_referenced_doc:
		if frappe.db.exists('DocType', si_ref_doc):
			frappe.reload_doc(get_doctype_module(si_ref_doc), 'doctype', scrub(si_ref_doc))

			if frappe.db.has_column(si_ref_doc, sales_invoice_referenced_doc[si_ref_doc]) \
			and frappe.db.has_column(si_ref_doc, 'invoiced'):
				# Set Reference DocType and Reference Docname
				doc_list = frappe.db.sql("""
							select name from `tab{0}`
							where {1} is not null
						""".format(si_ref_doc, sales_invoice_referenced_doc[si_ref_doc]))
				if doc_list:
					frappe.reload_doc(get_doctype_module("Sales Invoice"), 'doctype', 'sales_invoice')
					for doc_id in doc_list:
						invoice_id = frappe.db.get_value(si_ref_doc, doc_id[0], sales_invoice_referenced_doc[si_ref_doc])
						if frappe.db.exists("Sales Invoice", invoice_id):
							if si_ref_doc == "Lab Test":
								template = frappe.db.get_value("Lab Test", doc_id[0], "template")
								if template:
									item = frappe.db.get_value("Lab Test Template", template, "item")
									if item:
										frappe.db.sql("""update `tabSales Invoice Item` set reference_dt = '{0}',
										reference_dn = '{1}' where parent = '{2}' and item_code='{3}'""".format\
										(si_ref_doc, doc_id[0], invoice_id, item))
							else:
								invoice = frappe.get_doc("Sales Invoice", invoice_id)
								for item_line in invoice.items:
									if not item_line.reference_dn:
										item_line.db_set({"reference_dt":si_ref_doc, "reference_dn": doc_id[0]})
										break
				# Documents mark invoiced for submitted sales invoice
				frappe.db.sql("""update `tab{0}` doc, `tabSales Invoice` si
					set doc.invoiced = 1 where si.docstatus = 1 and doc.{1} = si.name
					""".format(si_ref_doc, sales_invoice_referenced_doc[si_ref_doc]))

def healthcare_custom_field_in_sales_invoice():
	frappe.reload_doc('healthcare', 'doctype', 'patient')
	frappe.reload_doc('healthcare', 'doctype', 'healthcare_practitioner')
	if data['custom_fields']:
		create_custom_fields(data['custom_fields'])

	frappe.db.sql("""
				delete from `tabCustom Field`
				where fieldname = 'appointment' and options = 'Patient Appointment'
			""")
