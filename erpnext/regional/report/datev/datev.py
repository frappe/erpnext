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
import zlib
import zipfile
import six
from csv import QUOTE_NONNUMERIC
from six import BytesIO
from six import string_types
import frappe
from frappe import _
import pandas as pd
from .datev_constants import DataCategory
from .datev_constants import Transactions
from .datev_constants import DebtorsCreditors
from .datev_constants import AccountNames
from .datev_constants import QUERY_REPORT_COLUMNS


def execute(filters=None):
	"""Entry point for frappe."""
	validate(filters)
	result = get_transactions(filters, as_dict=0)
	columns = QUERY_REPORT_COLUMNS

	return columns, result


def validate(filters):
	"""Make sure all mandatory filters and settings are present."""
	if not filters.get('company'):
		frappe.throw(_('<b>Company</b> is a mandatory filter.'))

	if not filters.get('from_date'):
		frappe.throw(_('<b>From Date</b> is a mandatory filter.'))

	if not filters.get('to_date'):
		frappe.throw(_('<b>To Date</b> is a mandatory filter.'))

	try:
		frappe.get_doc('DATEV Settings', filters.get('company'))
	except frappe.DoesNotExistError:
		frappe.throw(_('Please create <b>DATEV Settings</b> for Company <b>{}</b>.').format(filters.get('company')))


def get_transactions(filters, as_dict=1):
	"""
	Get a list of accounting entries.

	Select GL Entries joined with Account and Party Account in order to get the
	account numbers. Returns a list of accounting entries.

	Arguments:
	filters -- dict of filters to be passed to the sql query
	as_dict -- return as list of dicts [0,1]
	"""
	filter_by_voucher = 'AND gl.voucher_type = %(voucher_type)s' if filters.get('voucher_type') else ''
	gl_entries = frappe.db.sql("""
		SELECT

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

		FROM `tabGL Entry` gl

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

		WHERE gl.company = %(company)s 
		AND DATE(gl.posting_date) >= %(from_date)s
		AND DATE(gl.posting_date) <= %(to_date)s
		{}
		ORDER BY 'Belegdatum', gl.voucher_no""".format(filter_by_voucher), filters, as_dict=as_dict)

	return gl_entries


def get_customers(filters):
	"""
	Get a list of Customers.

	Arguments:
	filters -- dict of filters to be passed to the sql query
	"""
	return frappe.db.sql("""
		SELECT

			acc.account_number as 'Konto',
			cus.customer_name as 'Name (Adressatentyp Unternehmen)',
			case cus.customer_type when 'Individual' then 1 when 'Company' then 2 else 0 end as 'Adressatentyp',
			adr.address_line1 as 'Straße',
			adr.pincode as 'Postleitzahl',
			adr.city as 'Ort',
			UPPER(country.code) as 'Land',
			adr.address_line2 as 'Adresszusatz',
			con.email_id as 'E-Mail',
			coalesce(con.mobile_no, con.phone) as 'Telefon',
			cus.website as 'Internet',
			cus.tax_id as 'Steuernummer',
			ccl.credit_limit as 'Kreditlimit (Debitor)'

		FROM `tabParty Account` par

			left join `tabAccount` acc
			on acc.name = par.account

			left join `tabCustomer` cus
			on cus.name = par.parent

			left join `tabAddress` adr
			on adr.name = cus.customer_primary_address

			left join `tabCountry` country
			on country.name = adr.country

			left join `tabContact` con
			on con.name = cus.customer_primary_contact

			left join `tabCustomer Credit Limit` ccl
			on ccl.parent = cus.name
			and ccl.company = par.company

		WHERE par.company = %(company)s
		AND par.parenttype = 'Customer'""", filters, as_dict=1)


def get_suppliers(filters):
	"""
	Get a list of Suppliers.

	Arguments:
	filters -- dict of filters to be passed to the sql query
	"""
	return frappe.db.sql("""
		SELECT

			acc.account_number as 'Konto',
			sup.supplier_name as 'Name (Adressatentyp Unternehmen)',
			case sup.supplier_type when 'Individual' then '1' when 'Company' then '2' else '0' end as 'Adressatentyp',
			adr.address_line1 as 'Straße',
			adr.pincode as 'Postleitzahl',
			adr.city as 'Ort',
			UPPER(country.code) as 'Land',
			adr.address_line2 as 'Adresszusatz',
			con.email_id as 'E-Mail',
			coalesce(con.mobile_no, con.phone) as 'Telefon',
			sup.website as 'Internet',
			sup.tax_id as 'Steuernummer',
			case sup.on_hold when 1 then sup.release_date else null end as 'Zahlungssperre bis'

		FROM `tabParty Account` par

			left join `tabAccount` acc
			on acc.name = par.account

			left join `tabSupplier` sup
			on sup.name = par.parent

			left join `tabDynamic Link` dyn_adr
			on dyn_adr.link_name = sup.name
			and dyn_adr.link_doctype = 'Supplier'
			and dyn_adr.parenttype = 'Address'
			
			left join `tabAddress` adr
			on adr.name = dyn_adr.parent
			and adr.is_primary_address = '1'

			left join `tabCountry` country
			on country.name = adr.country

			left join `tabDynamic Link` dyn_con
			on dyn_con.link_name = sup.name
			and dyn_con.link_doctype = 'Supplier'
			and dyn_con.parenttype = 'Contact'

			left join `tabContact` con
			on con.name = dyn_con.parent
			and con.is_primary_contact = '1'

		WHERE par.company = %(company)s
		AND par.parenttype = 'Supplier'""", filters, as_dict=1)


def get_account_names(filters):
	return frappe.get_list("Account", 
		fields=["account_number as Konto", "name as Kontenbeschriftung"], 
		filters={"company": filters.get("company"), "is_group": "0"})


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

	if not six.PY2:
		data = data.encode('latin_1')

	header = get_header(filters, csv_class)
	header = ';'.join(header).encode('latin_1')

	# 1st Row: Header with meta data
	# 2nd Row: Data heading (Überschrift der Nutzdaten), included in `data` here.
	# 3rd - nth Row: Data (Nutzdaten)
	return header + b'\r\n' + data


def get_header(filters, csv_class):
	coa = frappe.get_value("Company", filters.get("company"), "chart_of_accounts")
	description = filters.get("voucher_type", csv_class.FORMAT_NAME)
	coa_used = "04" if "SKR04" in coa else ("03" if "SKR03" in coa else "")

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
		datetime.datetime.now().strftime("%Y%m%d%H%M%S") + '000',
		# Imported on -- stays empty
		'',
		# Origin. Any two symbols, will be replaced by "SV" on import.
		'"EN"',
		# I = Exported by
		'"%s"' % frappe.session.user,
		# J = Imported by -- stays empty
		'',
		# K = Tax consultant number (Beraternummer)
		frappe.get_value("DATEV Settings", filters.get("company"), "consultant_number"),
		# L = Tax client number (Mandantennummer)
		frappe.get_value("DATEV Settings", filters.get("company"), "client_number"),
		# M = Start of the fiscal year (Wirtschaftsjahresbeginn)
		frappe.utils.formatdate(frappe.defaults.get_user_default("year_start_date"), "yyyyMMdd"),
		# N = Length of account numbers (Sachkontenlänge)
		'4',
		# O = Transaction batch start date (YYYYMMDD)
		frappe.utils.formatdate(filters.get('from_date'), "yyyyMMdd"),
		# P = Transaction batch end date (YYYYMMDD)
		frappe.utils.formatdate(filters.get('to_date'), "yyyyMMdd"),
		# Q = Description (for example, "Sales Invoice") Max. 30 chars
		'"{}"'.format(_(description)),
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
		'0',
		# U = Festschreibung
		# TODO: Filter by Accounting Period. In export for closed Accounting Period, this will be "1"
		'0',
		# V = Default currency, for example, "EUR"
		'"%s"' % frappe.get_value("Company", filters.get("company"), "default_currency"),
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
	return header


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

	# This is where my zip will be written
	zip_buffer = BytesIO()
	# This is my zip file
	datev_zip = zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED)

	transactions = get_transactions(filters)
	transactions_csv = get_datev_csv(transactions, filters, csv_class=Transactions)
	datev_zip.writestr('EXTF_Buchungsstapel.csv', transactions_csv)

	account_names = get_account_names(filters)
	account_names_csv = get_datev_csv(account_names, filters, csv_class=AccountNames)
	datev_zip.writestr('EXTF_Kontenbeschriftungen.csv', account_names_csv)

	customers = get_customers(filters)
	customers_csv = get_datev_csv(customers, filters, csv_class=DebtorsCreditors)
	datev_zip.writestr('EXTF_Kunden.csv', customers_csv)

	suppliers = get_suppliers(filters)
	suppliers_csv = get_datev_csv(suppliers, filters, csv_class=DebtorsCreditors)
	datev_zip.writestr('EXTF_Lieferanten.csv', suppliers_csv)
	
	# You must call close() before exiting your program or essential records will not be written.
	datev_zip.close()

	frappe.response['filecontent'] = zip_buffer.getvalue()
	frappe.response['filename'] = 'DATEV.zip'
	frappe.response['type'] = 'binary'
