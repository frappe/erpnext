# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt
from webnotes.model.code import get_obj
from accounts.utils import get_balance_on

@webnotes.whitelist()
def get_default_bank_account():
	"""
		Get default bank account for a company
	"""
	company = webnotes.form_dict.get('company')
	if not company: return
	res = webnotes.conn.sql("""\
		SELECT default_bank_account FROM `tabCompany`
		WHERE name=%s AND docstatus<2""", company)
	
	if res: return res[0][0]

@webnotes.whitelist()
def get_new_jv_details():
	"""
		Get details which will help create new jv on sales/purchase return
	"""
	doclist = webnotes.form_dict.get('doclist')
	fiscal_year = webnotes.form_dict.get('fiscal_year')
	if not (isinstance(doclist, basestring) and isinstance(fiscal_year, basestring)): return

	import json
	doclist = json.loads(doclist)
	doc, children = doclist[0], doclist[1:]

	if doc.get('return_type')=='Sales Return':
		if doc.get('sales_invoice_no'):
			return get_invoice_details(doc, children, fiscal_year)
		elif doc.get('delivery_note_no'):
			return get_delivery_note_details(doc, children, fiscal_year)

	elif doc.get('purchase_receipt_no'):
		return get_purchase_receipt_details(doc, children, fiscal_year)


def get_invoice_details(doc, children, fiscal_year):
	"""
		Gets details from an invoice to make new jv
		Returns [{
			'account': ,
			'balance': ,
			'debit': ,
			'credit': ,
			'against_invoice': ,
			'against_payable': 
		}, { ... }, ...]
	"""
	if doc.get('return_type')=='Sales Return':
		obj = get_obj('Sales Invoice', doc.get('sales_invoice_no'), with_children=1)
	else:
		obj = get_obj('Purchase Invoice', doc.get('purchase_invoice_no'), with_children=1)
	if not obj.doc.docstatus==1: return

	# Build invoice account jv detail record
	invoice_rec = get_invoice_account_jv_record(doc, children, fiscal_year, obj)

	# Build item accountwise jv detail records
	item_accountwise_list = get_item_accountwise_jv_record(doc, children, fiscal_year, obj)

	return [invoice_rec] + item_accountwise_list


def get_invoice_account_jv_record(doc, children, fiscal_year, obj):
	"""
		Build customer/supplier account jv detail record
	"""
	# Calculate total return amount
	total_amt = sum([(flt(ch.get('rate')) * flt(ch.get('returned_qty'))) for ch in children])

	ret = {}

	if doc.get('return_type')=='Sales Return':
		account = obj.doc.debit_to
		ret['against_invoice'] = doc.get('sales_invoice_no')
		ret['credit'] = total_amt
	else:
		account = obj.doc.credit_to
		ret['against_voucher'] = doc.get('purchase_invoice_no')
		ret['debit'] = total_amt
	
	ret.update({
		'account': account,
		'balance': get_balance_on(account, doc.get("return_date"))
	})

	return ret


def get_item_accountwise_jv_record(doc, children, fiscal_year, obj):
	"""
		Build item accountwise jv detail records
	"""
	if doc.get('return_type')=='Sales Return':
		amt_field = 'debit'
		ac_field = 'income_account'
	else:
		amt_field = 'credit'
		ac_field = 'expense_head'
	
	inv_children = dict([[ic.fields.get('item_code'), ic] for ic in obj.doclist if ic.fields.get('item_code')])

	accwise_list = []
	
	for ch in children:
		inv_ch = inv_children.get(ch.get('item_code'))
		if not inv_ch: continue

		amount = flt(ch.get('rate')) * flt(ch.get('returned_qty'))

		accounts = [[jvd['account'], jvd['cost_center']] for jvd in accwise_list]
		
		if [inv_ch.fields.get(ac_field), inv_ch.fields.get('cost_center')] not in accounts:
			rec = {
				'account': inv_ch.fields.get(ac_field),
				'cost_center': inv_ch.fields.get('cost_center'),
				'balance': get_balance_on(inv_ch.fields.get(ac_field),
					doc.get("return_date"))
			}
			rec[amt_field] = amount
			accwise_list.append(rec)
		else:
			rec = accwise_list[accounts.index([inv_ch.fields.get(ac_field), inv_ch.fields.get('cost_center')])]
			rec[amt_field] = rec[amt_field] + amount
		
	return accwise_list


def get_jv_details_from_inv_list(doc, children, fiscal_year, inv_list, jv_details_list):
	"""
		Get invoice details and make jv detail records
	"""
	for inv in inv_list:
		if not inv[0]: continue

		if doc.get('return_type')=='Sales Return':
			doc['sales_invoice_no'] = inv[0]
		else:
			doc['purchase_invoice_no'] = inv[0]
		
		jv_details = get_invoice_details(doc, children, fiscal_year)
		
		if jv_details and len(jv_details)>1: jv_details_list.extend(jv_details)

	return jv_details_list


def get_prev_doc_list(obj, prev_doctype):
	"""
		Returns a list of previous doc's names
	"""
	prevdoc_list = []
	for ch in obj.doclist:
		if ch.fields.get('prevdoc_docname') and ch.fields.get('prevdoc_doctype')==prev_doctype:
			prevdoc_list.append(ch.fields.get('prevdoc_docname'))
	return prevdoc_list


def get_inv_list(table, field, value):
	"""
		Returns invoice list
	"""
	if isinstance(value, basestring):
		return webnotes.conn.sql("""\
			SELECT DISTINCT parent FROM `%s`
			WHERE %s='%s' AND docstatus=1""" % (table, field, value))
	elif isinstance(value, list):
		return webnotes.conn.sql("""\
			SELECT DISTINCT parent FROM `%s`
			WHERE %s IN ("%s") AND docstatus=1""" % (table, field, '", "'.join(value)))
	else:
		return []
	

def get_delivery_note_details(doc, children, fiscal_year):
	"""
		Gets sales invoice numbers from delivery note details
		and returns detail records for jv
	"""
	jv_details_list = []
	
	dn_obj = get_obj('Delivery Note', doc['delivery_note_no'], with_children=1)
	
	inv_list = get_inv_list('tabSales Invoice Item', 'delivery_note', doc['delivery_note_no'])

	if inv_list:
		jv_details_list = get_jv_details_from_inv_list(doc, children, fiscal_year, inv_list, jv_details_list)
	
	if not (inv_list and jv_details_list):
		so_list = get_prev_doc_list(dn_obj, 'Sales Order')
		inv_list = get_inv_list('tabSales Invoice Item', 'sales_order', so_list)
		if inv_list:
			jv_details_list = get_jv_details_from_inv_list(doc, children, fiscal_year, inv_list, jv_details_list)

	return jv_details_list


def get_purchase_receipt_details(doc, children, fiscal_year):
	"""
		Gets purchase invoice numbers from purchase receipt details
		and returns detail records for jv
	"""
	jv_details_list = []
	
	pr_obj = get_obj('Purchase Receipt', doc['purchase_receipt_no'], with_children=1)
	
	inv_list = get_inv_list('tabPurchase Invoice Item', 'purchase_receipt', doc['purchase_receipt_no'])

	if inv_list:
		jv_details_list = get_jv_details_from_inv_list(doc, children, fiscal_year, inv_list, jv_details_list)
	
	if not (inv_list and jv_details_list):
		po_list = get_prev_doc_list(pr_obj, 'Purchase Order')
		inv_list = get_inv_list('tabPurchase Invoice Item', 'purchase_order', po_list)
		if inv_list:
			jv_details_list = get_jv_details_from_inv_list(doc, children, fiscal_year, inv_list, jv_details_list)

	return jv_details_list
