# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint,cstr, today
from functools import reduce
import re
import datetime
from collections import OrderedDict
from frappe.core.doctype.file.file import download_file

def create_bank_remittance_txt(name):
    payment_order = frappe.get_doc("Payment Order", name)

    no_of_records = len(payment_order.get("references"))
    total_amount = reduce(lambda x, y: x.get("amount") + y.get("amount"), payment_order.get("references"))

    product_code, client_code = frappe.db.get_value("Company",
		filters={'name' : payment_order.company},
		fieldname=['product_code', 'client_code'])

	header, file_name = get_header_row(payment_order, client_code)
	batch = get_batch_row(payment_order, no_of_records, total_amount, product_code)

    detail = []
    for ref_doc in payment_order.get("references"):
        detail += get_detail_row(ref_doc, format_date(payment_order.posting_date))

    trailer = get_trailer_row(no_of_records, total_amount)
    detail_records = "\n".join(detail)

    return "\n".join([header, batch , detail_records, trailer]), file_name

@frappe.whitelist()
def generate_report(name):
    data, file_name = create_bank_remittance_txt(name)

    f = frappe.get_doc({
        'doctype': 'File',
        'file_name': file_name,
        'content': data,
        "attached_to_doctype": 'Payment Order',
        "attached_to_name": name,
        'is_private': True
    })
    f.save()
    download_file(f.file_url)

def generate_file_name(name, date):
    ''' generate file name with format (account_code)_mmdd_(payment_order_no) '''
    return '_'+date.strftime("%m%d")+sanitize_data(name, '_')+'.txt'

def get_header_row(doc, client_code):
    ''' Returns header row and generated file name '''
    file_name = generate_file_name(doc.name, doc.posting_date)
    header = ["H"]
    header.append(cstr(client_code)[:20])
    header += [''] * 3
    header.append(cstr(file_name)[:20])
    return "~".join(header), file_name

def get_batch_row(doc, no_of_records, total_amount, product_code):
    batch = ["B"]
    batch.append(cstr(no_of_records)[:5]) # 5
    batch.append(cstr(total_amount)[:17]) #amt 17.2
    batch.append(sanitize_data(doc.name, '_')[:20])
    batch.append(format_date(doc.posting_date))
    batch.append(product_code[:20])
    return "~".join(batch)

def get_detail_row(ref_doc, payment_date):
    payment_entry = frappe.get_cached_doc('Payment Entry', ref_doc.payment_entry)
    supplier_bank_details = frappe.get_cached_doc('Bank Account', ref_doc.bank_account)
    addr_link = frappe.db.get_value('Dynamic Link',
        {
        'link_doctype': 'Supplier',
        'link_name': 'Sample Supplier',
        'parenttype':'Address',
        'parent': ('like', '%-Billing')
        },'parent')
    supplier_billing_address = frappe.get_cached_doc('Address', addr_link)
    detail = OrderedDict(
        record_identifier='D',
        payment_ref_no=sanitize_data(ref_doc.payment_entry),
        payment_type=cstr(payment_entry.mode_of_payment)[:10],
        amount=str(ref_doc.amount)[:13],
        payment_date=payment_date,
        instrument_date=payment_date,
        instrument_number='',
        dr_account_no_client=str(payment_entry.bank_account_no)[:20],
        dr_description='',
        dr_ref_no='',
        cr_ref_no='',
        bank_code_indicator='M',
        beneficiary_code='',
        beneficiary_name=sanitize_data(payment_entry.party, ' ')[:160],
        beneficiary_bank=sanitize_data(supplier_bank_details.bank, ' ')[:10],
        beneficiary_branch_code=cstr(supplier_bank_details.branch_code),
        beneficiary_acc_no=supplier_bank_details.bank_account_no,
        location='',
        print_location='',
        beneficiary_address_1=cstr(supplier_billing_address.address_line1)[:50],
        beneficiary_address_2=cstr(supplier_billing_address.address_line2)[:50],
        beneficiary_address_3='',
        beneficiary_address_4='',
        beneficiary_address_5='',
        beneficiary_city=supplier_billing_address.city,
        beneficiary_zipcode=cstr(supplier_billing_address.pincode),
        beneficiary_state=supplier_billing_address.state,
        beneficiary_email=supplier_billing_address.email_id,
        beneficiary_mobile=supplier_billing_address.phone,
        payment_details_1='',
        payment_details_2='',
        payment_details_3='',
        payment_details_4='',
        delivery_mode=''
    )
    detail_record = ["~".join(list(detail.values()))]
    detail_record += get_advice_rows(payment_entry)
    return detail_record

def get_advice_rows(payment_entry):
    ''' Returns multiple advice rows for a single detail entry '''
    payment_entry_date = payment_entry.posting_date.strftime("%b%y%d%m").upper()
    mode_of_payment = payment_entry.mode_of_payment
    advice_rows = []
    for record in payment_entry.references:
        advice = ['E']
        advice.append(cstr(mode_of_payment))
        advice.append(cstr(record.total_amount))
        advice.append('')
        advice.append(cstr(record.outstanding_amount))
        advice.append(record.reference_name)
        advice.append(format_date(record.due_date))
        advice.append(payment_entry_date)
        advice += ['']*3
        advice_rows.append("~".join(advice))
    return advice_rows

def get_trailer_row(no_of_records, total_amount):
    ''' Returns trailer row '''
    trailer = ["T"]
    trailer.append(cstr(no_of_records)[:5]) # 5
    trailer.append(cstr(total_amount)[:17]) # 17.2
    return "~".join(trailer)

def sanitize_data(val, replace_str=''):
    ''' Remove all the non-alphanumeric characters from string '''
    pattern = pattern = re.compile('[\W_]+')
    return pattern.sub(replace_str, val)

def format_date(val):
    ''' Convert a datetime object to DD/MM/YYYY format '''
    return val.strftime("%d/%m/%Y")