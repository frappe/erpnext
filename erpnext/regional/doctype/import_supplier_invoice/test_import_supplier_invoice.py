# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import io
import zipfile

import frappe
from bs4 import BeautifulSoup
from frappe.tests.utils import FrappeTestCase

from erpnext.regional.doctype.import_supplier_invoice.import_supplier_invoice import (
	get_payment_terms_from_file,
)

test_dependencies = ["Supplier Group", "Item", "Account"]


class TestImportSupplierInvoice(FrappeTestCase):
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

	def import_files(self, files: dict[str, str | bytes]):
		doc = frappe.get_doc(
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
		doc.zip_file = make_zip_attachment(doc, files).file_url
		doc.save()
		doc.import_xml_data()
		return doc

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
