# coding: utf-8
from __future__ import unicode_literals

import datetime
import zipfile
from csv import QUOTE_NONNUMERIC

import frappe
import pandas as pd
from frappe import _
from six import BytesIO

from .datev_constants import DataCategory


def get_datev_csv(data, filters, csv_class):
	"""
	Fill in missing columns and return a CSV in DATEV Format.

	For automatic processing, DATEV requires the first line of the CSV file to
	hold meta data such as the length of account numbers oder the category of
	the data.

	Arguments:
	data -- array of dictionaries
	filters -- dict
	csv_class -- defines DATA_CATEGORY, FORMAT_NAME and COLUMNS
	"""
	empty_df = pd.DataFrame(columns=csv_class.COLUMNS)
	data_df = pd.DataFrame.from_records(data)
	result = empty_df.append(data_df, sort=True)

	if csv_class.DATA_CATEGORY == DataCategory.TRANSACTIONS:
		result['Belegdatum'] = pd.to_datetime(result['Belegdatum'])

		result['Beleginfo - Inhalt 6'] = pd.to_datetime(result['Beleginfo - Inhalt 6'])
		result['Beleginfo - Inhalt 6'] = result['Beleginfo - Inhalt 6'].dt.strftime('%d%m%Y')

		result['Fälligkeit'] = pd.to_datetime(result['Fälligkeit'])
		result['Fälligkeit'] = result['Fälligkeit'].dt.strftime('%d%m%y')

		result.sort_values(by='Belegdatum', inplace=True, kind='stable', ignore_index=True)

	if csv_class.DATA_CATEGORY == DataCategory.ACCOUNT_NAMES:
		result['Sprach-ID'] = 'de-DE'

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
		columns=csv_class.COLUMNS,
		# Quote most fields, even currency values with "," separator
		quoting=QUOTE_NONNUMERIC
	)

	data = data.encode('latin_1', errors='replace')

	header = get_header(filters, csv_class)
	header = ';'.join(header).encode('latin_1', errors='replace')

	# 1st Row: Header with meta data
	# 2nd Row: Data heading (Überschrift der Nutzdaten), included in `data` here.
	# 3rd - nth Row: Data (Nutzdaten)
	return header + b'\r\n' + data


def get_header(filters, csv_class):
	description = filters.get('voucher_type', csv_class.FORMAT_NAME)
	company = filters.get('company')
	datev_settings = frappe.get_doc('DATEV Settings', {'client': company})
	default_currency = frappe.get_value('Company', company, 'default_currency')
	coa = frappe.get_value('Company', company, 'chart_of_accounts')
	coa_short_code = '04' if 'SKR04' in coa else ('03' if 'SKR03' in coa else '')

	header = [
		# DATEV format
		#	"DTVF" = created by DATEV software,
		#	"EXTF" = created by other software
		'"EXTF"',
		# version of the DATEV format
		#	141 = 1.41, 
		#	510 = 5.10,
		#	720 = 7.20
		'700',
		csv_class.DATA_CATEGORY,
		'"%s"' % csv_class.FORMAT_NAME,
		# Format version (regarding format name)
		csv_class.FORMAT_VERSION,
		# Generated on
		datetime.datetime.now().strftime('%Y%m%d%H%M%S') + '000',
		# Imported on -- stays empty
		'',
		# Origin. Any two symbols, will be replaced by "SV" on import.
		'"EN"',
		# I = Exported by
		'"%s"' % frappe.session.user,
		# J = Imported by -- stays empty
		'',
		# K = Tax consultant number (Beraternummer)
		datev_settings.get('consultant_number', '0000000'),
		# L = Tax client number (Mandantennummer)
		datev_settings.get('client_number', '00000'),
		# M = Start of the fiscal year (Wirtschaftsjahresbeginn)
		frappe.utils.formatdate(filters.get('fiscal_year_start'), 'yyyyMMdd'),
		# N = Length of account numbers (Sachkontenlänge)
		str(filters.get('account_number_length', 4)),
		# O = Transaction batch start date (YYYYMMDD)
		frappe.utils.formatdate(filters.get('from_date'), 'yyyyMMdd') if csv_class.DATA_CATEGORY == DataCategory.TRANSACTIONS else '',
		# P = Transaction batch end date (YYYYMMDD)
		frappe.utils.formatdate(filters.get('to_date'), 'yyyyMMdd') if csv_class.DATA_CATEGORY == DataCategory.TRANSACTIONS else '',
		# Q = Description (for example, "Sales Invoice") Max. 30 chars
		'"{}"'.format(_(description)) if csv_class.DATA_CATEGORY == DataCategory.TRANSACTIONS else '',
		# R = Diktatkürzel
		'',
		# S = Buchungstyp
		#	1 = Transaction batch (Finanzbuchführung),
		#	2 = Annual financial statement (Jahresabschluss)
		'1' if csv_class.DATA_CATEGORY == DataCategory.TRANSACTIONS else '',
		# T = Rechnungslegungszweck
		#	0 oder leer = vom Rechnungslegungszweck unabhängig
		#	50 = Handelsrecht
		#	30 = Steuerrecht
		#	64 = IFRS
		#	40 = Kalkulatorik
		#	11 = Reserviert
		#	12 = Reserviert
		'0' if csv_class.DATA_CATEGORY == DataCategory.TRANSACTIONS else '',
		# U = Festschreibung
		# TODO: Filter by Accounting Period. In export for closed Accounting Period, this will be "1"
		'0',
		# V = Default currency, for example, "EUR"
		'"%s"' % default_currency if csv_class.DATA_CATEGORY == DataCategory.TRANSACTIONS else '',
		# reserviert
		'',
		# Derivatskennzeichen
		'',
		# reserviert
		'',
		# reserviert
		'',
		# SKR
		'"%s"' % coa_short_code,
		# Branchen-Lösungs-ID
		'',
		# reserviert
		'',
		# reserviert
		'',
		# Anwendungsinformation (Verarbeitungskennzeichen der abgebenden Anwendung)
		''
	]
	return header


def zip_and_download(zip_filename, csv_files):
	"""
	Put CSV files in a zip archive and send that to the client.

	Params:
	zip_filename	Name of the zip file
	csv_files		list of dicts [{'file_name': 'my_file.csv', 'csv_data': 'comma,separated,values'}]
	"""
	zip_buffer = BytesIO()

	zip_file = zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED)
	for csv_file in csv_files:
		zip_file.writestr(csv_file.get('file_name'), csv_file.get('csv_data'))

	zip_file.close()

	frappe.response['filecontent'] = zip_buffer.getvalue()
	frappe.response['filename'] = zip_filename
	frappe.response['type'] = 'binary'
