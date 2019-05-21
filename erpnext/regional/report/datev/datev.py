# coding: utf-8
from __future__ import unicode_literals
import json
from six import string_types
import frappe
from frappe import _
import pandas as pd


def execute(filters=None):
	validate_filters(filters)
	result = get_gl_entries(filters, as_dict=0)
	columns = get_columns()

	return columns, result


def validate_filters(filters):
	if not filters.get('company'):
		frappe.throw(_('{0} is mandatory').format(_('Company')))

	if not filters.get('from_date'):
		frappe.throw(_('{0} is mandatory').format(_('From Date')))

	if not filters.get('to_date'):
		frappe.throw(_('{0} is mandatory').format(_('To Date')))


def get_columns():
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
	gl_entries = frappe.db.sql("""
		select

			case gl.debit when 0 then gl.credit else gl.debit end as 'Umsatz (ohne Soll/Haben-Kz)',
			case gl.debit when 0 then 'H' else 'S' end as 'Soll/Haben-Kennzeichen',
			coalesce(acc.account_number, acc_pa.account_number) as 'Kontonummer',
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
	columns = [
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
		"FunktionsergänzungL+L",
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
		decimal=',',
		encoding='latin_1',
		date_format='%d%m',
		line_terminator=b'\r\n',
		index=False,
		columns=columns
	)


@frappe.whitelist()
def download_datev_csv(filters=None):
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
