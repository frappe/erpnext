import frappe, re
from frappe import _
from erpnext.regional.india import states, state_numbers
from erpnext.controllers.taxes_and_totals import get_itemised_tax, get_itemised_taxable_amount

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

def get_itemised_tax_breakup_header(item_doctype, tax_accounts):
	if frappe.get_meta(item_doctype).has_field('gst_hsn_code'):
		return [_("HSN/SAC"), _("Taxable Amount")] + tax_accounts
	else:
		return [_("Item"), _("Taxable Amount")] + tax_accounts
	
def get_itemised_tax_breakup_data(doc):
	itemised_tax = get_itemised_tax(doc.taxes)

	itemised_taxable_amount = get_itemised_taxable_amount(doc.items)
	
	if not frappe.get_meta(doc.doctype + " Item").has_field('gst_hsn_code'):
		return itemised_tax, itemised_taxable_amount

	item_hsn_map = frappe._dict()
	for d in doc.items:
		item_hsn_map.setdefault(d.item_code or d.item_name, d.get("gst_hsn_code"))

	hsn_tax = {}
	for item, taxes in itemised_tax.items():
		hsn_code = item_hsn_map.get(item)
		hsn_tax.setdefault(hsn_code, frappe._dict())
		for tax_account, tax_detail in taxes.items():
			hsn_tax[hsn_code].setdefault(tax_account, {"tax_rate": 0, "tax_amount": 0})
			hsn_tax[hsn_code][tax_account]["tax_rate"] = tax_detail.get("tax_rate")
			hsn_tax[hsn_code][tax_account]["tax_amount"] += tax_detail.get("tax_amount")

	# set taxable amount
	hsn_taxable_amount = frappe._dict()
	for item, taxable_amount in itemised_taxable_amount.items():
		hsn_code = item_hsn_map.get(item)
		hsn_taxable_amount.setdefault(hsn_code, 0)
		hsn_taxable_amount[hsn_code] += itemised_taxable_amount.get(item)

	return hsn_tax, hsn_taxable_amount

# don't remove this function it is used in tests
def test_method():
	'''test function'''
	return 'overridden'