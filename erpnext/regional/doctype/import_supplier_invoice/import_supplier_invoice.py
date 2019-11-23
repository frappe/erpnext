# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

from decimal import Decimal
import json
import re
import traceback
import zipfile
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils.data import format_datetime
from bs4 import BeautifulSoup as bs
from frappe.utils import cint, flt, today, nowdate, add_days, get_files_path
import dateutil
from frappe.utils.file_manager import save_file

class ImportSupplierInvoice(Document):
	def validate(self):
		if not frappe.db.get_value("Stock Settings", fieldname="stock_uom"):
			frappe.throw(_("Please set default UOM in Stock Settings"))

	def autoname(self):
		if not self.name:
			self.name = "Import Invoice on " + format_datetime(self.creation)

	def import_xml_data(self):
		import_file = frappe.get_doc("File", {"file_url": self.zip_file})
		self.publish("File Import", _("Processing XML Files"), 1, 3)

		pi_count = 0
		mop_options = frappe.get_meta('Mode of Payment').fields[4].options
		mop_str = re.sub('\n', ',', mop_options)
		mop_dict = dict(item.split("-") for item in mop_str.split(","))

		default_uom = frappe.db.get_value("Stock Settings", fieldname="stock_uom")

		with zipfile.ZipFile(get_full_path(self.zip_file)) as zf:
			file_count = 0
			for file_name in zf.namelist():
				items = []
				taxes = []
				terms = []
				encoded_content = zf.read(file_name)

				try:
					content = encoded_content.decode("utf-8-sig")
				except UnicodeDecodeError:
					try:
						content = encoded_content.decode("utf-16")
					except UnicodeDecodeError as e:
						frappe.log_error(message=e, title="UTF-16 encoding error for File Name: " + file_name)

				file_content = bs(content, "xml")

				for line in file_content.find_all("DatiTrasmissione"):
					destination_code = line.CodiceDestinatario.text

				#read address information from file
				for line in file_content.find_all("DatiGeneraliDocumento"):
					document_type = line.TipoDocumento.text
					bill_date = dateutil.parser.parse(line.Data.text).strftime("%Y-%m-%d")
					invoice_no = line.Numero.text
					if len(invoice_no) != 0:
						for line in file_content.find_all("CedentePrestatore"):
							tax_id = line.DatiAnagrafici.IdPaese.text + line.DatiAnagrafici.IdCodice.text
							if line.find("CodiceFiscale"):
								fiscal_code = line.DatiAnagrafici.CodiceFiscale.text
							else:
								fiscal_code = ""
							if line.find("RegimeFiscale"):
								fiscal_regime = line.DatiAnagrafici.RegimeFiscale.text
							else:
								fiscal_regime = ""
							if line.find("Denominazione"):
								supplier = line.DatiAnagrafici.Anagrafica.Denominazione.text
							if line.find("Nome"):
								supplier = line.DatiAnagrafici.Anagrafica.Nome.text + " " + line.DatiAnagrafici.Anagrafica.Cognome.text
							address_line1 = line.Sede.Indirizzo.text
							city = line.Sede.Comune.text
							if line.find("Provincia"):
								province = line.Sede.Provincia.text
							else:
								province = ""
							pin_code = line.Sede.CAP.text
							country = get_country(line.Sede.Nazione.text)

						total_discount = 0

						#read item information from file
						for line in file_content.find_all("DettaglioLinee"):
							if line.find("PrezzoUnitario") and line.find("PrezzoTotale"):
								unit_rate = flt(line.PrezzoUnitario.text) or 0
								line_total = flt(line.PrezzoTotale.text) or 0

								if (unit_rate == 0.0):
									qty = 1.0
									uom = default_uom
									rate = tax_rate = 0
								else:
									if (line_total / unit_rate) == 1.0:
										qty = 1.0
										uom = default_uom
									else:
										if line.find("Quantita"):
											qty = flt(line.Quantita.text) or 0
											if line.find("UnitaMisura"):
												uom = create_uom(line.UnitaMisura.text)
											else:
												uom = default_uom

									if (unit_rate < 0 and line_total < 0):
										qty *= -1
										return_invoice = 1
									else:
										return_invoice = 0

									rate = unit_rate
									if line.find("AliquotaIVA"):
										tax_rate = flt(line.AliquotaIVA.text)

								line_str = re.sub('[^A-Za-z0-9]+', '-', line.Descrizione.text)
								item_name = line_str[0:140]
								items.append({
												"item_code": self.item_code,
												"item_name": item_name,
												"description": line_str,
												"qty": qty,
												"uom": uom,
												"rate": rate,
												"conversion_factor": 1.0,
												"tax_rate": tax_rate
											})

								for disc_line in line.find_all("ScontoMaggiorazione"):
									if disc_line.find("Percentuale"):
										discount = flt(disc_line.Percentuale.text) or 0
										total_discount += flt((discount / 100) * (rate * qty))

						#read taxes from file
						for line in file_content.find_all("DatiRiepilogo"):
							if line.find("AliquotaIVA"):
								if line.find("EsigibilitaIVA"):
									descr = line.EsigibilitaIVA.text
								else:
									descr = "None"
								taxes.append({
									"charge_type": "Actual",
									"account_head": self.tax_account,
									"tax_rate": flt(line.AliquotaIVA.text) or 0,
									"description": descr,
									"tax_amount": flt(line.Imposta.text) if len(line.find("Imposta"))!=0 else 0
								})

						#read payment data from file
						for line in file_content.find_all("DettaglioPagamento"):
							mop_code = line.ModalitaPagamento.text + '-' + mop_dict.get(line.ModalitaPagamento.text)
							if line.find("DataScadenzaPagamento"):
								due_date = dateutil.parser.parse(line.DataScadenzaPagamento.text).strftime("%Y-%m-%d")
							else:
								due_date = today()
							terms.append({
											"mode_of_payment_code": mop_code,
											"bank_account_iban": line.IBAN.text if line.find("IBAN") else "",
											"due_date": due_date,
											"payment_amount": line.ImportoPagamento.text
							})

						supplier_name = create_supplier(supplier = supplier, supplier_group = self.supplier_group, 
											tax_id = tax_id, fiscal_code = fiscal_code,
											fiscal_regime = fiscal_regime)

						address = create_address(supplier_name = supplier_name, address_line1 = address_line1, 
									city = city, province = province, 
									pin_code = pin_code, country = country)

						pi_name = create_purchase_invoice(company = self.company, naming_series = self.invoice_series,
									supplier_name = supplier_name, bill_no = invoice_no,document_type = document_type, 
									bill_date = bill_date,is_return = return_invoice, destination_code = destination_code,
									total_discount = total_discount, items = items,taxes = taxes, terms = terms,
									file_name = file_name)

						file_count += 1
						if pi_name:
							pi_count += 1
							file_save = save_file(file_name, encoded_content, "Purchase Invoice", pi_name, folder=None, decode=False, is_private=0, df=None)

		if pi_count == file_count:
			self.status = "File Import Completed"
			self.publish("File Import", _("XML Files Processed"), 2, 3)
		else:
			self.status = "Partially Completed - Check Error Log"
			self.publish("File Import", _("XML Files Processed"), 2, 3)

		self.save()
		self.publish("File Import", _("XML Files Processed"), 3, 3)

	def process_file_data(self):
		self.status = "Processing File Data"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "import_xml_data", queue="long", timeout=3600)

	def publish(self, title, message, count, total):
		frappe.publish_realtime("import_invoice_update", {"title": title, "message": message, "count": count, "total": total})

def create_supplier(**args):
	args = frappe._dict(args)
	existing_supplier_name = frappe.db.get_value("Supplier",
				filters={"tax_id": args.tax_id}, fieldname="name")
	if existing_supplier_name:
		pass
	else:
		existing_supplier_name = frappe.db.get_value("Supplier",
				filters={"name": args.supplier}, fieldname="name")

	if existing_supplier_name:
		filters = [
				["Dynamic Link", "link_doctype", "=", "Supplier"],
				["Dynamic Link", "link_name", "=", args.existing_supplier_name],
				["Dynamic Link", "parenttype", "=", "Contact"]
			]

		existing_contacts = frappe.get_list("Contact", filters)

		if existing_contacts:
			pass
		else:
			new_contact = frappe.new_doc("Contact")
			new_contact.first_name = args.supplier
			new_contact.append('links', {
				"link_doctype": "Supplier",
				"link_name": existing_supplier_name
			})
			new_contact.insert()

		return existing_supplier_name
	else:
		
		new_supplier = frappe.new_doc("Supplier")
		new_supplier.supplier_name = args.supplier
		new_supplier.supplier_group = args.supplier_group
		new_supplier.tax_id = args.tax_id
		new_supplier.fiscal_code = args.fiscal_code
		new_supplier.fiscal_regime = args.fiscal_regime
		new_supplier.save()

		new_contact = frappe.new_doc("Contact")
		new_contact.first_name = args.supplier
		new_contact.append('links', {
			"link_doctype": "Supplier",
			"link_name": new_supplier.name
		})

		new_contact.insert()

		return new_supplier.name

def create_address(**args):
	args = frappe._dict(args)
	filters = [
			["Dynamic Link", "link_doctype", "=", "Supplier"],
			["Dynamic Link", "link_name", "=", args.supplier_name],
			["Dynamic Link", "parenttype", "=", "Address"]
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
			if (address_doc.address_line1 == new_address_doc.address_line1 and
				address_doc.pincode == new_address_doc.pincode):
				return address

		new_address_doc.append("links", {
			"link_doctype": "Supplier",
			"link_name": args.supplier_name
		})
		new_address_doc.address_type = "Billing"
		new_address_doc.insert()
		return new_address_doc.name
	else:
		return None

def create_purchase_invoice(**args):
	args = frappe._dict(args)
	pi = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"company": args.company,
			"naming_series": args.naming_series,
			"supplier": args.supplier_name,
			"is_return": args.is_return,
			"posting_date": today(),
			"bill_no": args.bill_no,
			"bill_date": args.bill_date,
			"destination_code": args.destination_code,
			"document_type": args.document_type,
			"items": args["items"],
			"taxes": args["taxes"]
		})

	try:
		pi.set_missing_values()
		pi.insert(ignore_permissions=True)
		#if discount exists in file, apply any discount on grand total
		if args.total_discount > 0:
			pi.apply_discount_on = "Grand Total"
			pi.discount_amount = args.total_discount
			pi.save()
		#adjust payment amount to match with grand total calculated
		calc_total = 0
		adj = 0
		for term in args.terms:
			calc_total += flt(term["payment_amount"])
		if flt(calc_total - flt(pi.grand_total)) != 0:
			adj = calc_total - flt(pi.grand_total)
		pi.payment_schedule = []
		for term in args.terms:
			pi.append('payment_schedule',{"mode_of_payment_code": term["mode_of_payment_code"],
			"bank_account_iban": term["bank_account_iban"],
			"due_date": term["due_date"],
			"payment_amount": flt(term["payment_amount"]) - adj })
			adj = 0
		pi.imported_grand_total = calc_total
		pi.save()
		return pi.name
	except Exception as e:
		frappe.log_error(message=e, title="Create Purchase Invoice: " + args.bill_no + "File Name: " + args.file_name)
		return None

def get_country(code):
	existing_country_name = frappe.db.get_value("Country",
			filters={"code": code}, fieldname="name")
	if existing_country_name:
		return existing_country_name
	else:
		frappe.throw(_("Country Code in File does not match with country code set up in the system"))

def create_uom(uom):
	existing_uom = frappe.db.get_value("UOM",
			filters={"uom_name": uom}, fieldname="uom_name")
	if existing_uom:
		return existing_uom
	else:
		new_uom = frappe.new_doc("UOM")
		new_uom.uom_name = uom
		new_uom.save()
		return new_uom.uom_name

def get_full_path(file_name):
	"""Returns file path from given file name"""
	file_path = file_name

	if "/" not in file_path:
		file_path = "/files/" + file_path

	if file_path.startswith("/private/files/"):
		file_path = get_files_path(*file_path.split("/private/files/", 1)[1].split("/"), is_private=1)

	elif file_path.startswith("/files/"):
		file_path = get_files_path(*file_path.split("/files/", 1)[1].split("/"))

	elif file_path.startswith("http"):
		pass

	elif not self.file_url:
		frappe.throw(_("There is some problem with the file url: {0}").format(file_path))

	return file_path