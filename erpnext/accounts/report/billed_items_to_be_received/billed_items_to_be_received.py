# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	data = get_data(filters) or []
	columns = get_columns()

	return columns, data

def get_data(report_filters):
	filters = get_report_filters(report_filters)
	fields = get_report_fields()

	return frappe.get_all('Purchase Invoice',
		fields= fields, filters=filters)

def get_report_filters(report_filters):
	filters = [['Purchase Invoice','company','=',report_filters.get('company')],
		['Purchase Invoice','posting_date','<=',report_filters.get('posting_date')], ['Purchase Invoice','docstatus','=',1],
		['Purchase Invoice','per_received','<',100], ['Purchase Invoice','update_stock','=',0]]

	if report_filters.get('purchase_invoice'):
		filters.append(['Purchase Invoice','per_received','in',[report_filters.get('purchase_invoice')]])

	return filters

def get_report_fields():
	fields = []
	for p_field in ['name', 'supplier', 'company', 'posting_date', 'currency']:
		fields.append('`tabPurchase Invoice`.`{}`'.format(p_field))

	for c_field in ['item_code', 'item_name', 'uom', 'qty', 'received_qty', 'rate', 'amount']:
		fields.append('`tabPurchase Invoice Item`.`{}`'.format(c_field))

	return fields

def get_columns():
	return [
		{
			'label': _('Purchase Invoice'),
			'fieldname': 'name',
			'fieldtype': 'Link',
			'options': 'Purchase Invoice',
			'width': 170
		},
		{
			'label': _('Supplier'),
			'fieldname': 'supplier',
			'fieldtype': 'Link',
			'options': 'Supplier',
			'width': 120
		},
		{
			'label': _('Posting Date'),
			'fieldname': 'posting_date',
			'fieldtype': 'Date',
			'width': 100
		},
		{
			'label': _('Item Code'),
			'fieldname': 'item_code',
			'fieldtype': 'Link',
			'options': 'Item',
			'width': 100
		},
		{
			'label': _('Item Name'),
			'fieldname': 'item_name',
			'fieldtype': 'Data',
			'width': 100
		},
		{
			'label': _('UOM'),
			'fieldname': 'uom',
			'fieldtype': 'Link',
			'options': 'UOM',
			'width': 100
		},
		{
			'label': _('Invoiced Qty'),
			'fieldname': 'qty',
			'fieldtype': 'Float',
			'width': 100
		},
		{
			'label': _('Received Qty'),
			'fieldname': 'received_qty',
			'fieldtype': 'Float',
			'width': 100
		},
		{
			'label': _('Rate'),
			'fieldname': 'rate',
			'fieldtype': 'Currency',
			'width': 100
		},
		{
			'label': _('Amount'),
			'fieldname': 'amount',
			'fieldtype': 'Currency',
			'width': 100
		}
	]
