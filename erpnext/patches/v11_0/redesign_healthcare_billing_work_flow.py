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
	healthcare_custom_field_in_sales_invoice()
	for si_ref_doc in sales_invoice_referenced_doc:
		if frappe.db.exists('DocType', si_ref_doc):
			frappe.reload_doc(get_doctype_module(si_ref_doc), 'doctype', scrub(si_ref_doc))

			if frappe.db.has_column(si_ref_doc, sales_invoice_referenced_doc[si_ref_doc]) \
			and frappe.db.has_column(si_ref_doc, 'invoiced'):
				doc_list = frappe.db.sql("""
							select name from `tab{0}`
							where {1} is not null
						""".format(si_ref_doc, sales_invoice_referenced_doc[si_ref_doc]))
				if doc_list:
					frappe.reload_doc(get_doctype_module("Sales Invoice"), 'doctype', 'sales_invoice')
					for doc_id in doc_list:
						invoice_id = frappe.db.get_value(si_ref_doc, doc_id[0][0], sales_invoice_referenced_doc[si_ref_doc])
						invoice = frappe.get_doc("Sales Invoice", invoice_id)
						if invoice.docstatus == 1 and invoice.items:
							marked = False
							if not marked:
								for item_line in invoice.items:
									marked = True
									item_line.reference_dt = si_ref_doc
									item_line.reference_dn = doc_id[0][0]
							invoice.update()


				frappe.db.sql("""
							update `tab{0}` set invoiced = 1
							where {1} is not null
						""".format(si_ref_doc, sales_invoice_referenced_doc[si_ref_doc]))

def healthcare_custom_field_in_sales_invoice():
	if data['custom_fields']:
		create_custom_fields(data['custom_fields'])

	frappe.db.sql("""
				delete from `tabCustom Field`
				where fieldname = 'appointment' and options = 'Patient Appointment'
			""")
