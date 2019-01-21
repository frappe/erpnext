import frappe, json, os
from frappe.utils import flt
from erpnext.controllers.taxes_and_totals import get_itemised_tax
from frappe.contacts.doctype.address.address import get_default_address, get_company_address

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
	
def get_rate_wise_tax_data(items):
	tax_data = {}
	for rate in set([item.item_tax_rate for item in items]):
		for key, value in json.loads(rate).items():
			tax_data.setdefault(key, {
				"tax_rate": value,
				"taxable_amount": sum([item.net_amount for item in items if item.item_tax_rate == rate]),
				"tax_amount": sum([item.tax_amount for item in items if item.item_tax_rate == rate]),
				"tax_exemption_reason": frappe.db.get_value("Account", key, "tax_exemption_reason")
			})
	return tax_data

@frappe.whitelist()
def export_invoices(filters=None):
	saved_xmls = []
	invoices = frappe.get_all("Sales Invoice", filters=get_conditions(filters), fields=["*"])
	for invoice in invoices:
		invoice = prepare_invoice(invoice)
		invoice_xml = frappe.render_template('erpnext/regional/italy/e-invoice.xml', context={"doc": invoice}, is_path=True)

		xml_filename = "{company_tax_id}_{invoice_number}.xml".format(
			company_tax_id=invoice["company_tax_id"],
			invoice_number=extract_doc_number(invoice)
		)
		xml_filename = frappe.get_site_path("private", "files", xml_filename)
		
		with open(xml_filename, "wb") as xml_file:
			xml_file.write(invoice_xml)
			saved_xmls.append(xml_filename)

	zip_filename = "e-invoices_{0}.zip".format(frappe.generate_hash(length=6))
	
	download_zip(saved_xmls, zip_filename)
	
	cleanup_files(saved_xmls)

@frappe.whitelist()
def prepare_invoice(invoice):
	#set company information
	company_fiscal_code, fiscal_regime, company_tax_id = frappe.db.get_value("Company", invoice.company, ["fiscal_code", "fiscal_regime", "tax_id"])
	invoice["progressive_number"] = extract_doc_number(invoice)
	invoice["company_fiscal_code"] = company_fiscal_code
	invoice["fiscal_regime"] = fiscal_regime
	invoice["company_tax_id"] = company_tax_id
	invoice["company_address_data"] = frappe.get_doc("Address", invoice.company_address)
	invoice["company_contact_data"] = frappe.db.get_value("Company", filters=invoice.company, fieldname=["phone_no", "email"], as_dict=1)

	#Set invoice type
	if invoice.is_return and invoice.return_against:
		invoice["type_of_document"] = "TD04" #Credit Note (Nota di Credito)
	else:
		invoice["type_of_document"] = "TD01" #Sales Invoice (Fattura)
	
	#set customer information
	invoice["customer_data"] = frappe.get_doc("Customer", invoice.customer)
	invoice["customer_address_data"] = frappe.get_doc("Address", invoice.customer_address)

	if invoice.shipping_address_name:
		invoice["shipping_address_data"] = frappe.get_doc("Address", invoice.shipping_address_name)

	if not invoice["vat_collectability"]:
		invoice["vat_collectability"] = frappe.db.get_value("Company", invoice.company, "vat_collectability")

	if invoice["customer_data"].is_public_administration:
		invoice["transmission_format_code"] = "FPA12"
	else:
		invoice["transmission_format_code"] = "FPR12"
	
	#append items, and tax exemption reason.
	items = frappe.get_all("Sales Invoice Item", filters={"parent":invoice.name}, fields=["*"], order_by="idx")
	for item in items:
		item_tax_rate = json.loads(item.item_tax_rate)
		for account in item_tax_rate.keys():
			item["tax_exemption_reason"] = frappe.db.get_value("Account", account, "tax_exemption_reason")

	invoice["invoice_items"] = items

	#tax rate wise grouping of tax amount and taxable amount.
	invoice["tax_data"] = get_rate_wise_tax_data(invoice["invoice_items"])

	invoice["payment_terms"] = frappe.get_all("Payment Schedule", filters={"parent": invoice.name}, fields=["*"])

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

def download_zip(files, output_filename):
	from zipfile import ZipFile

	input_files = [filename for filename in files]
	output_path = frappe.get_site_path('private', 'files', output_filename)
	
	with ZipFile(output_path, 'w') as output_zip:
		for input_file in input_files:
			output_zip.write(input_file, arcname=os.path.basename(input_file))

	with open(output_path, 'rb') as fileobj:
		filedata = fileobj.read()

	frappe.local.response.filename = output_filename
	frappe.local.response.filecontent = filedata
	frappe.local.response.type = "download"

def cleanup_files(files):
	#TODO: Clean up XML files after ZIP gets downloaded
	pass

def extract_doc_number(doc):
	if not hasattr(doc, "naming_series"):
		return doc.name
	
	name_parts = doc.name.split("-")

	if hasattr(doc, "amended_from"):
		if doc.amended_from:
			return name_parts[-2:-1][0]
		else:
			return name_parts[-1:][0]
	else:
		return doc.name
