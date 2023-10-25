# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import re
import zipfile

import dateutil
import frappe
from bs4 import BeautifulSoup as bs
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime_str, today
from frappe.utils.data import format_datetime
from frappe.utils.file_manager import save_file

import erpnext


class ImportSupplierInvoice(Document):
	def validate(self):
		if not frappe.db.get_value("Stock Settings", fieldname="stock_uom"):
			frappe.throw(_("Please set default UOM in Stock Settings"))

	def autoname(self):
		if not self.name:
			self.name = "Import Invoice on " + format_datetime(self.creation)

	def import_xml_data(self):
		zip_file = frappe.get_doc(
			"File",
			{"file_url": self.zip_file, "attached_to_doctype": self.doctype, "attached_to_name": self.name},
		)

		self.publish("File Import", _("Processing XML Files"), 1, 3)

		self.file_count = 0
		self.purchase_invoices_count = 0
		self.default_uom = frappe.db.get_value("Stock Settings", fieldname="stock_uom")

		with zipfile.ZipFile(zip_file.get_full_path()) as zf:
			for file_name in zf.namelist():
				content = get_file_content(file_name, zf)
				file_content = bs(content, "xml")
				self.prepare_data_for_import(file_content, file_name, content)

		if self.purchase_invoices_count == self.file_count:
			self.status = "File Import Completed"
			self.publish("File Import", _("XML Files Processed"), 2, 3)
		else:
			self.status = "Partially Completed - Check Error Log"
			self.publish("File Import", _("XML Files Processed"), 2, 3)

		self.save()
		self.publish("File Import", _("XML Files Processed"), 3, 3)

	def prepare_data_for_import(self, file_content, file_name, encoded_content):
		for line in file_content.find_all("DatiGeneraliDocumento"):
			invoices_args = {
				"company": self.company,
				"naming_series": self.invoice_series,
				"document_type": line.TipoDocumento.text,
				"bill_date": get_datetime_str(line.Data.text),
				"bill_no": line.Numero.text,
				"total_discount": 0,
				"items": [],
				"buying_price_list": self.default_buying_price_list,
			}

			if not invoices_args.get("bill_no", ""):
				frappe.throw(_("Numero has not set in the XML file"))

			supp_dict = get_supplier_details(file_content)
			invoices_args["destination_code"] = get_destination_code_from_file(file_content)
			self.prepare_items_for_invoice(file_content, invoices_args)
			invoices_args["taxes"] = get_taxes_from_file(file_content, self.tax_account)
			invoices_args["terms"] = get_payment_terms_from_file(file_content)

			supplier_name = create_supplier(self.supplier_group, supp_dict)
			address = create_address(supplier_name, supp_dict)
			pi_name = create_purchase_invoice(supplier_name, file_name, invoices_args, self.name)

			self.file_count += 1
			if pi_name:
				self.purchase_invoices_count += 1
				file_save = save_file(
					file_name,
					encoded_content,
					"Purchase Invoice",
					pi_name,
					folder=None,
					decode=False,
					is_private=0,
					df=None,
				)

	def prepare_items_for_invoice(self, file_content, invoices_args):
		qty = 1
		rate, tax_rate = [0, 0]
		uom = self.default_uom

		# read file for item information
		for line in file_content.find_all("DettaglioLinee"):
			if line.find("PrezzoUnitario") and line.find("PrezzoTotale"):
				rate = flt(line.PrezzoUnitario.text) or 0
				line_total = flt(line.PrezzoTotale.text) or 0

				if rate and flt(line_total) / rate != 1.0 and line.find("Quantita"):
					qty = flt(line.Quantita.text) or 0
					if line.find("UnitaMisura"):
						uom = create_uom(line.UnitaMisura.text)

				if rate < 0 and line_total < 0:
					qty *= -1
					invoices_args["return_invoice"] = 1

				if line.find("AliquotaIVA"):
					tax_rate = flt(line.AliquotaIVA.text)

				line_str = re.sub("[^A-Za-z0-9]+", "-", line.Descrizione.text)
				item_name = line_str[0:140]

				invoices_args["items"].append(
					{
						"item_code": self.item_code,
						"item_name": item_name,
						"description": line_str,
						"qty": qty,
						"uom": uom,
						"rate": abs(rate),
						"conversion_factor": 1.0,
						"tax_rate": tax_rate,
					}
				)

				for disc_line in line.find_all("ScontoMaggiorazione"):
					if disc_line.find("Percentuale"):
						invoices_args["total_discount"] += flt(
							(flt(disc_line.Percentuale.text) / 100) * (rate * qty)
						)

	@frappe.whitelist()
	def process_file_data(self):
		self.db_set("status", "Processing File Data", notify=True, commit=True)
		frappe.enqueue_doc(self.doctype, self.name, "import_xml_data", queue="long", timeout=3600)

	def publish(self, title, message, count, total):
		frappe.publish_realtime(
			"import_invoice_update",
			{"title": title, "message": message, "count": count, "total": total},
			user=self.modified_by,
		)


def get_file_content(file_name, zip_file_object):
	content = ""
	encoded_content = zip_file_object.read(file_name)

	try:
		content = encoded_content.decode("utf-8-sig")
	except UnicodeDecodeError:
		try:
			content = encoded_content.decode("utf-16")
		except UnicodeDecodeError as e:
			frappe.log_error("UTF-16 encoding error for File Name: " + file_name)

	return content


def get_supplier_details(file_content):
	supplier_info = {}
	for line in file_content.find_all("CedentePrestatore"):
		supplier_info["tax_id"] = line.DatiAnagrafici.IdPaese.text + line.DatiAnagrafici.IdCodice.text
		if line.find("CodiceFiscale"):
			supplier_info["fiscal_code"] = line.DatiAnagrafici.CodiceFiscale.text

		if line.find("RegimeFiscale"):
			supplier_info["fiscal_regime"] = line.DatiAnagrafici.RegimeFiscale.text

		if line.find("Denominazione"):
			supplier_info["supplier"] = line.DatiAnagrafici.Anagrafica.Denominazione.text

		if line.find("Nome"):
			supplier_info["supplier"] = (
				line.DatiAnagrafici.Anagrafica.Nome.text + " " + line.DatiAnagrafici.Anagrafica.Cognome.text
			)

		supplier_info["address_line1"] = line.Sede.Indirizzo.text
		supplier_info["city"] = line.Sede.Comune.text
		if line.find("Provincia"):
			supplier_info["province"] = line.Sede.Provincia.text

		supplier_info["pin_code"] = line.Sede.CAP.text
		supplier_info["country"] = get_country(line.Sede.Nazione.text)

		return supplier_info


def get_taxes_from_file(file_content, tax_account):
	taxes = []
	# read file for taxes information
	for line in file_content.find_all("DatiRiepilogo"):
		if line.find("AliquotaIVA"):
			if line.find("EsigibilitaIVA"):
				descr = line.EsigibilitaIVA.text
			else:
				descr = "None"
			taxes.append(
				{
					"charge_type": "Actual",
					"account_head": tax_account,
					"tax_rate": flt(line.AliquotaIVA.text) or 0,
					"description": descr,
					"tax_amount": flt(line.Imposta.text) if len(line.find("Imposta")) != 0 else 0,
				}
			)

	return taxes


def get_payment_terms_from_file(file_content):
	terms = []
	# Get mode of payment dict from setup
	mop_options = frappe.get_meta("Mode of Payment").fields[4].options
	mop_str = re.sub("\n", ",", mop_options)
	mop_dict = dict(item.split("-") for item in mop_str.split(","))
	# read file for payment information
	for line in file_content.find_all("DettaglioPagamento"):
		mop_code = line.ModalitaPagamento.text + "-" + mop_dict.get(line.ModalitaPagamento.text)
		if line.find("DataScadenzaPagamento"):
			due_date = dateutil.parser.parse(line.DataScadenzaPagamento.text).strftime("%Y-%m-%d")
		else:
			due_date = today()
		terms.append(
			{
				"mode_of_payment_code": mop_code,
				"bank_account_iban": line.IBAN.text if line.find("IBAN") else "",
				"due_date": due_date,
				"payment_amount": line.ImportoPagamento.text,
			}
		)

	return terms


def get_destination_code_from_file(file_content):
	destination_code = ""
	for line in file_content.find_all("DatiTrasmissione"):
		destination_code = line.CodiceDestinatario.text

	return destination_code


def create_supplier(supplier_group, args):
	args = frappe._dict(args)

	existing_supplier_name = frappe.db.get_value(
		"Supplier", filters={"tax_id": args.tax_id}, fieldname="name"
	)
	if existing_supplier_name:
		pass
	else:
		existing_supplier_name = frappe.db.get_value(
			"Supplier", filters={"name": args.supplier}, fieldname="name"
		)

	if existing_supplier_name:
		filters = [
			["Dynamic Link", "link_doctype", "=", "Supplier"],
			["Dynamic Link", "link_name", "=", args.existing_supplier_name],
			["Dynamic Link", "parenttype", "=", "Contact"],
		]

		if not frappe.get_list("Contact", filters):
			new_contact = frappe.new_doc("Contact")
			new_contact.first_name = args.supplier[:30]
			new_contact.append("links", {"link_doctype": "Supplier", "link_name": existing_supplier_name})
			new_contact.insert(ignore_mandatory=True)

		return existing_supplier_name
	else:

		new_supplier = frappe.new_doc("Supplier")
		new_supplier.supplier_name = re.sub("&amp", "&", args.supplier)
		new_supplier.supplier_group = supplier_group
		new_supplier.tax_id = args.tax_id
		new_supplier.fiscal_code = args.fiscal_code
		new_supplier.fiscal_regime = args.fiscal_regime
		new_supplier.save()

		new_contact = frappe.new_doc("Contact")
		new_contact.first_name = args.supplier[:30]
		new_contact.append("links", {"link_doctype": "Supplier", "link_name": new_supplier.name})

		new_contact.insert(ignore_mandatory=True)

		return new_supplier.name


def create_address(supplier_name, args):
	args = frappe._dict(args)

	filters = [
		["Dynamic Link", "link_doctype", "=", "Supplier"],
		["Dynamic Link", "link_name", "=", supplier_name],
		["Dynamic Link", "parenttype", "=", "Address"],
	]

	existing_address = frappe.get_list("Address", filters)

	if args.address_line1:
		new_address_doc = frappe.new_doc("Address")
		new_address_doc.address_line1 = args.address_line1

		if args.city:
			new_address_doc.city = args.city
		else:
			new_address_doc.city = "Not Provided"

		for field in ["province", "pincode", "country"]:
			if args.get(field):
				new_address_doc.set(field, args.get(field))

		for address in existing_address:
			address_doc = frappe.get_doc("Address", address["name"])
			if (
				address_doc.address_line1 == new_address_doc.address_line1
				and address_doc.pincode == new_address_doc.pincode
			):
				return address

		new_address_doc.append("links", {"link_doctype": "Supplier", "link_name": supplier_name})
		new_address_doc.address_type = "Billing"
		new_address_doc.insert(ignore_mandatory=True)
		return new_address_doc.name
	else:
		return None


def create_purchase_invoice(supplier_name, file_name, args, name):
	args = frappe._dict(args)
	pi = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"company": args.company,
			"currency": erpnext.get_company_currency(args.company),
			"naming_series": args.naming_series,
			"supplier": supplier_name,
			"is_return": args.is_return,
			"posting_date": today(),
			"bill_no": args.bill_no,
			"buying_price_list": args.buying_price_list,
			"bill_date": args.bill_date,
			"destination_code": args.destination_code,
			"document_type": args.document_type,
			"disable_rounded_total": 1,
			"items": args["items"],
			"taxes": args["taxes"],
		}
	)

	try:
		pi.set_missing_values()
		pi.insert(ignore_mandatory=True)

		# if discount exists in file, apply any discount on grand total
		if args.total_discount > 0:
			pi.apply_discount_on = "Grand Total"
			pi.discount_amount = args.total_discount
			pi.save()
		# adjust payment amount to match with grand total calculated
		calc_total = 0
		adj = 0
		for term in args.terms:
			calc_total += flt(term["payment_amount"])
		if flt(calc_total - flt(pi.grand_total)) != 0:
			adj = calc_total - flt(pi.grand_total)
		pi.payment_schedule = []
		for term in args.terms:
			pi.append(
				"payment_schedule",
				{
					"mode_of_payment_code": term["mode_of_payment_code"],
					"bank_account_iban": term["bank_account_iban"],
					"due_date": term["due_date"],
					"payment_amount": flt(term["payment_amount"]) - adj,
				},
			)
			adj = 0
		pi.imported_grand_total = calc_total
		pi.save()
		return pi.name
	except Exception as e:
		frappe.db.set_value("Import Supplier Invoice", name, "status", "Error")
		pi.log_error("Unable to create Puchase Invoice")
		return None


def get_country(code):
	existing_country_name = frappe.db.get_value("Country", filters={"code": code}, fieldname="name")
	if existing_country_name:
		return existing_country_name
	else:
		frappe.throw(_("Country Code in File does not match with country code set up in the system"))


def create_uom(uom):
	existing_uom = frappe.db.get_value("UOM", filters={"uom_name": uom}, fieldname="uom_name")
	if existing_uom:
		return existing_uom
	else:
		new_uom = frappe.new_doc("UOM")
		new_uom.uom_name = uom
		new_uom.save()
		return new_uom.uom_name
