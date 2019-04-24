# coding: utf-8
from __future__ import unicode_literals
import json
from six import string_types
import frappe
from frappe.utils import format_datetime
from frappe import _


def execute(filters=None):
	validate_filters(filters)
	result = get_gl_entries(filters, as_dict=0)
	columns = get_columns()

	return columns, result


def validate_filters(filters):
	if not filters.get('company'):
		frappe.throw(_('{0} is mandatory').format(_('Company')))

	if not filters.get('fiscal_year'):
		frappe.throw(_('{0} is mandatory').format(_('Fiscal Year')))


def get_columns():
	columns = [
		{
			"label": "Umsatz (ohne Soll/Haben-Kz)",
			"fieldname": "umsatz",
			"fieldtype": "Currency",
		},
		{
			"label": "Soll/Haben-Kennzeichen",
			"fieldname": "soll_haben_kennzeichen",
			"fieldtype": "Data",
		},
		{
			"label": "Kontonummer",
			"fieldname": "kontonummer",
			"fieldtype": "Data",
		},
		{
			"label": "Gegenkonto (ohne BU-Schlüssel)",
			"fieldname": "gegenkonto_nummer",
			"fieldtype": "Data",
		},
		{
			"label": "Belegdatum",
			"fieldname": "belegdatum",
			"fieldtype": "Date",
		}
	]

	return columns


def get_gl_entries(filters, as_dict):
	gl_entries = frappe.db.sql("""
		select

			case gl.debit when 0 then gl.credit else gl.debit end as Umsatz,
			case gl.debit when 0 then 'H' else 'S' end as Kennzeichen,
			coalesce(acc.account_number, acc_pa.account_number) as Kontonummer,
			coalesce(acc_against.account_number, acc_against_pa.account_number) as Gegenkonto,
			gl.posting_date as Belegdatum

		from `tabGL Entry` gl

			/* Statistisches Konto (Debitoren/Kreditoren) */
			left join `tabParty Account` pa
			on gl.against = pa.parent

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

		where gl.company=%(company)s and gl.fiscal_year=%(fiscal_year)s
		order by 'Belegdatum:Date', voucher_no""", filters, as_dict=as_dict)

	return gl_entries


def get_datev_csv(data):
	title_row = [
		"Umsatz (ohne Soll/Haben-Kz)",
		"Soll/Haben-Kennzeichen",
		"Kontonummer",
		"Gegenkonto (ohne BU-Schlüssel)",
		"Belegdatum"
	]

	result = ['"' + '";"'.join(title_row) + '"']
	result += [
		';'.join(
			[
				'{:.2f}'.format(d.get('Umsatz')).replace('.', ','),
				'"{}"'.format(d.get('Kennzeichen')),
				d.get('Kontonummer'),
				# Can be empty, if there are no debtor / creditor accounts
				d.get('Gegenkonto') or '',
				format_datetime(d.get('Belegdatum'), 'ddMMyyyy')
			]
		) for d in data
	]

	return b'\r\n'.join(result).encode(encoding='latin_1')


@frappe.whitelist()
def download_datev_csv(filters=None):
	if isinstance(filters, string_types):
		filters = json.loads(filters)

	validate_filters(filters)
	data = get_gl_entries(filters, as_dict=1)

	filename = 'DATEV_Buchungsstapel_{}-{}'.format(
		filters.get('company'),
		filters.get('fiscal_year')
	)

	frappe.response['result'] = get_datev_csv(data)
	frappe.response['doctype'] = filename
	frappe.response['type'] = 'csv'
