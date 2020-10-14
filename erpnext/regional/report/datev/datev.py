# coding: utf-8
"""
Provide a report and downloadable CSV according to the German DATEV format.

- Query report showing only the columns that contain data, formatted nicely for
  dispay to the user.
- CSV download functionality `download_datev_csv` that provides a CSV file with
  all required columns. Used to import the data into the DATEV Software.
"""
from __future__ import unicode_literals
import datetime
import json
import six
from six import string_types
from csv import QUOTE_NONNUMERIC

import frappe
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
import pandas as pd


def execute(filters=None):
	"""Entry point for frappe."""
	validate(filters)
	result = get_gl_entries(filters, as_dict=0)
	columns = get_columns()

	return columns, result


def validate(filters):
	"""Make sure all mandatory filters and settings are present."""
	company = filters.get('company')
	if not company:
		frappe.throw(_('<b>Company</b> is a mandatory filter.'))

	from_date = filters.get('from_date')
	if not from_date:
		frappe.throw(_('<b>From Date</b> is a mandatory filter.'))

	to_date = filters.get('to_date')
	if not to_date:
		frappe.throw(_('<b>To Date</b> is a mandatory filter.'))

	validate_fiscal_year(from_date, to_date, company)

	try:
		frappe.get_doc('DATEV Settings', filters.get('company'))
	except frappe.DoesNotExistError:
		frappe.throw(_('Please create <b>DATEV Settings</b> for Company <b>{}</b>.').format(filters.get('company')))


def validate_fiscal_year(from_date, to_date, company):
	from_fiscal_year = get_fiscal_year(date=from_date, company=company)
	to_fiscal_year = get_fiscal_year(date=to_date, company=company)
	if from_fiscal_year != to_fiscal_year:
		frappe.throw(_('Dates {} and {} are not in the same fiscal year.').format(from_date, to_date))


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
			"label": "Konto",
			"fieldname": "Konto",
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
			"label": "Belegfeld 1",
			"fieldname": "Belegfeld 1",
			"fieldtype": "Data",
		},
		{
			"label": "Buchungstext",
			"fieldname": "Buchungstext",
			"fieldtype": "Text",
		},
		{
			"label": "Beleginfo - Art 1",
			"fieldname": "Beleginfo - Art 1",
			"fieldtype": "Link",
			"options": "DocType"
		},
		{
			"label": "Beleginfo - Inhalt 1",
			"fieldname": "Beleginfo - Inhalt 1",
			"fieldtype": "Dynamic Link",
			"options": "Beleginfo - Art 1"
		},
		{
			"label": "Beleginfo - Art 2",
			"fieldname": "Beleginfo - Art 2",
			"fieldtype": "Link",
			"options": "DocType"
		},
		{
			"label": "Beleginfo - Inhalt 2",
			"fieldname": "Beleginfo - Inhalt 2",
			"fieldtype": "Dynamic Link",
			"options": "Beleginfo - Art 2"
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
			coalesce(acc.account_number, acc_pa.account_number) as 'Konto',

			/* against number or, if empty, party against number */
			coalesce(acc_against.account_number, acc_against_pa.account_number) as 'Gegenkonto (ohne BU-Schlüssel)',
			
			gl.posting_date as 'Belegdatum',
			gl.voucher_no as 'Belegfeld 1',
			LEFT(gl.remarks, 60) as 'Buchungstext',
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


def get_datev_csv(data, filters):
	"""
	Fill in missing columns and return a CSV in DATEV Format.

	For automatic processing, DATEV requires the first line of the CSV file to
	hold meta data such as the length of account numbers oder the category of
	the data.

	Arguments:
	data -- array of dictionaries
	filters -- dict
	"""
	coa = frappe.get_value("Company", filters.get("company"), "chart_of_accounts")
	coa_used = "04" if "SKR04" in coa else ("03" if "SKR03" in coa else "")

	header = [
		# A = DATEV-Format-KZ
		#   DTVF = created by DATEV software,
		#   EXTF = created by other software
		'"EXTF"',
		# B = version of the DATEV format
		#   141 = 1.41, 
		#   510 = 5.10,
		#   720 = 7.20
		"700",
		# C = Data category
		#   21 = Transaction batch (Buchungsstapel),
		#   67 = Buchungstextkonstanten,
		#   16 = Debitors/Creditors,
		#   20 = Account names (Kontenbeschriftungen)
		"21",
		# D = Format name
		#   Buchungsstapel,
		#   Buchungstextkonstanten,
		#   Debitoren/Kreditoren,
		#   Kontenbeschriftungen
		"Buchungsstapel",
		# E = Format version (regarding format name)
		"9",
		# F = Generated on
		datetime.datetime.now().strftime("%Y%m%d%H%M%S") + '000',
		# G = Imported on -- stays empty
		"",
		# H = Herkunfts-Kennzeichen (Origin)
		# Any two letters
		'"EN"',
		# I = Exported by
		'"%s"' % frappe.session.user,
		# J = Imported by -- stays empty
		"",
		# K = Tax consultant number (Beraternummer)
		frappe.get_value("DATEV Settings", filters.get("company"), "consultant_number") or "",
		# L = Tax client number (Mandantennummer)
		frappe.get_value("DATEV Settings", filters.get("company"), "client_number") or "",
		# M = Start of the fiscal year (Wirtschaftsjahresbeginn)
		frappe.utils.formatdate(filters.get("fiscal_year_start"), "yyyyMMdd"),
		# N = Length of account numbers (Sachkontenlänge)
		str(filters.get('account_number_length', 4)),
		# O = Transaction batch start date (YYYYMMDD)
		frappe.utils.formatdate(filters.get('from_date'), "yyyyMMdd"),
		# P = Transaction batch end date (YYYYMMDD)
		frappe.utils.formatdate(filters.get('to_date'), "yyyyMMdd"),
		# Q = Description (for example, "January - February 2019 Transactions")
		"Buchungsstapel",
		# R = Diktatkürzel
		"",
		# S = Buchungstyp
		#   1 = Transaction batch (Buchungsstapel),
		#   2 = Annual financial statement (Jahresabschluss)
		"1",
		# T = Rechnungslegungszweck
		"0", # vom Rechnungslegungszweck unabhängig
		# U = Festschreibung
		"0", # keine Festschreibung
		# V = Kontoführungs-Währungskennzeichen des Geldkontos
		frappe.get_value("Company", filters.get("company"), "default_currency"),
		# reserviert
		'',
		# Derivatskennzeichen
		'',
		# reserviert
		'',
		# reserviert
		'',
		# SKR
		'"%s"' % coa_used,
		# Branchen-Lösungs-ID
		'',
		# reserviert
		'',
		# reserviert
		'',
		# Anwendungsinformation (Verarbeitungskennzeichen der abgebenden Anwendung)
		''
	]
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
		"Konto",
		"Gegenkonto (ohne BU-Schlüssel)",
		"BU-Schlüssel",
		# Datum
		"Belegdatum",
		# Rechnungs- / Belegnummer
		"Belegfeld 1",
		# z.B. Fälligkeitsdatum Format: TTMMJJ
		"Belegfeld 2",
		# Skonto-Betrag / -Abzug (Der Wert 0 ist unzulässig)
		"Skonto",
		# Beschreibung des Buchungssatzes
		"Buchungstext",
		# Mahn- / Zahl-Sperre (1 = Postensperre)
		"Postensperre",
		"Diverse Adressnummer",
		"Geschäftspartnerbank",
		"Sachverhalt",
		# Keine Mahnzinsen
		"Zinssperre",
		# Link auf den Buchungsbeleg (Programmkürzel + GUID)
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
		# Zuordnung des Geschäftsvorfalls für die Kostenrechnung
		"KOST1 - Kostenstelle",
		"KOST2 - Kostenstelle",
		"KOST-Menge",
		# USt-ID-Nummer (Beispiel: DE133546770)
		"EU-Mitgliedstaat u. USt-IdNr.",
		# Der im EU-Bestimmungsland gültige Steuersatz
		"EU-Steuersatz",
		# I = Ist-Versteuerung,
		# K = keine Umsatzsteuerrechnung
		# P = Pauschalierung (z. B. für Land- und Forstwirtschaft),
		# S = Soll-Versteuerung
		"Abw. Versteuerungsart",
		# Sachverhalte gem. § 13b Abs. 1 Satz 1 Nrn. 1.-5. UStG
		"Sachverhalt L+L",
		# Steuersatz / Funktion zum L+L-Sachverhalt (Beispiel: Wert 190 für 19%)
		"Funktionsergänzung L+L",
		# Bei Verwendung des BU-Schlüssels 49 für „andere Steuersätze“ muss der
		# steuerliche Sachverhalt mitgegeben werden
		"BU 49 Hauptfunktionstyp",
		"BU 49 Hauptfunktionsnummer",
		"BU 49 Funktionsergänzung",
		# Zusatzinformationen, besitzen den Charakter eines Notizzettels und können
		# frei erfasst werden.
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
		# Wirkt sich nur bei Sachverhalt mit SKR 14 Land- und Forstwirtschaft aus,
		# für andere SKR werden die Felder beim Import / Export überlesen bzw.
		# leer exportiert.
		"Stück",
		"Gewicht",
		# 1 = Lastschrift
		# 2 = Mahnung
		# 3 = Zahlung
		"Zahlweise",
		"Forderungsart",
		# JJJJ
		"Veranlagungsjahr",
		# TTMMJJJJ
		"Zugeordnete Fälligkeit",
		# 1 = Einkauf von Waren
		# 2 = Erwerb von Roh-Hilfs- und Betriebsstoffen
		"Skontotyp",
		# Allgemeine Bezeichnung, des Auftrags / Projekts.
		"Auftragsnummer",
		# AA = Angeforderte Anzahlung / Abschlagsrechnung
		# AG = Erhaltene Anzahlung (Geldeingang)
		# AV = Erhaltene Anzahlung (Verbindlichkeit)
		# SR = Schlussrechnung
		# SU = Schlussrechnung (Umbuchung)
		# SG = Schlussrechnung (Geldeingang)
		# SO = Sonstige
		"Buchungstyp",
		"USt-Schlüssel (Anzahlungen)",
		"EU-Mitgliedstaat (Anzahlungen)",
		"Sachverhalt L+L (Anzahlungen)",
		"EU-Steuersatz (Anzahlungen)",
		"Erlöskonto (Anzahlungen)",
		# Wird beim Import durch SV (Stapelverarbeitung) ersetzt.
		"Herkunft-Kz",
		# Wird von DATEV verwendet.
		"Leerfeld",
		# Format TTMMJJJJ
		"KOST-Datum",
		# Vom Zahlungsempfänger individuell vergebenes Kennzeichen eines Mandats
		# (z.B. Rechnungs- oder Kundennummer).
		"SEPA-Mandatsreferenz",
		# 1 = Skontosperre
		# 0 = Keine Skontosperre
		"Skontosperre",
		# Gesellschafter und Sonderbilanzsachverhalt
		"Gesellschaftername",
		# Amtliche Nummer aus der Feststellungserklärung
		"Beteiligtennummer",
		"Identifikationsnummer",
		"Zeichnernummer",
		# Format TTMMJJJJ
		"Postensperre bis",
		# Gesellschafter und Sonderbilanzsachverhalt
		"Bezeichnung SoBil-Sachverhalt",
		"Kennzeichen SoBil-Buchung",
		# 0 = keine Festschreibung
		# 1 = Festschreibung
		"Festschreibung",
		# Format TTMMJJJJ
		"Leistungsdatum",
		# Format TTMMJJJJ
		"Datum Zuord. Steuerperiode",
		# OPOS-Informationen, Format TTMMJJJJ
		"Fälligkeit",
		# G oder 1 = Generalumkehr
		# 0 = keine Generalumkehr
		"Generalumkehr (GU)",
		# Steuersatz für Steuerschlüssel
		"Steuersatz",
		# Beispiel: DE für Deutschland
		"Land"
	]

	empty_df = pd.DataFrame(columns=columns)
	data_df = pd.DataFrame.from_records(data)

	result = empty_df.append(data_df)
	result['Belegdatum'] = pd.to_datetime(result['Belegdatum'])

	header = ';'.join(header).encode('latin_1')
	data = result.to_csv(
		# Reason for str(';'): https://github.com/pandas-dev/pandas/issues/6035
		sep=str(';'),
		# European decimal seperator
		decimal=',',
		# Windows "ANSI" encoding
		encoding='latin_1',
		# format date as DDMM
		date_format='%d%m',
		# Windows line terminator
		line_terminator='\r\n',
		# Do not number rows
		index=False,
		# Use all columns defined above
		columns=columns,
		# Quote most fields, even currency values with "," separator
		quoting=QUOTE_NONNUMERIC
	)

	if not six.PY2:
		data = data.encode('latin_1')

	return header + b'\r\n' + data

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

	validate(filters)

	filters['account_number_length'] = frappe.get_value('DATEV Settings', filters.get('company'), 'account_number_length')

	fiscal_year = get_fiscal_year(date=filters.get('from_date'), company=filters.get('company'))
	filters['fiscal_year_start'] = fiscal_year[1]

	data = get_gl_entries(filters, as_dict=1)

	frappe.response['result'] = get_datev_csv(data, filters)
	frappe.response['doctype'] = 'EXTF_Buchungsstapel'
	frappe.response['type'] = 'csv'
