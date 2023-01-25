# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import base64
import io
import json
import os
import re
import sys
import traceback

import frappe
import jwt
import requests
import six
from frappe import _, bold
from frappe.core.page.background_jobs.background_jobs import get_info
from frappe.integrations.utils import make_get_request, make_post_request
from frappe.utils.background_jobs import enqueue
from frappe.utils.data import (
	add_to_date,
	cint,
	cstr,
	flt,
	format_date,
	get_link_to_form,
	getdate,
	now_datetime,
	time_diff_in_hours,
	time_diff_in_seconds,
)
from frappe.utils.scheduler import is_scheduler_inactive
from pyqrcode import create as qrcreate

from erpnext.regional.india.utils import get_gst_accounts, get_place_of_supply


@frappe.whitelist()
def validate_eligibility(doc):
	if isinstance(doc, six.string_types):
		doc = json.loads(doc)

	invalid_doctype = doc.get("doctype") != "Sales Invoice"
	if invalid_doctype:
		return False

	einvoicing_enabled = cint(frappe.db.get_single_value("E Invoice Settings", "enable"))
	if not einvoicing_enabled:
		return False

	einvoicing_eligible_from = (
		frappe.db.get_single_value("E Invoice Settings", "applicable_from") or "2021-04-01"
	)
	if getdate(doc.get("posting_date")) < getdate(einvoicing_eligible_from):
		return False

	invalid_company = not frappe.db.get_value("E Invoice User", {"company": doc.get("company")})
	invalid_company_gstin = not frappe.db.get_value(
		"E Invoice User", {"gstin": doc.get("company_gstin")}
	)
	invalid_supply_type = doc.get("gst_category") not in [
		"Registered Regular",
		"Registered Composition",
		"SEZ",
		"Overseas",
		"Deemed Export",
		"UIN Holders",
	]
	company_transaction = doc.get("billing_address_gstin") == doc.get("company_gstin")

	# if export invoice, then taxes can be empty
	# invoice can only be ineligible if no taxes applied and is not an export invoice
	no_taxes_applied = (
		not doc.get("taxes")
		and not doc.get("gst_category") == "Overseas"
		and not doc.get("gst_category") == "SEZ"
	)
	has_non_gst_item = any(d for d in doc.get("items", []) if d.get("is_non_gst"))

	if (
		invalid_company
		or invalid_company_gstin
		or invalid_supply_type
		or company_transaction
		or no_taxes_applied
		or has_non_gst_item
	):
		return False

	return True


def validate_einvoice_fields(doc):
	invoice_eligible = validate_eligibility(doc)

	if not invoice_eligible:
		return

	if doc.docstatus == 0 and doc._action == "save":
		if doc.irn:
			frappe.throw(_("You cannot edit the invoice after generating IRN"), title=_("Edit Not Allowed"))
		if len(doc.name) > 16:
			raise_document_name_too_long_error()

		doc.einvoice_status = "Pending"

	elif doc.docstatus == 1 and doc._action == "submit" and not doc.irn:
		frappe.throw(_("You must generate IRN before submitting the document."), title=_("Missing IRN"))

	elif doc.irn and doc.docstatus == 2 and doc._action == "cancel" and not doc.irn_cancelled:
		frappe.throw(
			_("You must cancel IRN before cancelling the document."), title=_("Cancel Not Allowed")
		)


def raise_document_name_too_long_error():
	title = _("Document ID Too Long")
	msg = _("As you have E-Invoicing enabled, to be able to generate IRN for this invoice")
	msg += ", "
	msg += _("document id {} exceed 16 letters.").format(bold(_("should not")))
	msg += "<br><br>"
	msg += _("You must {} your {} in order to have document id of {} length 16.").format(
		bold(_("modify")), bold(_("naming series")), bold(_("maximum"))
	)
	msg += _("Please account for ammended documents too.")
	frappe.throw(msg, title=title)


def read_json(name):
	file_path = os.path.join(os.path.dirname(__file__), "{name}.json".format(name=name))
	with open(file_path, "r") as f:
		return cstr(f.read())


def get_transaction_details(invoice):
	supply_type = ""
	if invoice.gst_category in ("Registered Regular", "Registered Composition", "UIN Holders"):
		supply_type = "B2B"
	elif invoice.gst_category == "SEZ":
		if invoice.export_type == "Without Payment of Tax":
			supply_type = "SEZWOP"
		else:
			supply_type = "SEZWP"
	elif invoice.gst_category == "Overseas":
		if invoice.export_type == "Without Payment of Tax":
			supply_type = "EXPWOP"
		else:
			supply_type = "EXPWP"
	elif invoice.gst_category == "Deemed Export":
		supply_type = "DEXP"

	if not supply_type:
		rr, rc, sez, overseas, export, uin = (
			bold("Registered Regular"),
			bold("Registered Composition"),
			bold("SEZ"),
			bold("Overseas"),
			bold("Deemed Export"),
			bold("UIN Holders"),
		)
		frappe.throw(
			_("GST category should be one of {}, {}, {}, {}, {}, {}").format(
				rr, rc, sez, overseas, export, uin
			),
			title=_("Invalid Supply Type"),
		)

	return frappe._dict(
		dict(tax_scheme="GST", supply_type=supply_type, reverse_charge=invoice.reverse_charge)
	)


def get_doc_details(invoice):
	if getdate(invoice.posting_date) < getdate("2021-01-01"):
		frappe.throw(
			_("IRN generation is not allowed for invoices dated before 1st Jan 2021"),
			title=_("Not Allowed"),
		)

	if invoice.is_return:
		invoice_type = "CRN"
	elif invoice.is_debit_note:
		invoice_type = "DBN"
	else:
		invoice_type = "INV"

	invoice_name = invoice.name
	invoice_date = format_date(invoice.posting_date, "dd/mm/yyyy")

	return frappe._dict(
		dict(invoice_type=invoice_type, invoice_name=invoice_name, invoice_date=invoice_date)
	)


def validate_address_fields(address, skip_gstin_validation):
	if (
		(not address.gstin and not skip_gstin_validation)
		or not address.city
		or not address.pincode
		or not address.address_title
		or not address.address_line1
		or not address.gst_state_number
	):

		frappe.throw(
			msg=_(
				"Address Lines, City, Pincode, GSTIN are mandatory for address {}. Please set them and try again."
			).format(address.name),
			title=_("Missing Address Fields"),
		)

	if address.address_line2 and len(address.address_line2) < 2:
		# to prevent "The field Address 2 must be a string with a minimum length of 3 and a maximum length of 100"
		address.address_line2 = ""


def get_party_details(address_name, skip_gstin_validation=False):
	addr = frappe.get_doc("Address", address_name)

	validate_address_fields(addr, skip_gstin_validation)

	if addr.gst_state_number == 97:
		# according to einvoice standard
		addr.pincode = 999999

	party_address_details = frappe._dict(
		dict(
			legal_name=sanitize_for_json(addr.address_title),
			location=sanitize_for_json(addr.city),
			pincode=addr.pincode,
			gstin=addr.gstin,
			state_code=addr.gst_state_number,
			address_line1=sanitize_for_json(addr.address_line1),
			address_line2=sanitize_for_json(addr.address_line2),
		)
	)

	return party_address_details


def get_overseas_address_details(address_name):
	address_title, address_line1, address_line2, city = frappe.db.get_value(
		"Address", address_name, ["address_title", "address_line1", "address_line2", "city"]
	)

	if not address_title or not address_line1 or not city:
		frappe.throw(
			msg=_(
				"Address lines and city is mandatory for address {}. Please set them and try again."
			).format(get_link_to_form("Address", address_name)),
			title=_("Missing Address Fields"),
		)

	return frappe._dict(
		dict(
			gstin="URP",
			legal_name=sanitize_for_json(address_title),
			location=city,
			address_line1=sanitize_for_json(address_line1),
			address_line2=sanitize_for_json(address_line2),
			pincode=999999,
			state_code=96,
			place_of_supply=96,
		)
	)


def get_item_list(invoice):
	item_list = []

	hide_discount_in_einvoice = cint(
		frappe.db.get_single_value("E Invoice Settings", "dont_show_discounts_in_e_invoice")
	)

	for d in invoice.items:
		einvoice_item_schema = read_json("einv_item_template")
		item = frappe._dict({})
		item.update(d.as_dict())

		item.sr_no = d.idx
		item.description = sanitize_for_json(d.item_name)

		item.qty = abs(item.qty)
		item_qty = item.qty

		item.taxable_value = abs(item.taxable_value)

		if invoice.get("is_return") or invoice.get("is_debit_note"):
			item_qty = item_qty or 1

		if hide_discount_in_einvoice or invoice.is_internal_customer or item.discount_amount < 0:
			item.unit_rate = item.taxable_value / item_qty
			item.gross_amount = item.taxable_value
			item.discount_amount = 0

		else:
			if invoice.get("apply_discount_on") and (abs(invoice.get("base_discount_amount") or 0.0) > 0.0):
				# TODO: need to handle case when tax included in basic rate is checked.
				item.discount_amount = (item.discount_amount * item_qty) + (
					abs(item.base_amount) - abs(item.base_net_amount)
				)
			else:
				item.discount_amount = item.discount_amount * item_qty

			try:
				item.unit_rate = (item.taxable_value + item.discount_amount) / item_qty
			except ZeroDivisionError:
				# This will never run but added as safety measure
				frappe.throw(
					title=_("Error: Qty is Zero"),
					msg=_("Quantity can't be zero unless it's Credit/Debit Note."),
				)

		item.gross_amount = item.taxable_value + item.discount_amount
		item.taxable_value = item.taxable_value
		item.is_service_item = "Y" if item.gst_hsn_code and item.gst_hsn_code[:2] == "99" else "N"
		item.serial_no = ""

		item = update_item_taxes(invoice, item)

		item.total_value = abs(
			item.taxable_value
			+ item.igst_amount
			+ item.sgst_amount
			+ item.cgst_amount
			+ item.cess_amount
			+ item.cess_nadv_amount
			+ item.other_charges
		)
		einv_item = einvoice_item_schema.format(item=item)
		item_list.append(einv_item)

	return ", ".join(item_list)


def update_item_taxes(invoice, item):
	gst_accounts = get_gst_accounts(invoice.company)
	gst_accounts_list = [d for accounts in gst_accounts.values() for d in accounts if d]

	for attr in [
		"tax_rate",
		"cess_rate",
		"cess_nadv_amount",
		"cgst_amount",
		"sgst_amount",
		"igst_amount",
		"cess_amount",
		"cess_nadv_amount",
		"other_charges",
	]:
		item[attr] = 0

	for t in invoice.taxes:
		is_applicable = t.tax_amount and t.account_head in gst_accounts_list
		if is_applicable:
			# this contains item wise tax rate & tax amount (incl. discount)
			item_tax_detail = json.loads(t.item_wise_tax_detail).get(item.item_code or item.item_name)

			item_tax_rate = item_tax_detail[0]
			# item tax amount excluding discount amount
			item_tax_amount = (item_tax_rate / 100) * item.taxable_value

			if t.account_head in gst_accounts.cess_account:
				item_tax_amount_after_discount = item_tax_detail[1]
				if t.charge_type == "On Item Quantity":
					item.cess_nadv_amount += abs(item_tax_amount_after_discount)
				else:
					item.cess_rate += item_tax_rate
					item.cess_amount += abs(item_tax_amount_after_discount)

			for tax_type in ["igst", "cgst", "sgst", "utgst"]:
				if t.account_head in gst_accounts[f"{tax_type}_account"]:
					item.tax_rate += item_tax_rate
					if tax_type == "utgst":
						# utgst taxes are reported same as sgst tax
						item["sgst_amount"] += abs(item_tax_amount)
					else:
						item[f"{tax_type}_amount"] += abs(item_tax_amount)
		else:
			# TODO: other charges per item
			pass

	return item


def get_invoice_value_details(invoice):
	invoice_value_details = frappe._dict(dict())
	invoice_value_details.base_total = abs(sum([i.taxable_value for i in invoice.get("items")]))
	if (
		invoice.apply_discount_on == "Grand Total"
		and invoice.discount_amount
		and invoice.get("is_cash_or_non_trade_discount")
	):
		invoice_value_details.invoice_discount_amt = invoice.discount_amount
	else:
		invoice_value_details.invoice_discount_amt = 0

	invoice_value_details.round_off = invoice.base_rounding_adjustment
	invoice_value_details.base_grand_total = abs(invoice.base_rounded_total) or abs(
		invoice.base_grand_total
	)
	invoice_value_details.grand_total = abs(invoice.rounded_total) or abs(invoice.grand_total)

	invoice_value_details = update_invoice_taxes(invoice, invoice_value_details)

	return invoice_value_details


def update_invoice_taxes(invoice, invoice_value_details):
	gst_accounts = get_gst_accounts(invoice.company)
	gst_accounts_list = [d for accounts in gst_accounts.values() for d in accounts if d]

	invoice_value_details.total_cgst_amt = 0
	invoice_value_details.total_sgst_amt = 0
	invoice_value_details.total_igst_amt = 0
	invoice_value_details.total_cess_amt = 0
	invoice_value_details.total_other_charges = 0
	considered_rows = []

	for t in invoice.taxes:
		tax_amount = t.base_tax_amount_after_discount_amount
		if t.account_head in gst_accounts_list:
			if t.account_head in gst_accounts.cess_account:
				# using after discount amt since item also uses after discount amt for cess calc
				invoice_value_details.total_cess_amt += abs(t.base_tax_amount_after_discount_amount)

			for tax_type in ["igst", "cgst", "sgst", "utgst"]:
				if t.account_head in gst_accounts[f"{tax_type}_account"]:
					if tax_type == "utgst":
						invoice_value_details["total_sgst_amt"] += abs(tax_amount)
					else:
						invoice_value_details[f"total_{tax_type}_amt"] += abs(tax_amount)

				update_other_charges(t, invoice_value_details, gst_accounts_list, invoice, considered_rows)

		else:
			invoice_value_details.total_other_charges += abs(tax_amount)

	return invoice_value_details


def update_other_charges(
	tax_row, invoice_value_details, gst_accounts_list, invoice, considered_rows
):
	prev_row_id = cint(tax_row.row_id) - 1
	if tax_row.account_head in gst_accounts_list and prev_row_id not in considered_rows:
		if tax_row.charge_type == "On Previous Row Amount":
			amount = invoice.get("taxes")[prev_row_id].tax_amount_after_discount_amount
			invoice_value_details.total_other_charges -= abs(amount)
			considered_rows.append(prev_row_id)
		if tax_row.charge_type == "On Previous Row Total":
			amount = invoice.get("taxes")[prev_row_id].base_total - invoice.base_net_total
			invoice_value_details.total_other_charges -= abs(amount)
			considered_rows.append(prev_row_id)


def get_payment_details(invoice):
	payee_name = invoice.company
	mode_of_payment = ""
	paid_amount = invoice.base_paid_amount
	outstanding_amount = invoice.outstanding_amount

	return frappe._dict(
		dict(
			payee_name=payee_name,
			mode_of_payment=mode_of_payment,
			paid_amount=paid_amount,
			outstanding_amount=outstanding_amount,
		)
	)


def get_return_doc_reference(invoice):
	invoice_date = frappe.db.get_value("Sales Invoice", invoice.return_against, "posting_date")
	return frappe._dict(
		dict(invoice_name=invoice.return_against, invoice_date=format_date(invoice_date, "dd/mm/yyyy"))
	)


def get_eway_bill_details(invoice):
	if invoice.is_return:
		frappe.throw(
			_(
				"E-Way Bill cannot be generated for Credit Notes & Debit Notes. Please clear fields in the Transporter Section of the invoice."
			),
			title=_("Invalid Fields"),
		)

	mode_of_transport = {"": "", "Road": "1", "Air": "2", "Rail": "3", "Ship": "4"}
	vehicle_type = {"Regular": "R", "Over Dimensional Cargo (ODC)": "O"}

	return frappe._dict(
		dict(
			gstin=invoice.gst_transporter_id,
			name=invoice.transporter_name,
			mode_of_transport=mode_of_transport[invoice.mode_of_transport or ""] or None,
			distance=invoice.distance or 0,
			document_name=invoice.lr_no,
			document_date=format_date(invoice.lr_date, "dd/mm/yyyy"),
			vehicle_no=invoice.vehicle_no,
			vehicle_type=vehicle_type[invoice.gst_vehicle_type],
		)
	)


def validate_mandatory_fields(invoice):
	if not invoice.company_address:
		frappe.throw(
			_(
				"Company Address is mandatory to fetch company GSTIN details. Please set Company Address and try again."
			),
			title=_("Missing Fields"),
		)
	if not invoice.customer_address:
		frappe.throw(
			_(
				"Customer Address is mandatory to fetch customer GSTIN details. Please set Company Address and try again."
			),
			title=_("Missing Fields"),
		)
	if not frappe.db.get_value("Address", invoice.company_address, "gstin"):
		frappe.throw(
			_(
				"GSTIN is mandatory to fetch company GSTIN details. Please enter GSTIN in selected company address."
			),
			title=_("Missing Fields"),
		)
	if invoice.gst_category != "Overseas" and not frappe.db.get_value(
		"Address", invoice.customer_address, "gstin"
	):
		frappe.throw(
			_(
				"GSTIN is mandatory to fetch customer GSTIN details. Please enter GSTIN in selected customer address."
			),
			title=_("Missing Fields"),
		)


def validate_totals(einvoice):
	item_list = einvoice["ItemList"]
	value_details = einvoice["ValDtls"]

	total_item_ass_value = 0
	total_item_cgst_value = 0
	total_item_sgst_value = 0
	total_item_igst_value = 0
	total_item_value = 0
	for item in item_list:
		total_item_ass_value += flt(item["AssAmt"])
		total_item_cgst_value += flt(item["CgstAmt"])
		total_item_sgst_value += flt(item["SgstAmt"])
		total_item_igst_value += flt(item["IgstAmt"])
		total_item_value += flt(item["TotItemVal"])

		if (
			abs(flt(item["AssAmt"]) * flt(item["GstRt"]) / 100)
			- (flt(item["CgstAmt"]) + flt(item["SgstAmt"]) + flt(item["IgstAmt"]))
			> 1
		):
			frappe.throw(
				_(
					"Row #{}: GST rate is invalid. Please remove tax rows with zero tax amount from taxes table."
				).format(item.idx)
			)

	if abs(flt(value_details["AssVal"]) - total_item_ass_value) > 1:
		frappe.throw(
			_(
				"Total Taxable Value of the items is not equal to the Invoice Net Total. Please check item taxes / discounts for any correction."
			)
		)

	if (
		abs(
			flt(value_details["CgstVal"])
			+ flt(value_details["SgstVal"])
			- total_item_cgst_value
			- total_item_sgst_value
		)
		> 1
	):
		frappe.throw(
			_(
				"CGST + SGST value of the items is not equal to total CGST + SGST value. Please review taxes for any correction."
			)
		)

	if abs(flt(value_details["IgstVal"]) - total_item_igst_value) > 1:
		frappe.throw(
			_(
				"IGST value of all items is not equal to total IGST value. Please review taxes for any correction."
			)
		)

	if (
		abs(
			flt(value_details["TotInvVal"])
			+ flt(value_details["Discount"])
			- flt(value_details["OthChrg"])
			- total_item_value
		)
		> 1
	):
		frappe.throw(
			_(
				"Total Value of the items is not equal to the Invoice Grand Total. Please check item taxes / discounts for any correction."
			)
		)

	calculated_invoice_value = (
		flt(value_details["AssVal"])
		+ flt(value_details["CgstVal"])
		+ flt(value_details["SgstVal"])
		+ flt(value_details["IgstVal"])
		+ flt(value_details["CesVal"])
		+ flt(value_details["OthChrg"])
		- flt(value_details["Discount"])
	)

	if abs(flt(value_details["TotInvVal"]) - calculated_invoice_value) > 1:
		frappe.throw(
			_(
				"Total Item Value + Taxes - Discount is not equal to the Invoice Grand Total. Please check taxes / discounts for any correction."
			)
		)


def make_einvoice(invoice):
	validate_mandatory_fields(invoice)

	schema = read_json("einv_template")

	transaction_details = get_transaction_details(invoice)
	item_list = get_item_list(invoice)
	doc_details = get_doc_details(invoice)
	invoice_value_details = get_invoice_value_details(invoice)
	seller_details = get_party_details(invoice.company_address)

	if invoice.gst_category == "Overseas":
		buyer_details = get_overseas_address_details(invoice.customer_address)
	else:
		buyer_details = get_party_details(invoice.customer_address)
		place_of_supply = get_place_of_supply(invoice, invoice.doctype)
		if place_of_supply:
			place_of_supply = place_of_supply.split("-")[0]
		else:
			place_of_supply = sanitize_for_json(invoice.billing_address_gstin)[:2]
		buyer_details.update(dict(place_of_supply=place_of_supply))

	seller_details.update(dict(legal_name=invoice.company))
	buyer_details.update(dict(legal_name=invoice.customer_name or invoice.customer))

	shipping_details = payment_details = prev_doc_details = eway_bill_details = frappe._dict({})
	if invoice.shipping_address_name and invoice.customer_address != invoice.shipping_address_name:
		if invoice.gst_category == "Overseas":
			shipping_details = get_overseas_address_details(invoice.shipping_address_name)
		else:
			shipping_details = get_party_details(invoice.shipping_address_name, skip_gstin_validation=True)

	dispatch_details = frappe._dict({})
	if invoice.dispatch_address_name:
		dispatch_details = get_party_details(invoice.dispatch_address_name, skip_gstin_validation=True)

	if invoice.is_pos and invoice.base_paid_amount:
		payment_details = get_payment_details(invoice)

	if invoice.is_return and invoice.return_against:
		prev_doc_details = get_return_doc_reference(invoice)

	if invoice.transporter and not invoice.is_return:
		eway_bill_details = get_eway_bill_details(invoice)

	# not yet implemented
	period_details = export_details = frappe._dict({})

	einvoice = schema.format(
		transaction_details=transaction_details,
		doc_details=doc_details,
		dispatch_details=dispatch_details,
		seller_details=seller_details,
		buyer_details=buyer_details,
		shipping_details=shipping_details,
		item_list=item_list,
		invoice_value_details=invoice_value_details,
		payment_details=payment_details,
		period_details=period_details,
		prev_doc_details=prev_doc_details,
		export_details=export_details,
		eway_bill_details=eway_bill_details,
	)

	try:
		einvoice = safe_json_load(einvoice)
		einvoice = santize_einvoice_fields(einvoice)
	except json.JSONDecodeError:
		raise
	except Exception:
		show_link_to_error_log(invoice, einvoice)

	try:
		validate_totals(einvoice)
	except Exception:
		log_error(einvoice)
		raise

	return einvoice


def show_link_to_error_log(invoice, einvoice):
	err_log = log_error(einvoice)
	link_to_error_log = get_link_to_form("Error Log", err_log.name, "Error Log")
	frappe.throw(
		_(
			"An error occurred while creating e-invoice for {}. Please check {} for more information."
		).format(invoice.name, link_to_error_log),
		title=_("E Invoice Creation Failed"),
	)


def log_error(data=None):
	if isinstance(data, six.string_types):
		data = json.loads(data)

	seperator = "--" * 50
	err_tb = traceback.format_exc()
	err_msg = str(sys.exc_info()[1])
	data = json.dumps(data, indent=4)

	message = "\n".join(["Error", err_msg, seperator, "Data:", data, seperator, "Exception:", err_tb])
	return frappe.log_error(title=_("E Invoice Request Failed"), message=message)


def santize_einvoice_fields(einvoice):
	int_fields = ["Pin", "Distance", "CrDay"]
	float_fields = [
		"Qty",
		"FreeQty",
		"UnitPrice",
		"TotAmt",
		"Discount",
		"PreTaxVal",
		"AssAmt",
		"GstRt",
		"IgstAmt",
		"CgstAmt",
		"SgstAmt",
		"CesRt",
		"CesAmt",
		"CesNonAdvlAmt",
		"StateCesRt",
		"StateCesAmt",
		"StateCesNonAdvlAmt",
		"OthChrg",
		"TotItemVal",
		"AssVal",
		"CgstVal",
		"SgstVal",
		"IgstVal",
		"CesVal",
		"StCesVal",
		"Discount",
		"OthChrg",
		"RndOffAmt",
		"TotInvVal",
		"TotInvValFc",
		"PaidAmt",
		"PaymtDue",
		"ExpDuty",
	]
	copy = einvoice.copy()
	for key, value in copy.items():
		if isinstance(value, list):
			for idx, d in enumerate(value):
				santized_dict = santize_einvoice_fields(d)
				if santized_dict:
					einvoice[key][idx] = santized_dict
				else:
					einvoice[key].pop(idx)

			if not einvoice[key]:
				einvoice.pop(key, None)

		elif isinstance(value, dict):
			santized_dict = santize_einvoice_fields(value)
			if santized_dict:
				einvoice[key] = santized_dict
			else:
				einvoice.pop(key, None)

		elif not value or value == "None":
			einvoice.pop(key, None)

		elif key in float_fields:
			einvoice[key] = flt(value, 2)

		elif key in int_fields:
			einvoice[key] = cint(value)

	return einvoice


def safe_json_load(json_string):
	try:
		return json.loads(json_string)
	except json.JSONDecodeError as e:
		# print a snippet of 40 characters around the location where error occured
		pos = e.pos
		start, end = max(0, pos - 20), min(len(json_string) - 1, pos + 20)
		snippet = json_string[start:end]
		frappe.throw(
			_(
				"Error in input data. Please check for any special characters near following input: <br> {}"
			).format(snippet),
			title=_("Invalid JSON"),
			exc=e,
		)


class RequestFailed(Exception):
	pass


class CancellationNotAllowed(Exception):
	pass


class GSPConnector:
	def __init__(self, doctype=None, docname=None):
		self.doctype = doctype
		self.docname = docname

		self.set_invoice()
		self.set_credentials()

		# authenticate url is same for sandbox & live
		self.authenticate_url = "https://gsp.adaequare.com/gsp/authenticate?grant_type=token"
		self.base_url = (
			"https://gsp.adaequare.com"
			if not self.e_invoice_settings.sandbox_mode
			else "https://gsp.adaequare.com/test"
		)

		self.cancel_irn_url = self.base_url + "/enriched/ei/api/invoice/cancel"
		self.irn_details_url = self.base_url + "/enriched/ei/api/invoice/irn"
		self.generate_irn_url = self.base_url + "/enriched/ei/api/invoice"
		self.gstin_details_url = self.base_url + "/enriched/ei/api/master/gstin"
		# cancel_ewaybill_url will only work if user have bought ewb api from adaequare.
		self.cancel_ewaybill_url = self.base_url + "/enriched/ewb/ewayapi?action=CANEWB"
		# ewaybill_details_url + ?irn={irn_number} will provide eway bill number and details.
		self.ewaybill_details_url = self.base_url + "/enriched/ei/api/ewaybill/irn"
		self.generate_ewaybill_url = self.base_url + "/enriched/ei/api/ewaybill"
		self.get_qrcode_url = self.base_url + "/enriched/ei/others/qr/image"

	def set_invoice(self):
		self.invoice = None
		if self.doctype and self.docname:
			self.invoice = frappe.get_cached_doc(self.doctype, self.docname)

	def set_credentials(self):
		self.e_invoice_settings = frappe.get_cached_doc("E Invoice Settings")

		if not self.e_invoice_settings.enable:
			frappe.throw(
				_("E-Invoicing is disabled. Please enable it from {} to generate e-invoices.").format(
					get_link_to_form("E Invoice Settings", "E Invoice Settings")
				)
			)

		if self.invoice:
			gstin = self.get_seller_gstin()
			credentials_for_gstin = [d for d in self.e_invoice_settings.credentials if d.gstin == gstin]
			if credentials_for_gstin:
				self.credentials = credentials_for_gstin[0]
			else:
				frappe.throw(
					_(
						"Cannot find e-invoicing credentials for selected Company GSTIN. Please check E-Invoice Settings"
					)
				)
		else:
			self.credentials = (
				self.e_invoice_settings.credentials[0] if self.e_invoice_settings.credentials else None
			)

	def get_seller_gstin(self):
		gstin = frappe.db.get_value("Address", self.invoice.company_address, "gstin")
		if not gstin:
			frappe.throw(
				_("Cannot retrieve Company GSTIN. Please select company address with valid GSTIN.")
			)
		return gstin

	def get_auth_token(self):
		if time_diff_in_seconds(self.e_invoice_settings.token_expiry, now_datetime()) < 150.0:
			self.fetch_auth_token()

		return self.e_invoice_settings.auth_token

	def make_request(self, request_type, url, headers=None, data=None):
		res = None
		try:
			if request_type == "post":
				res = make_post_request(url, headers=headers, data=data)
			else:
				res = make_get_request(url, headers=headers, data=data)

		except requests.exceptions.HTTPError as e:
			if e.response.status_code in [401, 403] and not hasattr(self, "token_auto_refreshed"):
				self.auto_refresh_token()
				headers = self.get_headers()
				return self.make_request(request_type, url, headers, data)

		self.log_request(url, headers, data, res)
		return res

	def auto_refresh_token(self):
		self.token_auto_refreshed = True
		self.fetch_auth_token()

	def log_request(self, url, headers, data, res):
		headers.update({"password": self.credentials.password})
		request_log = frappe.get_doc(
			{
				"doctype": "E Invoice Request Log",
				"user": frappe.session.user,
				"reference_invoice": self.invoice.name if self.invoice else None,
				"url": url,
				"headers": json.dumps(headers, indent=4) if headers else None,
				"data": json.dumps(data, indent=4) if isinstance(data, dict) else data,
				"response": json.dumps(res, indent=4) if res else None,
			}
		)
		request_log.save(ignore_permissions=True)
		frappe.db.commit()

	def get_client_credentials(self):
		if self.e_invoice_settings.client_id and self.e_invoice_settings.client_secret:
			return self.e_invoice_settings.client_id, self.e_invoice_settings.get_password("client_secret")

		return frappe.conf.einvoice_client_id, frappe.conf.einvoice_client_secret

	def fetch_auth_token(self):
		client_id, client_secret = self.get_client_credentials()
		headers = {"gspappid": client_id, "gspappsecret": client_secret}
		res = {}
		try:
			res = self.make_request("post", self.authenticate_url, headers)
			self.e_invoice_settings.auth_token = "{} {}".format(
				res.get("token_type"), res.get("access_token")
			)
			self.e_invoice_settings.token_expiry = add_to_date(None, seconds=res.get("expires_in"))
			self.e_invoice_settings.save(ignore_permissions=True)
			self.e_invoice_settings.reload()

		except Exception:
			log_error(res)
			self.raise_error(True)

	def get_headers(self):
		return {
			"content-type": "application/json",
			"user_name": self.credentials.username,
			"password": self.credentials.get_password(),
			"gstin": self.credentials.gstin,
			"authorization": self.get_auth_token(),
			"requestid": str(base64.b64encode(os.urandom(18))),
		}

	def fetch_gstin_details(self, gstin):
		headers = self.get_headers()

		try:
			params = "?gstin={gstin}".format(gstin=gstin)
			res = self.make_request("get", self.gstin_details_url + params, headers)
			if res.get("success"):
				return res.get("result")
			else:
				log_error(res)
				raise RequestFailed

		except RequestFailed:
			self.raise_error()

		except Exception:
			log_error()
			self.raise_error(True)

	@staticmethod
	def get_gstin_details(gstin):
		"""fetch and cache GSTIN details"""
		if not hasattr(frappe.local, "gstin_cache"):
			frappe.local.gstin_cache = {}

		key = gstin
		gsp_connector = GSPConnector()
		details = gsp_connector.fetch_gstin_details(gstin)

		frappe.local.gstin_cache[key] = details
		frappe.cache().hset("gstin_cache", key, details)
		return details

	def generate_irn(self):
		data = {}
		try:
			headers = self.get_headers()
			einvoice = make_einvoice(self.invoice)
			data = json.dumps(einvoice, indent=4)
			res = self.make_request("post", self.generate_irn_url, headers, data)

			if res.get("success"):
				self.set_einvoice_data(res.get("result"))

			elif "2150" in res.get("message"):
				# IRN already generated but not updated in invoice
				# Extract the IRN from the response description and fetch irn details
				irn = res.get("result")[0].get("Desc").get("Irn")
				irn_details = self.get_irn_details(irn)
				if irn_details:
					self.set_einvoice_data(irn_details)
				else:
					raise RequestFailed(
						"IRN has already been generated for the invoice but cannot fetch details for the it. \
						Contact ERPNext support to resolve the issue."
					)

			else:
				raise RequestFailed

		except RequestFailed:
			errors = self.sanitize_error_message(res.get("message"))
			self.set_failed_status(errors=errors)
			self.raise_error(errors=errors)

		except Exception as e:
			self.set_failed_status(errors=str(e))
			log_error(data)
			self.raise_error(True)

	@staticmethod
	def bulk_generate_irn(invoices):
		gsp_connector = GSPConnector()
		gsp_connector.doctype = "Sales Invoice"

		failed = []

		for invoice in invoices:
			try:
				gsp_connector.docname = invoice
				gsp_connector.set_invoice()
				gsp_connector.set_credentials()
				gsp_connector.generate_irn()

			except Exception as e:
				failed.append({"docname": invoice, "message": str(e)})

		return failed

	def fetch_and_attach_qrcode_from_irn(self):
		is_qrcode_file_attached = self.invoice.qrcode_image and frappe.db.exists(
			"File",
			{
				"attached_to_doctype": "Sales Invoice",
				"attached_to_name": self.invoice.name,
				"file_url": self.invoice.qrcode_image,
				"attached_to_field": "qrcode_image",
			},
		)
		if not is_qrcode_file_attached:
			if self.invoice.signed_qr_code:
				self.attach_qrcode_image()
				frappe.db.set_value(
					"Sales Invoice", self.invoice.name, "qrcode_image", self.invoice.qrcode_image
				)
				frappe.msgprint(_("QR Code attached to the invoice."), alert=True)
			else:
				qrcode = self.get_qrcode_from_irn(self.invoice.irn)
				if qrcode:
					qrcode_file = self.create_qr_code_file(qrcode)
					frappe.db.set_value("Sales Invoice", self.invoice.name, "qrcode_image", qrcode_file.file_url)
					frappe.msgprint(_("QR Code attached to the invoice."), alert=True)
				else:
					frappe.msgprint(_("QR Code not found for the IRN"), alert=True)
		else:
			frappe.msgprint(_("QR Code is already Attached"), indicator="green", alert=True)

	def get_qrcode_from_irn(self, irn):
		import requests

		headers = self.get_headers()
		headers.update({"width": "215", "height": "215", "imgtype": "jpg", "irn": irn})

		try:
			# using requests.get instead of make_request to avoid parsing the response
			res = requests.get(self.get_qrcode_url, headers=headers)
			self.log_request(self.get_qrcode_url, headers, None, None)
			if res.status_code == 200:
				return res.content
			else:
				raise RequestFailed(str(res.content, "utf-8"))

		except RequestFailed as e:
			self.raise_error(errors=str(e))

		except Exception:
			log_error()
			self.raise_error()

	def get_irn_details(self, irn):
		headers = self.get_headers()

		try:
			params = "?irn={irn}".format(irn=irn)
			res = self.make_request("get", self.irn_details_url + params, headers)
			if res.get("success"):
				return res.get("result")
			else:
				raise RequestFailed

		except RequestFailed:
			errors = self.sanitize_error_message(res.get("message"))
			self.raise_error(errors=errors)

		except Exception:
			log_error()
			self.raise_error(True)

	def cancel_irn(self, irn, reason, remark):
		data, res = {}, {}
		try:
			# validate cancellation
			if time_diff_in_hours(now_datetime(), self.invoice.ack_date) > 24:
				frappe.throw(
					_("E-Invoice cannot be cancelled after 24 hours of IRN generation."),
					title=_("Not Allowed"),
					exc=CancellationNotAllowed,
				)
			if not irn:
				frappe.throw(
					_("IRN not found. You must generate IRN before cancelling."),
					title=_("Not Allowed"),
					exc=CancellationNotAllowed,
				)

			headers = self.get_headers()
			data = json.dumps({"Irn": irn, "Cnlrsn": reason, "Cnlrem": remark}, indent=4)

			res = self.make_request("post", self.cancel_irn_url, headers, data)
			if res.get("success") or "9999" in res.get("message"):
				self.invoice.irn_cancelled = 1
				self.invoice.irn_cancel_date = res.get("result")["CancelDate"] if res.get("result") else ""
				self.invoice.einvoice_status = "Cancelled"
				self.invoice.flags.updater_reference = {
					"doctype": self.invoice.doctype,
					"docname": self.invoice.name,
					"label": _("IRN Cancelled - {}").format(remark),
				}
				self.update_invoice()

			else:
				raise RequestFailed

		except RequestFailed:
			errors = self.sanitize_error_message(res.get("message"))
			self.set_failed_status(errors=errors)
			self.raise_error(errors=errors)

		except CancellationNotAllowed as e:
			self.set_failed_status(errors=str(e))
			self.raise_error(errors=str(e))

		except Exception as e:
			self.set_failed_status(errors=str(e))
			log_error(data)
			self.raise_error(True)

	@staticmethod
	def bulk_cancel_irn(invoices, reason, remark):
		gsp_connector = GSPConnector()
		gsp_connector.doctype = "Sales Invoice"

		failed = []

		for invoice in invoices:
			try:
				gsp_connector.docname = invoice
				gsp_connector.set_invoice()
				gsp_connector.set_credentials()
				irn = gsp_connector.invoice.irn
				gsp_connector.cancel_irn(irn, reason, remark)

			except Exception as e:
				failed.append({"docname": invoice, "message": str(e)})

		return failed

	def generate_eway_bill(self, **kwargs):
		args = frappe._dict(kwargs)

		headers = self.get_headers()
		eway_bill_details = get_eway_bill_details(args)
		data = json.dumps(
			{
				"Irn": args.irn,
				"Distance": cint(eway_bill_details.distance),
				"TransMode": eway_bill_details.mode_of_transport,
				"TransId": eway_bill_details.gstin,
				"TransName": eway_bill_details.name,
				"TrnDocDt": eway_bill_details.document_date,
				"TrnDocNo": eway_bill_details.document_name,
				"VehNo": eway_bill_details.vehicle_no,
				"VehType": eway_bill_details.vehicle_type,
			},
			indent=4,
		)

		try:
			res = self.make_request("post", self.generate_ewaybill_url, headers, data)
			if res.get("success"):
				self.invoice.ewaybill = res.get("result").get("EwbNo")
				self.invoice.eway_bill_validity = res.get("result").get("EwbValidTill")
				self.invoice.eway_bill_cancelled = 0
				self.invoice.update(args)
				if res.get("info"):
					info = res.get("info")
					# when we have more features (responses) in eway bill, we can add them using below forloop.
					for msg in info:
						if msg.get("InfCd") == "EWBPPD":
							pin_to_pin_distance = int(re.search(r"\d+", msg.get("Desc")).group())
							frappe.msgprint(
								_("Auto Calculated Distance is {} KM.").format(str(pin_to_pin_distance)),
								title="Notification",
								indicator="green",
								alert=True,
							)
							self.invoice.distance = flt(pin_to_pin_distance)
				self.invoice.flags.updater_reference = {
					"doctype": self.invoice.doctype,
					"docname": self.invoice.name,
					"label": _("E-Way Bill Generated"),
				}
				self.update_invoice()

			else:
				raise RequestFailed

		except RequestFailed:
			errors = self.sanitize_error_message(res.get("message"))
			self.raise_error(errors=errors)

		except Exception:
			log_error(data)
			self.raise_error(True)

	def get_ewb_details(self):
		"""
		Get e-Waybill Details by IRN API documentaion for validation is not added yet.
		https://einv-apisandbox.nic.in/version1.03/get-ewaybill-details-by-irn.html#validations
		NOTE: if ewaybill Validity period lapsed or scanned by officer enroute (not tested yet) it will still return status as "ACT".
		"""
		headers = self.get_headers()
		irn = self.invoice.irn
		if not irn:
			frappe.throw(_("IRN is mandatory to get E-Waybill Details. Please generate IRN first."))

		try:
			params = "?irn={irn}".format(irn=irn)
			res = self.make_request("get", self.ewaybill_details_url + params, headers)
			if res.get("success"):
				return res.get("result")
			else:
				raise RequestFailed

		except RequestFailed:
			errors = self.sanitize_error_message(res.get("message"))
			self.raise_error(errors=errors)

		except Exception:
			log_error()
			self.raise_error(True)

	def update_ewb_details(self, ewb_details=None):
		# for any reason user chooses to generate eway bill using portal this will allow to update ewaybill details in the invoice.
		if not self.invoice.irn:
			frappe.throw(_("IRN is mandatory to update E-Waybill Details. Please generate IRN first."))
		if not ewb_details:
			ewb_details = self.get_ewb_details()
		if ewb_details:
			self.invoice.ewaybill = ewb_details.get("EwbNo")
			self.invoice.eway_bill_validity = ewb_details.get("EwbValidTill")
			self.invoice.eway_bill_cancelled = 0 if ewb_details.get("Status") == "ACT" else 1
			self.update_invoice()

	def cancel_eway_bill(self):
		ewb_details = self.get_ewb_details()
		if ewb_details:
			ewb_no = str(ewb_details.get("EwbNo"))
			ewb_status = ewb_details.get("Status")
			if ewb_status == "CNL":
				self.invoice.ewaybill = ""
				self.invoice.eway_bill_cancelled = 1
				self.invoice.flags.updater_reference = {
					"doctype": self.invoice.doctype,
					"docname": self.invoice.name,
					"label": _("E-Way Bill Cancelled"),
				}
				self.update_invoice()
				frappe.msgprint(
					_("E-Way Bill Cancelled successfully"),
					indicator="green",
					alert=True,
				)
			elif ewb_status == "ACT" and self.invoice.ewaybill == ewb_no:
				msg = _("E-Way Bill {} is still active.").format(bold(ewb_no))
				msg += "<br><br>"
				msg += _(
					"You must first use the portal to cancel the e-way bill and then update the cancelled status in the ERPNext system."
				)
				frappe.msgprint(msg)
			elif ewb_status == "ACT" and self.invoice.ewaybill != ewb_no:
				# if user cancelled the current eway bill and generated new eway bill using portal, then this will update new ewb number in sales invoice.
				msg = _("E-Way Bill No. {0} doesn't match {1} saved in the invoice.").format(
					bold(ewb_no), bold(self.invoice.ewaybill)
				)
				msg += "<hr/>"
				msg += _("E-Way Bill No. {} is updated in the invoice.").format(bold(ewb_no))
				frappe.msgprint(msg)
				self.update_ewb_details(ewb_details=ewb_details)
			else:
				# this block should not be ever called but added incase there is any change in API.
				msg = _("Unknown E-Way Status Code {}.").format(ewb_status)
				msg += "<br><br>"
				msg += _("Please contact your system administrator.")
				frappe.throw(msg)
		else:
			frappe.msgprint(_("E-Way Bill Details not found for this IRN."))

	def sanitize_error_message(self, message):
		"""
		On validation errors, response message looks something like this:
		message = '2174 : For inter-state transaction, CGST and SGST amounts are not applicable; only IGST amount is applicable,
		                        3095 : Supplier GSTIN is inactive'
		we search for string between ':' to extract the error messages
		errors = [
		        ': For inter-state transaction, CGST and SGST amounts are not applicable; only IGST amount is applicable, 3095 ',
		        ': Test'
		]
		then we trim down the message by looping over errors
		"""
		if not message:
			return []

		errors = re.findall(": [^:]+", message)
		for idx, e in enumerate(errors):
			# remove colons
			errors[idx] = errors[idx].replace(":", "").strip()
			# if not last
			if idx != len(errors) - 1:
				# remove last 7 chars eg: ', 3095 '
				errors[idx] = errors[idx][:-6]

		return errors

	def raise_error(self, raise_exception=False, errors=None):
		title = _("E Invoice Request Failed")
		if errors:
			frappe.throw(errors, title=title, as_list=1)
		else:
			link_to_error_list = '<a href="/app/error-log" target="_blank">Error Log</a>'
			frappe.msgprint(
				_(
					"An error occurred while making e-invoicing request. Please check {} for more information."
				).format(link_to_error_list),
				title=title,
				raise_exception=raise_exception,
				indicator="red",
			)

	def set_einvoice_data(self, res):
		enc_signed_invoice = res.get("SignedInvoice")
		dec_signed_invoice = jwt.decode(enc_signed_invoice, verify=False)["data"]

		self.invoice.irn = res.get("Irn")
		self.invoice.ewaybill = res.get("EwbNo")
		self.invoice.eway_bill_validity = res.get("EwbValidTill")
		self.invoice.ack_no = res.get("AckNo")
		self.invoice.ack_date = res.get("AckDt")
		self.invoice.signed_einvoice = dec_signed_invoice
		self.invoice.ack_no = res.get("AckNo")
		self.invoice.ack_date = res.get("AckDt")
		self.invoice.signed_qr_code = res.get("SignedQRCode")
		self.invoice.einvoice_status = "Generated"

		self.attach_qrcode_image()

		self.invoice.flags.updater_reference = {
			"doctype": self.invoice.doctype,
			"docname": self.invoice.name,
			"label": _("IRN Generated"),
		}
		self.update_invoice()

	def attach_qrcode_image(self):
		qrcode = self.invoice.signed_qr_code
		qr_image = io.BytesIO()
		url = qrcreate(qrcode, error="L")
		url.png(qr_image, scale=2, quiet_zone=1)
		qrcode_file = self.create_qr_code_file(qr_image.getvalue())
		self.invoice.qrcode_image = qrcode_file.file_url

	def create_qr_code_file(self, qr_image):
		doctype = self.invoice.doctype
		docname = self.invoice.name
		filename = "QRCode_{}.png".format(docname).replace(os.path.sep, "__")

		_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": filename,
				"attached_to_doctype": doctype,
				"attached_to_name": docname,
				"attached_to_field": "qrcode_image",
				"is_private": 0,
				"content": qr_image,
			}
		)
		_file.save()
		frappe.db.commit()
		return _file

	def update_invoice(self):
		self.invoice.flags.ignore_validate_update_after_submit = True
		self.invoice.flags.ignore_validate = True
		self.invoice.save()

	def set_failed_status(self, errors=None):
		frappe.db.rollback()
		self.invoice.einvoice_status = "Failed"
		self.invoice.failure_description = self.get_failure_message(errors) if errors else ""
		self.update_invoice()
		frappe.db.commit()

	def get_failure_message(self, errors):
		if isinstance(errors, list):
			errors = ", ".join(errors)
		return errors


def sanitize_for_json(string):
	"""Escape JSON specific characters from a string."""

	# json.dumps adds double-quotes to the string. Indexing to remove them.
	return json.dumps(string)[1:-1]


@frappe.whitelist()
def get_einvoice(doctype, docname):
	invoice = frappe.get_doc(doctype, docname)
	return make_einvoice(invoice)


@frappe.whitelist()
def generate_irn(doctype, docname):
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.generate_irn()


@frappe.whitelist()
def cancel_irn(doctype, docname, irn, reason, remark):
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.cancel_irn(irn, reason, remark)


@frappe.whitelist()
def generate_qrcode(doctype, docname):
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.fetch_and_attach_qrcode_from_irn()


@frappe.whitelist()
def generate_eway_bill(doctype, docname, **kwargs):
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.generate_eway_bill(**kwargs)


@frappe.whitelist()
def cancel_eway_bill(doctype, docname):
	# NOTE: cancel_eway_bill api is disabled by NIC for E-invoice so this will only check if eway bill is canceled or not and update accordingly.
	# https://einv-apisandbox.nic.in/version1.03/cancel-eway-bill.html#
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.cancel_eway_bill()


@frappe.whitelist()
def get_ewb_details(doctype, docname):
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.get_ewb_details()


@frappe.whitelist()
def update_ewb_details(doctype, docname):
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.update_ewb_details()


@frappe.whitelist()
def generate_einvoices(docnames):
	docnames = json.loads(docnames) or []

	if len(docnames) < 10:
		failures = GSPConnector.bulk_generate_irn(docnames)
		frappe.local.message_log = []

		if failures:
			show_bulk_action_failure_message(failures)

		success = len(docnames) - len(failures)
		frappe.msgprint(
			_("{} e-invoices generated successfully").format(success),
			title=_("Bulk E-Invoice Generation Complete"),
		)

	else:
		enqueue_bulk_action(schedule_bulk_generate_irn, docnames=docnames)


def schedule_bulk_generate_irn(docnames):
	failures = GSPConnector.bulk_generate_irn(docnames)
	frappe.local.message_log = []

	frappe.publish_realtime(
		"bulk_einvoice_generation_complete",
		{"user": frappe.session.user, "failures": failures, "invoices": docnames},
	)


def show_bulk_action_failure_message(failures):
	for doc in failures:
		docname = '<a href="sales-invoice/{0}">{0}</a>'.format(doc.get("docname"))
		message = doc.get("message").replace("'", '"')
		if message[0] == "[":
			errors = json.loads(message)
			error_list = "".join(["<li>{}</li>".format(err) for err in errors])
			message = """{} has following errors:<br>
				<ul style="padding-left: 20px; padding-top: 5px">{}</ul>""".format(
				docname, error_list
			)
		else:
			message = "{} - {}".format(docname, message)

		frappe.msgprint(message, title=_("Bulk E-Invoice Generation Complete"), indicator="red")


@frappe.whitelist()
def cancel_irns(docnames, reason, remark):
	docnames = json.loads(docnames) or []

	if len(docnames) < 10:
		failures = GSPConnector.bulk_cancel_irn(docnames, reason, remark)
		frappe.local.message_log = []

		if failures:
			show_bulk_action_failure_message(failures)

		success = len(docnames) - len(failures)
		frappe.msgprint(
			_("{} e-invoices cancelled successfully").format(success),
			title=_("Bulk E-Invoice Cancellation Complete"),
		)
	else:
		enqueue_bulk_action(schedule_bulk_cancel_irn, docnames=docnames, reason=reason, remark=remark)


def schedule_bulk_cancel_irn(docnames, reason, remark):
	failures = GSPConnector.bulk_cancel_irn(docnames, reason, remark)
	frappe.local.message_log = []

	frappe.publish_realtime(
		"bulk_einvoice_cancellation_complete",
		{"user": frappe.session.user, "failures": failures, "invoices": docnames},
	)


def enqueue_bulk_action(job, **kwargs):
	check_scheduler_status()

	enqueue(
		job,
		**kwargs,
		queue="long",
		timeout=10000,
		event="processing_bulk_einvoice_action",
		now=frappe.conf.developer_mode or frappe.flags.in_test,
	)

	if job == schedule_bulk_generate_irn:
		msg = _("E-Invoices will be generated in a background process.")
	else:
		msg = _("E-Invoices will be cancelled in a background process.")

	frappe.msgprint(msg, alert=1)


def check_scheduler_status():
	if is_scheduler_inactive() and not frappe.flags.in_test:
		frappe.throw(_("Scheduler is inactive. Cannot enqueue job."), title=_("Scheduler Inactive"))


def job_already_enqueued(job_name):
	enqueued_jobs = [d.get("job_name") for d in get_info()]
	if job_name in enqueued_jobs:
		return True
