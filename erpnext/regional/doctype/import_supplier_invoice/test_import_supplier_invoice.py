# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import io
import zipfile

import frappe
from bs4 import BeautifulSoup

from erpnext.regional.doctype.import_supplier_invoice.import_supplier_invoice import (
	get_country,
	get_payment_terms_from_file,
)
from erpnext.regional.italy.setup import add_permissions
from erpnext.tests.utils import ERPNextTestSuite


class TestImportSupplierInvoice(ERPNextTestSuite):
	"""The importer requires a default stock UOM and resolves country codes from the file."""

	@ERPNextTestSuite.change_settings("Stock Settings", {"stock_uom": ""})
	def test_validate_requires_a_default_uom(self):
		doc = frappe.new_doc("Import Supplier Invoice")
		self.assertRaises(frappe.ValidationError, doc.validate)

	@ERPNextTestSuite.change_settings("Stock Settings", {"stock_uom": "Nos"})
	def test_validate_passes_with_a_default_uom(self):
		frappe.new_doc("Import Supplier Invoice").validate()

	def test_get_country_resolves_a_known_code(self):
		country = frappe.get_all("Country", filters={"code": ["!=", ""]}, fields=["name", "code"], limit=1)[0]
		self.assertEqual(get_country(country.code), country.name)

	def test_get_country_rejects_an_unknown_code(self):
		self.assertRaises(frappe.ValidationError, get_country, "__no_such_country_code__")

	def test_payment_terms_use_the_italian_payment_codes(self):
		xml = make_invoice_xml(
			"ISI-MP", [make_line("Service", "10.00", "10.00")], payments=[("MP05", "12.20")]
		)
		terms = get_payment_terms_from_file(BeautifulSoup(xml, "xml"))
		self.assertEqual(terms[0]["mode_of_payment_code"], "MP05-Bonifico")

	def test_each_line_has_its_own_qty_and_uom(self):
		lines = [
			make_line("Bolts", "10.00", "50.00", qty="5.00", uom="_Test ISI KG"),
			make_line("Service", "20.00", "20.00"),
		]
		self.import_files({"a.xml": make_invoice_xml("ISI-LINES", lines, tax="15.40")})

		invoice = self.get_invoice("ISI-LINES")
		self.assertEqual([(row.qty, row.uom) for row in invoice.items], [(5, "_Test ISI KG"), (1, "Nos")])
		self.assertEqual((invoice.net_total, invoice.grand_total), (70, 85.40))

	def test_bad_files_are_logged_and_the_rest_imported(self):
		service = [make_line("Service", "10.00", "10.00")]
		doc = self.import_files(
			{
				"1.xml": make_invoice_xml("ISI-NO-TAX", service, tax=None),
				"2.xml": make_invoice_xml("ISI-MP99", service, tax="2.20", payments=[("MP99", "12.20")]),
				"3.xml": make_invoice_xml("ISI-XX", service, country="XX"),
			}
		)

		self.assertEqual(doc.status, "Partially Completed - Check Error Log")
		self.assertEqual(self.get_invoice("ISI-NO-TAX").grand_total, 10)
		self.assertEqual(self.get_invoice("ISI-MP99").grand_total, 12.20)
		self.assertFalse(frappe.db.exists("Purchase Invoice", {"bill_no": "ISI-XX"}))

	def test_credit_notes_are_imported_as_returns(self):
		negative = [make_line("Return one", "-50.00", "-50.00"), make_line("Return two", "-30.00", "-30.00")]
		positive = [make_line("Return one", "50.00", "50.00"), make_line("Return two", "30.00", "30.00")]
		self.import_files(
			{
				"c1.xml": make_invoice_xml("ISI-CN-NEG", negative, tax="-17.60", document_type="TD04"),
				"c2.xml": make_invoice_xml("ISI-CN-POS", positive, tax="17.60", document_type="TD04"),
			}
		)

		for bill_no in ("ISI-CN-NEG", "ISI-CN-POS"):
			invoice = self.get_invoice(bill_no)
			self.assertEqual(invoice.is_return, 1)
			self.assertEqual([row.qty for row in invoice.items], [-1, -1])
			self.assertEqual(invoice.grand_total, -97.60)

	def test_line_surcharges_and_amount_discounts(self):
		surcharge = (
			"<ScontoMaggiorazione><Tipo>MG</Tipo><Percentuale>10.00</Percentuale></ScontoMaggiorazione>"
		)
		discount = "<ScontoMaggiorazione><Tipo>SC</Tipo><Importo>5.00</Importo></ScontoMaggiorazione>"
		lines = [
			make_line("Widget", "100.00", "110.00", qty="1.00", discounts=surcharge),
			make_line("Gadget", "50.00", "90.00", qty="2.00", discounts=discount),
		]
		self.import_files({"d.xml": make_invoice_xml("ISI-DISC", lines, tax="44.00")})

		invoice = self.get_invoice("ISI-DISC")
		self.assertEqual([row.amount for row in invoice.items], [110, 90])
		self.assertEqual((invoice.net_total, invoice.grand_total), (200, 244))

	def test_reimporting_a_file_does_not_duplicate_the_supplier_masters(self):
		lines = [make_line("Service", "10.00", "10.00")]
		xml = make_invoice_xml("ISI-AGAIN", lines)
		self.import_files({"a.xml": xml})
		doc = self.import_files({"a.xml": xml, "b.xml": make_invoice_xml("ISI-NEXT", lines)})

		self.assertEqual(doc.status, "Partially Completed - Check Error Log")
		self.assertEqual(frappe.db.count("Purchase Invoice", {"bill_no": "ISI-AGAIN"}), 1)
		supplier = self.get_invoice("ISI-AGAIN").supplier
		contact_links = {"link_doctype": "Supplier", "link_name": supplier, "parenttype": "Contact"}
		self.assertEqual(frappe.db.count("Dynamic Link", contact_links), 1)
		address = frappe.db.get_value(
			"Dynamic Link",
			{"link_doctype": "Supplier", "link_name": supplier, "parenttype": "Address"},
			"parent",
		)
		self.assertEqual(frappe.db.get_value("Address", address, "pincode"), "00185")

	def test_seller_is_matched_by_vat_number_not_by_name(self):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "_Test ISI Namesake",
				"supplier_group": "_Test Supplier Group",
				"tax_id": "IT99999999999",
			}
		).insert()
		xml = make_invoice_xml(
			"ISI-NAMESAKE", [make_line("Service", "10.00", "10.00")], supplier="_Test ISI Namesake"
		)
		self.import_files({"a.xml": xml})

		supplier = self.get_invoice("ISI-NAMESAKE").supplier
		self.assertNotEqual(supplier, "_Test ISI Namesake")
		self.assertEqual(frappe.db.get_value("Supplier", supplier, "tax_id"), "IT01234567890")

	def test_accounts_user_can_import_a_file_from_a_new_supplier(self):
		add_permissions()
		self.addCleanup(frappe.clear_cache, doctype="Import Supplier Invoice")
		frappe.clear_cache(doctype="Import Supplier Invoice")
		user = frappe.get_doc(
			{"doctype": "User", "email": "isi-accounts-user@example.com", "first_name": "ISI"}
		).insert()
		user.add_roles("Accounts User")

		lines = [make_line("Bolts", "10.00", "50.00", qty="5.00", uom="_Test ISI Box")]
		xml = make_invoice_xml("ISI-ACC-USER", lines, supplier="_Test ISI New Seller", vat_code="11111111111")
		with self.set_user(user.name):
			doc = self.import_files({"a.xml": xml})

		self.assertEqual(doc.status, "File Import Completed")
		self.assertEqual(self.get_invoice("ISI-ACC-USER").supplier, "_Test ISI New Seller")

	def test_imports_created_in_the_same_second_get_unique_names(self):
		first = self.make_import()
		second = frappe.new_doc("Import Supplier Invoice")
		second.creation = first.creation
		second.autoname()

		self.assertNotEqual(second.name, first.name)

	def import_files(self, files: dict[str, str | bytes]):
		doc = self.make_import()
		doc.zip_file = make_zip_attachment(doc, files).file_url
		doc.save()
		doc.import_xml_data()
		return doc

	def make_import(self):
		return frappe.get_doc(
			{
				"doctype": "Import Supplier Invoice",
				"company": "_Test Company",
				"item_code": "_Test Non Stock Item",
				"supplier_group": "_Test Supplier Group",
				"tax_account": "_Test Account VAT - _TC",
				"invoice_series": "ACC-PINV-.YYYY.-",
				"default_buying_price_list": "Standard Buying",
			}
		).insert()

	def get_invoice(self, bill_no: str):
		return frappe.get_doc("Purchase Invoice", {"bill_no": bill_no})


def make_zip_attachment(doc, files: dict[str, str | bytes]):
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w") as zip_file:
		for name, content in files.items():
			zip_file.writestr(name, content)

	return frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{frappe.generate_hash(length=8)}.zip",
			"content": buffer.getvalue(),
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"is_private": 1,
		}
	).insert()


def make_line(
	description: str,
	rate: str,
	total: str,
	qty: str | None = None,
	uom: str | None = None,
	discounts: str = "",
) -> str:
	quantity = f"<Quantita>{qty}</Quantita>" if qty else ""
	unit = f"<UnitaMisura>{uom}</UnitaMisura>" if uom else ""
	return (
		f"<DettaglioLinee><Descrizione>{description}</Descrizione>{quantity}{unit}"
		f"<PrezzoUnitario>{rate}</PrezzoUnitario>{discounts}<PrezzoTotale>{total}</PrezzoTotale>"
		"<AliquotaIVA>22.00</AliquotaIVA></DettaglioLinee>"
	)


def make_invoice_xml(
	number: str,
	lines: list[str],
	tax: str | None = "0.00",
	payments: tuple[tuple[str, str], ...] | list = (),
	supplier: str = "_Test ISI Fornitore",
	vat_code: str = "01234567890",
	document_type: str = "TD01",
	country: str = "IT",
) -> str:
	imposta = f"<Imposta>{tax}</Imposta>" if tax is not None else ""
	payment_xml = "".join(
		f"<DettaglioPagamento><ModalitaPagamento>{code}</ModalitaPagamento>"
		f"<ImportoPagamento>{amount}</ImportoPagamento></DettaglioPagamento>"
		for code, amount in payments
	)
	return f"""<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
<FatturaElettronicaHeader>
<DatiTrasmissione><CodiceDestinatario>0000000</CodiceDestinatario></DatiTrasmissione>
<CedentePrestatore><DatiAnagrafici><IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>{vat_code}</IdCodice></IdFiscaleIVA>
<Anagrafica><Denominazione>{supplier}</Denominazione></Anagrafica><RegimeFiscale>RF01</RegimeFiscale></DatiAnagrafici>
<Sede><Indirizzo>Via Roma 1</Indirizzo><CAP>00185</CAP><Comune>Roma</Comune><Nazione>{country}</Nazione></Sede>
</CedentePrestatore></FatturaElettronicaHeader>
<FatturaElettronicaBody><DatiGenerali><DatiGeneraliDocumento><TipoDocumento>{document_type}</TipoDocumento>
<Data>2026-09-30</Data><Numero>{number}</Numero></DatiGeneraliDocumento></DatiGenerali>
<DatiBeniServizi>{"".join(lines)}<DatiRiepilogo><AliquotaIVA>22.00</AliquotaIVA>{imposta}</DatiRiepilogo></DatiBeniServizi>
<DatiPagamento>{payment_xml}</DatiPagamento>
</FatturaElettronicaBody></p:FatturaElettronica>"""
