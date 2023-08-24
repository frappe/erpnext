import io
import json

import frappe
from frappe import _
from frappe.utils import cstr, flt
from frappe.utils.file_manager import remove_file

from erpnext.controllers.taxes_and_totals import get_itemised_tax
from erpnext.regional.italy import state_codes


def update_itemised_tax_data(doc):
	if not doc.taxes:
		return

	if doc.doctype == "Purchase Invoice":
		return

	itemised_tax = get_itemised_tax(doc.taxes)

	for row in doc.items:
		tax_rate = 0.0
		if itemised_tax.get(row.item_code):
			tax_rate = sum([tax.get("tax_rate", 0) for d, tax in itemised_tax.get(row.item_code).items()])

		row.tax_rate = flt(tax_rate, row.precision("tax_rate"))
		row.tax_amount = flt((row.net_amount * tax_rate) / 100, row.precision("net_amount"))
		row.total_amount = flt((row.net_amount + row.tax_amount), row.precision("total_amount"))


@frappe.whitelist()
def export_invoices(filters=None):
	frappe.has_permission("Sales Invoice", throw=True)

	invoices = frappe.get_all(
		"Sales Invoice", filters=get_conditions(filters), fields=["name", "company_tax_id"]
	)

	attachments = get_e_invoice_attachments(invoices)

	zip_filename = "{0}-einvoices.zip".format(frappe.utils.get_datetime().strftime("%Y%m%d_%H%M%S"))

	download_zip(attachments, zip_filename)


def prepare_invoice(invoice, progressive_number):
	# set company information
	company = frappe.get_doc("Company", invoice.company)

	invoice.progressive_number = progressive_number
	invoice.unamended_name = get_unamended_name(invoice)
	invoice.company_data = company
	company_address = frappe.get_doc("Address", invoice.company_address)
	invoice.company_address_data = company_address

	# Set invoice type
	if not invoice.type_of_document:
		if invoice.is_return and invoice.return_against:
			invoice.type_of_document = "TD04"  # Credit Note (Nota di Credito)
			invoice.return_against_unamended = get_unamended_name(
				frappe.get_doc("Sales Invoice", invoice.return_against)
			)
		else:
			invoice.type_of_document = "TD01"  # Sales Invoice (Fattura)

	# set customer information
	invoice.customer_data = frappe.get_doc("Customer", invoice.customer)
	customer_address = frappe.get_doc("Address", invoice.customer_address)
	invoice.customer_address_data = customer_address

	if invoice.shipping_address_name:
		invoice.shipping_address_data = frappe.get_doc("Address", invoice.shipping_address_name)

	if invoice.customer_data.is_public_administration:
		invoice.transmission_format_code = "FPA12"
	else:
		invoice.transmission_format_code = "FPR12"

	invoice.e_invoice_items = [item for item in invoice.items]
	tax_data = get_invoice_summary(invoice.e_invoice_items, invoice.taxes)
	invoice.tax_data = tax_data

	# Check if stamp duty (Bollo) of 2 EUR exists.
	stamp_duty_charge_row = next(
		(tax for tax in invoice.taxes if tax.charge_type == "Actual" and tax.tax_amount == 2.0), None
	)
	if stamp_duty_charge_row:
		invoice.stamp_duty = stamp_duty_charge_row.tax_amount

	for item in invoice.e_invoice_items:
		if item.tax_rate == 0.0 and item.tax_amount == 0.0 and tax_data.get("0.0"):
			item.tax_exemption_reason = tax_data["0.0"]["tax_exemption_reason"]

	customer_po_data = {}
	for d in invoice.e_invoice_items:
		if d.customer_po_no and d.customer_po_date and d.customer_po_no not in customer_po_data:
			customer_po_data[d.customer_po_no] = d.customer_po_date

	invoice.customer_po_data = customer_po_data

	return invoice


def get_conditions(filters):
	filters = json.loads(filters)

	conditions = {"docstatus": 1, "company_tax_id": ("!=", "")}

	if filters.get("company"):
		conditions["company"] = filters["company"]
	if filters.get("customer"):
		conditions["customer"] = filters["customer"]

	if filters.get("from_date"):
		conditions["posting_date"] = (">=", filters["from_date"])
	if filters.get("to_date"):
		conditions["posting_date"] = ("<=", filters["to_date"])

	if filters.get("from_date") and filters.get("to_date"):
		conditions["posting_date"] = ("between", [filters.get("from_date"), filters.get("to_date")])

	return conditions


def download_zip(files, output_filename):
	import zipfile

	zip_stream = io.BytesIO()
	with zipfile.ZipFile(zip_stream, "w", zipfile.ZIP_DEFLATED) as zip_file:
		for file in files:
			file_path = frappe.utils.get_files_path(file.file_name, is_private=file.is_private)

			zip_file.write(file_path, arcname=file.file_name)

	frappe.local.response.filename = output_filename
	frappe.local.response.filecontent = zip_stream.getvalue()
	frappe.local.response.type = "download"
	zip_stream.close()


def get_invoice_summary(items, taxes):
	summary_data = frappe._dict()
	for tax in taxes:
		# Include only VAT charges.
		if tax.charge_type == "Actual":
			continue

		# Charges to appear as items in the e-invoice.
		if tax.charge_type in ["On Previous Row Total", "On Previous Row Amount"]:
			reference_row = next((row for row in taxes if row.idx == int(tax.row_id or 0)), None)
			if reference_row:
				items.append(
					frappe._dict(
						idx=len(items) + 1,
						item_code=reference_row.description,
						item_name=reference_row.description,
						description=reference_row.description,
						rate=reference_row.tax_amount,
						qty=1.0,
						amount=reference_row.tax_amount,
						stock_uom=frappe.db.get_single_value("Stock Settings", "stock_uom") or _("Nos"),
						tax_rate=tax.rate,
						tax_amount=(reference_row.tax_amount * tax.rate) / 100,
						net_amount=reference_row.tax_amount,
						taxable_amount=reference_row.tax_amount,
						item_tax_rate={tax.account_head: tax.rate},
						charges=True,
					)
				)

		# Check item tax rates if tax rate is zero.
		if tax.rate == 0:
			for item in items:
				item_tax_rate = item.item_tax_rate
				if isinstance(item.item_tax_rate, str):
					item_tax_rate = json.loads(item.item_tax_rate)

				if item_tax_rate and tax.account_head in item_tax_rate:
					key = cstr(item_tax_rate[tax.account_head])
					if key not in summary_data:
						summary_data.setdefault(
							key,
							{
								"tax_amount": 0.0,
								"taxable_amount": 0.0,
								"tax_exemption_reason": "",
								"tax_exemption_law": "",
							},
						)

					summary_data[key]["tax_amount"] += item.tax_amount
					summary_data[key]["taxable_amount"] += item.net_amount
					if key == "0.0":
						summary_data[key]["tax_exemption_reason"] = tax.tax_exemption_reason
						summary_data[key]["tax_exemption_law"] = tax.tax_exemption_law

			if summary_data.get("0.0") and tax.charge_type in [
				"On Previous Row Total",
				"On Previous Row Amount",
			]:
				summary_data[key]["taxable_amount"] = tax.total

			if summary_data == {}:  # Implies that Zero VAT has not been set on any item.
				summary_data.setdefault(
					"0.0",
					{
						"tax_amount": 0.0,
						"taxable_amount": tax.total,
						"tax_exemption_reason": tax.tax_exemption_reason,
						"tax_exemption_law": tax.tax_exemption_law,
					},
				)

		else:
			item_wise_tax_detail = json.loads(tax.item_wise_tax_detail)
			for rate_item in [
				tax_item for tax_item in item_wise_tax_detail.items() if tax_item[1][0] == tax.rate
			]:
				key = cstr(tax.rate)
				if not summary_data.get(key):
					summary_data.setdefault(key, {"tax_amount": 0.0, "taxable_amount": 0.0})
				summary_data[key]["tax_amount"] += rate_item[1][1]
				summary_data[key]["taxable_amount"] += sum(
					[item.net_amount for item in items if item.item_code == rate_item[0]]
				)

			for item in items:
				key = cstr(tax.rate)
				if item.get("charges"):
					if not summary_data.get(key):
						summary_data.setdefault(key, {"taxable_amount": 0.0})
					summary_data[key]["taxable_amount"] += item.taxable_amount

	return summary_data


# Preflight for successful e-invoice export.
def sales_invoice_validate(doc):
	# Validate company
	if doc.doctype != "Sales Invoice":
		return

	if not doc.company_address:
		frappe.throw(
			_("Please set an Address on the Company '%s'" % doc.company),
			title=_("E-Invoicing Information Missing"),
		)
	else:
		validate_address(doc.company_address)

	company_fiscal_regime = frappe.get_cached_value("Company", doc.company, "fiscal_regime")
	if not company_fiscal_regime:
		frappe.throw(
			_("Fiscal Regime is mandatory, kindly set the fiscal regime in the company {0}").format(
				doc.company
			)
		)
	else:
		doc.company_fiscal_regime = company_fiscal_regime

	doc.company_tax_id = frappe.get_cached_value("Company", doc.company, "tax_id")
	doc.company_fiscal_code = frappe.get_cached_value("Company", doc.company, "fiscal_code")
	if not doc.company_tax_id and not doc.company_fiscal_code:
		frappe.throw(
			_("Please set either the Tax ID or Fiscal Code on Company '%s'" % doc.company),
			title=_("E-Invoicing Information Missing"),
		)

	# Validate customer details
	customer = frappe.get_doc("Customer", doc.customer)

	if customer.customer_type == "Individual":
		doc.customer_fiscal_code = customer.fiscal_code
		if not doc.customer_fiscal_code:
			frappe.throw(
				_("Please set Fiscal Code for the customer '%s'" % doc.customer),
				title=_("E-Invoicing Information Missing"),
			)
	else:
		if customer.is_public_administration:
			doc.customer_fiscal_code = customer.fiscal_code
			if not doc.customer_fiscal_code:
				frappe.throw(
					_("Please set Fiscal Code for the public administration '%s'" % doc.customer),
					title=_("E-Invoicing Information Missing"),
				)
		else:
			doc.tax_id = customer.tax_id
			if not doc.tax_id:
				frappe.throw(
					_("Please set Tax ID for the customer '%s'" % doc.customer),
					title=_("E-Invoicing Information Missing"),
				)

	if not doc.customer_address:
		frappe.throw(_("Please set the Customer Address"), title=_("E-Invoicing Information Missing"))
	else:
		validate_address(doc.customer_address)

	if not len(doc.taxes):
		frappe.throw(
			_("Please set at least one row in the Taxes and Charges Table"),
			title=_("E-Invoicing Information Missing"),
		)
	else:
		for row in doc.taxes:
			if row.rate == 0 and row.tax_amount == 0 and not row.tax_exemption_reason:
				frappe.throw(
					_("Row {0}: Please set at Tax Exemption Reason in Sales Taxes and Charges").format(row.idx),
					title=_("E-Invoicing Information Missing"),
				)

	for schedule in doc.payment_schedule:
		if schedule.mode_of_payment and not schedule.mode_of_payment_code:
			schedule.mode_of_payment_code = frappe.get_cached_value(
				"Mode of Payment", schedule.mode_of_payment, "mode_of_payment_code"
			)


# Ensure payment details are valid for e-invoice.
def sales_invoice_on_submit(doc, method):
	# Validate payment details
	if get_company_country(doc.company) not in [
		"Italy",
		"Italia",
		"Italian Republic",
		"Repubblica Italiana",
	]:
		return

	if not len(doc.payment_schedule):
		frappe.throw(_("Please set the Payment Schedule"), title=_("E-Invoicing Information Missing"))
	else:
		for schedule in doc.payment_schedule:
			if not schedule.mode_of_payment:
				frappe.throw(
					_("Row {0}: Please set the Mode of Payment in Payment Schedule").format(schedule.idx),
					title=_("E-Invoicing Information Missing"),
				)
			elif not frappe.db.get_value(
				"Mode of Payment", schedule.mode_of_payment, "mode_of_payment_code"
			):
				frappe.throw(
					_("Row {0}: Please set the correct code on Mode of Payment {1}").format(
						schedule.idx, schedule.mode_of_payment
					),
					title=_("E-Invoicing Information Missing"),
				)

	prepare_and_attach_invoice(doc)


def prepare_and_attach_invoice(doc, replace=False):
	progressive_name, progressive_number = get_progressive_name_and_number(doc, replace)

	invoice = prepare_invoice(doc, progressive_number)
	item_meta = frappe.get_meta("Sales Invoice Item")

	invoice_xml = frappe.render_template(
		"erpnext/regional/italy/e-invoice.xml",
		context={"doc": invoice, "item_meta": item_meta},
		is_path=True,
	)

	invoice_xml = invoice_xml.replace("&", "&amp;")

	xml_filename = progressive_name + ".xml"

	_file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": xml_filename,
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"is_private": True,
			"content": invoice_xml,
		}
	)
	_file.save()
	return _file


@frappe.whitelist()
def generate_single_invoice(docname):
	doc = frappe.get_doc("Sales Invoice", docname)
	frappe.has_permission("Sales Invoice", doc=doc, throw=True)

	e_invoice = prepare_and_attach_invoice(doc, True)
	return e_invoice.file_url


# Delete e-invoice attachment on cancel.
def sales_invoice_on_cancel(doc, method):
	if get_company_country(doc.company) not in [
		"Italy",
		"Italia",
		"Italian Republic",
		"Repubblica Italiana",
	]:
		return

	for attachment in get_e_invoice_attachments(doc):
		remove_file(attachment.name, attached_to_doctype=doc.doctype, attached_to_name=doc.name)


def get_company_country(company):
	return frappe.get_cached_value("Company", company, "country")


def get_e_invoice_attachments(invoices):
	if not isinstance(invoices, list):
		if not invoices.company_tax_id:
			return

		invoices = [invoices]

	tax_id_map = {
		invoice.name: (
			invoice.company_tax_id
			if invoice.company_tax_id.startswith("IT")
			else "IT" + invoice.company_tax_id
		)
		for invoice in invoices
	}

	attachments = frappe.get_all(
		"File",
		fields=("name", "file_name", "attached_to_name", "is_private"),
		filters={"attached_to_name": ("in", tax_id_map), "attached_to_doctype": "Sales Invoice"},
	)

	out = []
	for attachment in attachments:
		if (
			attachment.file_name
			and attachment.file_name.endswith(".xml")
			and attachment.file_name.startswith(tax_id_map.get(attachment.attached_to_name))
		):
			out.append(attachment)

	return out


def validate_address(address_name):
	fields = ["pincode", "city", "country_code"]
	data = frappe.get_cached_value("Address", address_name, fields, as_dict=1) or {}

	for field in fields:
		if not data.get(field):
			frappe.throw(
				_("Please set {0} for address {1}").format(field.replace("-", ""), address_name),
				title=_("E-Invoicing Information Missing"),
			)


def get_unamended_name(doc):
	attributes = ["naming_series", "amended_from"]
	for attribute in attributes:
		if not hasattr(doc, attribute):
			return doc.name

	if doc.amended_from:
		return "-".join(doc.name.split("-")[:-1])
	else:
		return doc.name


def get_progressive_name_and_number(doc, replace=False):
	if replace:
		for attachment in get_e_invoice_attachments(doc):
			remove_file(attachment.name, attached_to_doctype=doc.doctype, attached_to_name=doc.name)
			filename = attachment.file_name.split(".xml")[0]
			return filename, filename.split("_")[1]

	company_tax_id = (
		doc.company_tax_id if doc.company_tax_id.startswith("IT") else "IT" + doc.company_tax_id
	)
	progressive_name = frappe.model.naming.make_autoname(company_tax_id + "_.#####")
	progressive_number = progressive_name.split("_")[1]

	return progressive_name, progressive_number


def set_state_code(doc, method):
	if doc.get("country_code"):
		doc.country_code = doc.country_code.upper()

	if not doc.get("state"):
		return

	if not (
		hasattr(doc, "state_code")
		and doc.country in ["Italy", "Italia", "Italian Republic", "Repubblica Italiana"]
	):
		return

	state_codes_lower = {key.lower(): value for key, value in state_codes.items()}

	state = doc.get("state", "").lower()
	if state_codes_lower.get(state):
		doc.state_code = state_codes_lower.get(state)
