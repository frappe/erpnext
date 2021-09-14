# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe import _

from erpnext.stock.stock_ledger import get_stock_ledger_entries


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters):
	columns = [{
		'label': _('Posting Date'),
		'fieldtype': 'Date',
		'fieldname': 'posting_date'
	}, {
		'label': _('Posting Time'),
		'fieldtype': 'Time',
		'fieldname': 'posting_time'
	}, {
		'label': _('Voucher Type'),
		'fieldtype': 'Link',
		'fieldname': 'voucher_type',
		'options': 'DocType',
		'width': 220
	}, {
		'label': _('Voucher No'),
		'fieldtype': 'Dynamic Link',
		'fieldname': 'voucher_no',
		'options': 'voucher_type',
		'width': 220
	}, {
		'label': _('Company'),
		'fieldtype': 'Link',
		'fieldname': 'company',
		'options': 'Company',
		'width': 220
	}, {
		'label': _('Warehouse'),
		'fieldtype': 'Link',
		'fieldname': 'warehouse',
		'options': 'Warehouse',
		'width': 220
	}]

	return columns

def get_data(filters):
	return get_stock_ledger_entries(filters, '<=', order="asc") or []
