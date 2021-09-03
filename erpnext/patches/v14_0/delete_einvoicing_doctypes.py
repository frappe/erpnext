import frappe


def execute():
	frappe.delete_doc('DocType', 'E Invoice Settings', ignore_missing=True)
	frappe.delete_doc('DocType', 'E Invoice User', ignore_missing=True)
	frappe.delete_doc('Report', 'E-Invoice Summary', ignore_missing=True)
	frappe.delete_doc('Print Format', 'GST E-Invoice', ignore_missing=True)
	frappe.delete_doc('Custom Field', 'Sales Invoice-eway_bill_cancelled', ignore_missing=True)
	frappe.delete_doc('Custom Field', 'Sales Invoice-irn_cancelled', ignore_missing=True)
