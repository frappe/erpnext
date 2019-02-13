import frappe, json, os
from frappe.utils import flt
from erpnext.controllers.taxes_and_totals import get_itemised_tax
from frappe import _
from frappe.utils.file_manager import save_file, remove_file
from frappe.desk.form.load import get_attachments


def update_itemised_tax_data(doc):
	if not doc.taxes: return

	itemised_tax = get_itemised_tax(doc.taxes)

	for row in doc.items:
		tax_rate = 0.0
		if itemised_tax.get(row.item_code):
			tax_rate = sum([tax.get('tax_rate', 0) for d, tax in itemised_tax.get(row.item_code).items()])

		row.tax_rate = flt(tax_rate, row.precision("tax_rate"))
		row.tax_amount = flt((row.net_amount * tax_rate) / 100, row.precision("net_amount"))
		row.total_amount = flt((row.net_amount + row.tax_amount), row.precision("total_amount"))

@frappe.whitelist()
def export_invoices(filters=None):
	saved_xmls = []

	invoices = frappe.get_all("Sales Invoice", filters=get_conditions(filters), fields=["*"])

	for invoice in invoices:
		attachments = get_e_invoice_attachments(invoice)
		saved_xmls += [attachment.file_name for attachment in attachments]

	zip_filename = "{0}-einvoices.zip".format(frappe.utils.get_datetime().strftime("%Y%m%d_%H%M%S"))

	download_zip(saved_xmls, zip_filename)


@frappe.whitelist()
def prepare_invoice(invoice, progressive_number):
	#set company information
	company = frappe.get_doc("Company", invoice.company)

	invoice.progressive_number = progressive_number
	invoice.unamended_name = get_unamended_name(invoice)
	invoice.company_data = company
	company_address = frappe.get_doc("Address", invoice.company_address)
	invoice.company_address_data = company_address

	#Set invoice type
	if invoice.is_return and invoice.return_against:
		invoice.type_of_document = "TD04" #Credit Note (Nota di Credito)
		invoice.return_against_unamended =  get_unamended_name(frappe.get_doc("Sales Invoice", invoice.return_against))
	else:
		invoice.type_of_document = "TD01" #Sales Invoice (Fattura)

	#set customer information
	invoice.customer_data = frappe.get_doc("Customer", invoice.customer)
	customer_address = frappe.get_doc("Address", invoice.customer_address)
	invoice.customer_address_data = customer_address

	if invoice.shipping_address_name:
		invoice.shipping_address_data = frappe.get_doc("Address", invoice.shipping_address_name)

	if invoice.customer_data.is_public_administration:
		invoice.transmission_format_code = "FPA12"
	else:
		invoice.transmission_format_code = "FPR12"

	tax_data = get_invoice_summary(invoice.items, invoice.taxes)
	invoice.tax_data = tax_data

	#Check if stamp duty (Bollo) of 2 EUR exists.
	stamp_duty_charge_row = next((tax for tax in invoice.taxes if tax.charge_type == _("Actual") and tax.tax_amount == 2.0 ), None)
	if stamp_duty_charge_row:
		invoice.stamp_duty = stamp_duty_charge_row.tax_amount

	for item in invoice.items:
		if item.tax_rate == 0.0:
			item.tax_exemption_reason = tax_data["0.0"]["tax_exemption_reason"]

	return invoice

def get_conditions(filters):
	filters = json.loads(filters)

	conditions = {"docstatus": 1}

	if filters.get("company"): conditions["company"] = filters["company"]
	if filters.get("customer"): conditions["customer"] =  filters["customer"]

	if filters.get("from_date"): conditions["posting_date"] = (">=", filters["from_date"])
	if filters.get("to_date"): conditions["posting_date"] = ("<=", filters["to_date"])

	if filters.get("from_date") and filters.get("to_date"):
		conditions["posting_date"] = ("between", [filters.get("from_date"), filters.get("to_date")])

	return conditions

#TODO: Use function from frappe once PR #6853 is merged.
def download_zip(files, output_filename):
	from zipfile import ZipFile

	input_files = [frappe.get_site_path('private', 'files', filename) for filename in files]
	output_path = frappe.get_site_path('private', 'files', output_filename)

	with ZipFile(output_path, 'w') as output_zip:
		for input_file in input_files:
			output_zip.write(input_file, arcname=os.path.basename(input_file))

	with open(output_path, 'rb') as fileobj:
		filedata = fileobj.read()

	frappe.local.response.filename = output_filename
	frappe.local.response.filecontent = filedata
	frappe.local.response.type = "download"

def get_invoice_summary(items, taxes):
	summary_data = frappe._dict()
	for tax in taxes:
		#Include only VAT charges.
		if tax.charge_type == "Actual":
			continue

		#Check item tax rates if tax rate is zero.
		if tax.rate == 0:
			for item in items:
				item_tax_rate = json.loads(item.item_tax_rate)
				if tax.account_head in item_tax_rate:
					key = str(item_tax_rate[tax.account_head])
					summary_data.setdefault(key, {"tax_amount": 0.0, "taxable_amount": 0.0, "tax_exemption_reason": "", "tax_exemption_law": ""})
					summary_data[key]["tax_amount"] += item.tax_amount
					summary_data[key]["taxable_amount"] += item.net_amount
					if key == "0.0":
						summary_data[key]["tax_exemption_reason"] = tax.tax_exemption_reason
						summary_data[key]["tax_exemption_law"] = tax.tax_exemption_law

			if summary_data == {}: #Implies that Zero VAT has not been set on any item.
				summary_data.setdefault("0.0", {"tax_amount": 0.0, "taxable_amount": tax.total,
					"tax_exemption_reason": tax.tax_exemption_reason, "tax_exemption_law": tax.tax_exemption_law})

		else:
			item_wise_tax_detail = json.loads(tax.item_wise_tax_detail)
			for rate_item in [tax_item for tax_item in item_wise_tax_detail.items() if tax_item[1][0] == tax.rate]:
				key = str(tax.rate)
				if not summary_data.get(key): summary_data.setdefault(key, {"tax_amount": 0.0, "taxable_amount": 0.0})
				summary_data[key]["tax_amount"] += rate_item[1][1]
				summary_data[key]["taxable_amount"] += sum([item.net_amount for item in items if item.item_code == rate_item[0]])

	return summary_data

#Preflight for successful e-invoice export.
def sales_invoice_validate(doc):
	#Validate company
	if not doc.company_address:
		frappe.throw(_("Please set an Address on the Company '%s'" % doc.company), title=_("E-Invoicing Information Missing"))
	else:
		validate_address(doc.company_address, "Company")

	if not doc.company_tax_id and not doc.company_fiscal_code:
		frappe.throw(_("Please set either the Tax ID or Fiscal Code on Company '%s'" % doc.company), title=_("E-Invoicing Information Missing"))

	#Validate customer details
	customer_type, is_public_administration = frappe.db.get_value("Customer", doc.customer, ["customer_type", "is_public_administration"])
	if customer_type == _("Individual"):
		if not doc.customer_fiscal_code:
			frappe.throw(_("Please set Fiscal Code for the customer '%s'" % doc.customer), title=_("E-Invoicing Information Missing"))
	else:
		if is_public_administration:
			if not doc.customer_fiscal_code:
				frappe.throw(_("Please set Fiscal Code for the public administration '%s'" % doc.customer), title=_("E-Invoicing Information Missing"))
		else:
			if not doc.tax_id:
				frappe.throw(_("Please set Tax ID for the customer '%s'" % doc.customer), title=_("E-Invoicing Information Missing"))

	if not doc.customer_address:
	 	frappe.throw(_("Please set the Customer Address"), title=_("E-Invoicing Information Missing"))
	else:
		validate_address(doc.customer_address, "Customer")

	if not len(doc.taxes):
		frappe.throw(_("Please set at least one row in the Taxes and Charges Table"), title=_("E-Invoicing Information Missing"))
	else:
		for row in doc.taxes:
			if row.rate == 0 and row.tax_amount == 0 and not row.tax_exemption_reason:
				frappe.throw(_("Row {0}: Please set at Tax Exemption Reason in Sales Taxes and Charges".format(row.idx)),
					title=_("E-Invoicing Information Missing"))


#Ensure payment details are valid for e-invoice.
def sales_invoice_on_submit(doc):
	#Validate payment details
	if not len(doc.payment_schedule):
		frappe.throw(_("Please set the Payment Schedule"), title=_("E-Invoicing Information Missing"))
	else:
		for schedule in doc.payment_schedule:
			if not schedule.mode_of_payment:
				frappe.throw(_("Row {0}: Please set the Mode of Payment in Payment Schedule".format(schedule.idx)),
					title=_("E-Invoicing Information Missing"))

	prepare_and_attach_invoice(doc)

def prepare_and_attach_invoice(doc):
	progressive_name, progressive_number = get_progressive_name_and_number(doc)

	invoice = prepare_invoice(doc, progressive_number)
	invoice_xml = frappe.render_template('erpnext/regional/italy/e-invoice.xml', context={"doc": invoice}, is_path=True)

	xml_filename = progressive_name + ".xml"
	save_file(xml_filename, invoice_xml, dt=doc.doctype, dn=doc.name, is_private=True)

#Delete e-invoice attachment on cancel.
def sales_invoice_on_cancel(doc):
	for attachment in get_e_invoice_attachments(doc):
		remove_file(attachment.name, attached_to_doctype=doc.doctype, attached_to_name=doc.name)

def get_e_invoice_attachments(invoice):
	out = []
	attachments = get_attachments(invoice.doctype, invoice.name)
	company_tax_id = invoice.company_tax_id if invoice.company_tax_id.startswith("IT") else "IT" + invoice.company_tax_id

	for attachment in attachments:
		if attachment.file_name.startswith(company_tax_id) and attachment.file_name.endswith(".xml"):
			out.append(attachment)

	return out

def validate_address(address_name, address_context):
	pincode, city = frappe.db.get_value("Address", address_name, ["pincode", "city"])
	if not pincode:
		frappe.throw(_("Please set pin code on %s Address" % address_context), title=_("E-Invoicing Information Missing"))
	if not city:
		frappe.throw(_("Please set city on %s Address" % address_context), title=_("E-Invoicing Information Missing"))


def get_unamended_name(doc):
	attributes = ["naming_series", "amended_from"]
	for attribute in attributes:
		if not hasattr(doc, attribute):
			return doc.name

	if doc.amended_from:
		return "-".join(doc.name.split("-")[:-1])
	else:
		return doc.name

def get_progressive_name_and_number(doc):
	company_tax_id = doc.company_tax_id if doc.company_tax_id.startswith("IT") else "IT" + doc.company_tax_id
	progressive_name = frappe.model.naming.make_autoname(company_tax_id + "_.#####")
	progressive_number = progressive_name.split("_")[1]

	return progressive_name, progressive_number