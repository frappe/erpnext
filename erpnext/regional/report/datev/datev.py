# coding: utf-8
"""
Provide a report and downloadable CSV according to the German DATEV format.

- Query report showing only the columns that contain data, formatted nicely for
  dispay to the user.
- CSV download functionality `download_datev_csv` that provides a CSV file with
  all required columns. Used to import the data into the DATEV Software.
"""
from __future__ import unicode_literals
import json
from six import string_types
import frappe
from frappe import _
import pandas as pd


def execute(filters=None):
	"""Entry point for frappe."""
	validate_filters(filters)
	result = get_gl_entries(filters, as_dict=0)
	columns = get_columns()

	return columns, result


def validate_filters(filters):
	"""Make sure all mandatory filters are present."""
	if not filters.get('company'):
		frappe.throw(_('{0} is mandatory').format(_('Company')))

	if not filters.get('from_date'):
		frappe.throw(_('{0} is mandatory').format(_('From Date')))

	if not filters.get('to_date'):
		frappe.throw(_('{0} is mandatory').format(_('To Date')))


def get_columns():
	"""Return the list of columns that will be shown in query report."""
	columns = [
		{
			"label": "Umsatz (ohne Soll/Haben-Kz)",
			"fieldname": "Umsatz (ohne Soll/Haben-Kz)",
			"fieldtype": "Currency",
		},
		{
			"label": "Soll/Haben-Kennzeichen",
			"fieldname": "Soll/Haben-Kennzeichen",
			"fieldtype": "Data",
		},
		{
			"label": "Kontonummer",
			"fieldname": "Kontonummer",
			"fieldtype": "Data",
		},
		{
			"label": "Gegenkonto (ohne BU-Schlüssel)",
			"fieldname": "Gegenkonto (ohne BU-Schlüssel)",
			"fieldtype": "Data",
		},
		{
			"label": "Belegdatum",
			"fieldname": "Belegdatum",
			"fieldtype": "Date",
		},
		{
			"label": "Buchungstext",
			"fieldname": "Buchungstext",
			"fieldtype": "Text",
		},
		{
			"label": "Beleginfo - Art 1",
			"fieldname": "Beleginfo - Art 1",
			"fieldtype": "Data",
		},
		{
			"label": "Beleginfo - Inhalt 1",
			"fieldname": "Beleginfo - Inhalt 1",
			"fieldtype": "Data",
		},
		{
			"label": "Beleginfo - Art 2",
			"fieldname": "Beleginfo - Art 2",
			"fieldtype": "Data",
		},
		{
			"label": "Beleginfo - Inhalt 2",
			"fieldname": "Beleginfo - Inhalt 2",
			"fieldtype": "Data",
		}
	]

	return columns


def get_gl_entries(filters, as_dict):
	"""
	Get a list of accounting entries.

	Select GL Entries joined with Account and Party Account in order to get the
	account numbers. Returns a list of accounting entries.

	Arguments:
	filters -- dict of filters to be passed to the sql query
	as_dict -- return as list of dicts [0,1]
	"""
	gl_entries = frappe.db.sql("""
		select

			/* either debit or credit amount; always positive */
			case gl.debit when 0 then gl.credit else gl.debit end as 'Umsatz (ohne Soll/Haben-Kz)',

			/* 'H' when credit, 'S' when debit */
			case gl.debit when 0 then 'H' else 'S' end as 'Soll/Haben-Kennzeichen',

			/* account number or, if empty, party account number */
			coalesce(acc.account_number, acc_pa.account_number) as 'Kontonummer',

			/* against number or, if empty, party against number */
			coalesce(acc_against.account_number, acc_against_pa.account_number) as 'Gegenkonto (ohne BU-Schlüssel)',
			
			gl.posting_date as 'Belegdatum',
			gl.remarks as 'Buchungstext',
			gl.voucher_type as 'Beleginfo - Art 1',
			gl.voucher_no as 'Beleginfo - Inhalt 1',
			gl.against_voucher_type as 'Beleginfo - Art 2',
			gl.against_voucher as 'Beleginfo - Inhalt 2'

		from `tabGL Entry` gl

			/* Statistisches Konto (Debitoren/Kreditoren) */
			left join `tabParty Account` pa
			on gl.against = pa.parent
			and gl.company = pa.company

			/* Kontonummer */
			left join `tabAccount` acc 
			on gl.account = acc.name

			/* Gegenkonto-Nummer */
			left join `tabAccount` acc_against 
			on gl.against = acc_against.name

			/* Statistische Kontonummer */
			left join `tabAccount` acc_pa
			on pa.account = acc_pa.name

			/* Statistische Gegenkonto-Nummer */
			left join `tabAccount` acc_against_pa 
			on pa.account = acc_against_pa.name

		where gl.company = %(company)s 
		and DATE(gl.posting_date) >= %(from_date)s
		and DATE(gl.posting_date) <= %(to_date)s
		order by 'Belegdatum', gl.voucher_no""", filters, as_dict=as_dict)

	return gl_entries


def get_datev_csv(data):
	"""
	Fill in missing columns and return a CSV in DATEV Format.

	Arguments:
	data -- array of dictionaries
	"""
	columns = [
		# All possible columns must tbe listed here, because DATEV requires them to
		# be present in the CSV.
		# ---
		# Umsatz
		"Umsatz (ohne Soll/Haben-Kz)",
		"Soll/Haben-Kennzeichen",
		"WKZ Umsatz",
		"Kurs",
		"Basis-Umsatz",
		"WKZ Basis-Umsatz",
		# Konto/Gegenkonto
		"Kontonummer",
		"Gegenkonto (ohne BU-Schlüssel)",
		"BU-Schlüssel",
		# Datum
		"Belegdatum",
		# Belegfelder
		"Belegfeld 1",
		"Belegfeld 2",
		# Weitere Felder
		"Skonto",
		"Buchungstext",
		# OPOS-Informationen
		"Postensperre",
		"Diverse Adressnummer",
		"Geschäftspartnerbank",
		"Sachverhalt",
		"Zinssperre",
		# Digitaler Beleg
		"Beleglink",
		# Beleginfo
		"Beleginfo - Art 1",
		"Beleginfo - Inhalt 1",
		"Beleginfo - Art 2",
		"Beleginfo - Inhalt 2",
		"Beleginfo - Art 3",
		"Beleginfo - Inhalt 3",
		"Beleginfo - Art 4",
		"Beleginfo - Inhalt 4",
		"Beleginfo - Art 5",
		"Beleginfo - Inhalt 5",
		"Beleginfo - Art 6",
		"Beleginfo - Inhalt 6",
		"Beleginfo - Art 7",
		"Beleginfo - Inhalt 7",
		"Beleginfo - Art 8",
		"Beleginfo - Inhalt 8",
		# Kostenrechnung
		"Kost 1 - Kostenstelle",
		"Kost 2 - Kostenstelle",
		"Kost-Menge",
		# Steuerrechnung
		"EU-Land u. UStID",
		"EU-Steuersatz",
		"Abw. Versteuerungsart",
		# L+L Sachverhalt
		"Sachverhalt L+L",
		"Funktionsergänzung L+L",
		# Funktion Steuerschlüssel 49
		"BU 49 Hauptfunktionstyp",
		"BU 49 Hauptfunktionsnummer",
		"BU 49 Funktionsergänzung",
		# Zusatzinformationen
		"Zusatzinformation - Art 1",
		"Zusatzinformation - Inhalt 1",
		"Zusatzinformation - Art 2",
		"Zusatzinformation - Inhalt 2",
		"Zusatzinformation - Art 3",
		"Zusatzinformation - Inhalt 3",
		"Zusatzinformation - Art 4",
		"Zusatzinformation - Inhalt 4",
		"Zusatzinformation - Art 5",
		"Zusatzinformation - Inhalt 5",
		"Zusatzinformation - Art 6",
		"Zusatzinformation - Inhalt 6",
		"Zusatzinformation - Art 7",
		"Zusatzinformation - Inhalt 7",
		"Zusatzinformation - Art 8",
		"Zusatzinformation - Inhalt 8",
		"Zusatzinformation - Art 9",
		"Zusatzinformation - Inhalt 9",
		"Zusatzinformation - Art 10",
		"Zusatzinformation - Inhalt 10",
		"Zusatzinformation - Art 11",
		"Zusatzinformation - Inhalt 11",
		"Zusatzinformation - Art 12",
		"Zusatzinformation - Inhalt 12",
		"Zusatzinformation - Art 13",
		"Zusatzinformation - Inhalt 13",
		"Zusatzinformation - Art 14",
		"Zusatzinformation - Inhalt 14",
		"Zusatzinformation - Art 15",
		"Zusatzinformation - Inhalt 15",
		"Zusatzinformation - Art 16",
		"Zusatzinformation - Inhalt 16",
		"Zusatzinformation - Art 17",
		"Zusatzinformation - Inhalt 17",
		"Zusatzinformation - Art 18",
		"Zusatzinformation - Inhalt 18",
		"Zusatzinformation - Art 19",
		"Zusatzinformation - Inhalt 19",
		"Zusatzinformation - Art 20",
		"Zusatzinformation - Inhalt 20",
		# Mengenfelder LuF
		"Stück",
		"Gewicht",
		# Forderungsart
		"Zahlweise",
		"Forderungsart",
		"Veranlagungsjahr",
		"Zugeordnete Fälligkeit",
		# Weitere Felder
		"Skontotyp",
		# Anzahlungen
		"Auftragsnummer",
		"Buchungstyp",
		"USt-Schlüssel (Anzahlungen)",
		"EU-Land (Anzahlungen)",
		"Sachverhalt L+L (Anzahlungen)",
		"EU-Steuersatz (Anzahlungen)",
		"Erlöskonto (Anzahlungen)",
		# Stapelinformationen
		"Herkunft-Kz",
		# Technische Identifikation
		"Buchungs GUID",
		# Kostenrechnung
		"Kost-Datum",
		# OPOS-Informationen
		"SEPA-Mandatsreferenz",
		"Skontosperre",
		# Gesellschafter und Sonderbilanzsachverhalt
		"Gesellschaftername",
		"Beteiligtennummer",
		"Identifikationsnummer",
		"Zeichnernummer",
		# OPOS-Informationen
		"Postensperre bis",
		# Gesellschafter und Sonderbilanzsachverhalt
		"Bezeichnung SoBil-Sachverhalt",
		"Kennzeichen SoBil-Buchung",
		# Stapelinformationen
		"Festschreibung",
		# Datum
		"Leistungsdatum",
		"Datum Zuord. Steuerperiode",
		# OPOS-Informationen
		"Fälligkeit",
		# Konto/Gegenkonto
		"Generalumkehr (GU)",
		# Steuersatz für Steuerschlüssel
		"Steuersatz",
		"Land"
	]

	empty_df = pd.DataFrame(columns=columns)
	data_df = pd.DataFrame.from_records(data)

	result = empty_df.append(data_df)
	result["Belegdatum"] = pd.to_datetime(result["Belegdatum"])

	return result.to_csv(
		sep=b';',
		# European decimal seperator
		decimal=',',
		# Windows "ANSI" encoding
		encoding='latin_1',
		# format date as DDMM
		date_format='%d%m',
		# Windows line terminator
		line_terminator=b'\r\n',
		# Do not number rows
		index=False,
		# Use all columns defined above
		columns=columns
	)


@frappe.whitelist()
def download_datev_csv(filters=None):
	"""
	Provide accounting entries for download in DATEV format.

	Validate the filters, get the data, produce the CSV file and provide it for
	download. Can be called like this:

	GET /api/method/erpnext.regional.report.datev.datev.download_datev_csv

	Arguments / Params:
	filters -- dict of filters to be passed to the sql query
	"""
	if isinstance(filters, string_types):
		filters = json.loads(filters)

	validate_filters(filters)
	data = get_gl_entries(filters, as_dict=1)

	filename = 'DATEV_Buchungsstapel_{}-{}_bis_{}'.format(
		filters.get('company'),
		filters.get('from_date'),
		filters.get('to_date')
	)

	frappe.response['result'] = get_datev_csv(data)
	frappe.response['doctype'] = filename
	frappe.response['type'] = 'csv'
