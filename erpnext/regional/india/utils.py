import frappe, re
from frappe import _
from frappe.utils import cstr
from erpnext.regional.india import states, state_numbers
from erpnext.controllers.taxes_and_totals import get_itemised_tax, get_itemised_taxable_amount

def validate_gstin_for_india(doc, method):
	if not hasattr(doc, 'gstin'):
		return

	if doc.gstin:
		doc.gstin = doc.gstin.upper()
		if doc.gstin not in ["NA", "na"]:
			p = re.compile("[0-9]{2}[A-Z]{4}[0-9A-Z]{1}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[1-9A-Z]{1}[0-9A-Z]{1}")
			if not p.match(doc.gstin) or doc.gstin != get_gstin_with_check_digit(doc.gstin[:-1]):
				frappe.throw(_("Invalid GSTIN!! Check for typos or Enter NA for Unregistered"))

	if not doc.gst_state:
		if doc.state in states:
			doc.gst_state = doc.state

	if doc.gst_state:
		doc.gst_state_number = state_numbers[doc.gst_state]
		if doc.gstin and doc.gstin != "NA" and doc.gst_state_number != doc.gstin[:2]:
			frappe.throw(_("First 2 digits of GSTIN should match with State number {0}")
				.format(doc.gst_state_number))

def get_gstin_with_check_digit(gstin_without_check_digit):
	''' Function to get the check digit for the gstin.

		param: gstin_without_check_digit
		return: GSTIN with check digit 
	'''
	factor = 1
	total = 0
	code_point_chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
	input_chars = gstin_without_check_digit.strip()
	if not input_chars:
		frappe.throw(_("GSTIN supplied for checkdigit calculation is blank"))
	mod = len(code_point_chars)
	for char in input_chars:
		digit = factor * code_point_chars.find(char)
		if digit < 0:
			frappe.throw(_("GSTIN supplied for checkdigit contains invalid character"))
		digit = (digit / mod) + (digit % mod)
		total += digit
		factor = 2 if factor == 1 else 1
	return ''.join([gstin_without_check_digit,code_point_chars[((mod - (total % mod)) % mod)]])

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

def set_place_of_supply(doc, method):
	if not frappe.get_meta('Address').has_field('gst_state'): return

	if doc.doctype in ("Sales Invoice", "Delivery Note"):
		address_name = doc.shipping_address_name or doc.customer_address
	elif doc.doctype == "Purchase Invoice":
		address_name = doc.shipping_address or doc.supplier_address

	if address_name:
		address = frappe.db.get_value("Address", address_name, ["gst_state", "gst_state_number"], as_dict=1)
		doc.place_of_supply = cstr(address.gst_state_number) + "-" + cstr(address.gst_state)

# don't remove this function it is used in tests
def test_method():
	'''test function'''
	return 'overridden'
