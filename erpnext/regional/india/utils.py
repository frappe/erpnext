import frappe, re
from frappe import _
from erpnext.regional.india import states, state_numbers

def validate_gstin_for_india(doc, method):
	if not hasattr(doc, 'gstin'):
		return

	if doc.gstin:
		doc.gstin = doc.gstin.upper()
		if doc.gstin != "NA":
			p = re.compile("[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[Z]{1}[0-9a-zA-Z]{1}")
			if not p.match(doc.gstin):
				frappe.throw(_("Invalid GSTIN or Enter NA for Unregistered"))

		if not doc.gst_state:
			if doc.state in states:
				doc.gst_state = doc.state

		if doc.gst_state:
			doc.gst_state_number = state_numbers[doc.gst_state]
			if doc.gstin != "NA" and doc.gst_state_number != doc.gstin[:2]:
				frappe.throw(_("First 2 digits of GSTIN should match with State number {0}")
					.format(doc.gst_state_number))
