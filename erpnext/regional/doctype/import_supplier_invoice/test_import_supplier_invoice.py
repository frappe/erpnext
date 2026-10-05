# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from bs4 import BeautifulSoup
from frappe.tests.utils import FrappeTestCase

from erpnext.regional.doctype.import_supplier_invoice.import_supplier_invoice import (
	get_payment_terms_from_file,
)


class TestImportSupplierInvoice(FrappeTestCase):
	def test_payment_terms_use_the_italian_payment_codes(self):
		xml = make_invoice_xml(
			"ISI-MP", [make_line("Service", "10.00", "10.00")], payments=[("MP05", "12.20")]
		)
		terms = get_payment_terms_from_file(BeautifulSoup(xml, "xml"))
		self.assertEqual(terms[0]["mode_of_payment_code"], "MP05-Bonifico")


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
