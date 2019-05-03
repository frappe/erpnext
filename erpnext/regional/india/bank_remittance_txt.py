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

def create_bank_remittance_txt(name):
    payment_order = frappe.get_doc("Payment Order", name)

    no_of_records = len(payment_order.get("references"))
    total_amount = reduce(lambda x, y: x.get("amount") + y.get("amount"), payment_order.get("references"))

    header = get_header_row(payment_order)
    batch = get_batch_row(payment_order, no_of_records, total_amount)

    detail = []
    for ref_doc in payment_order.get("references"):
        detail.append(get_detail_row(ref_doc, format_date(doc.posting_date))

    trailer = get_trailer_row(no_of_records, total_amount)

    detail_records = "\n".join(detail)

    return "~".join([header, batch , detail_records, trailer])

@frappe.whitelist()
def generate_report_and_get_url(name):
    data = create_bank_remittance_txt(name)
    file_name = generate_file_name(name)
    f = frappe.get_doc({
        'doctype': 'File',
        'file_name': file_name+'.txt',
        'content': data,
        'is_private': True
    })
    f.save()

def generate_file_name(name):
    ''' generate file name with format (account_code)_mmdd_(payment_order_no) '''
    return name

def get_header_row(doc):
    client_code = "ELECTROLAB"
    file_name = generate_file_name(doc.name)
    header = ["H"]
    header.append(cstr(client_code)[:20])
    header += [''] * 3
    header.append(cstr(file_name)[:20])
    return "~".join(header)

def get_batch_row(doc, no_of_records, total_amount):
    product_code = "VENPAY"
    batch = ["B"]
    batch.append(cstr(no_of_records)[:5]) # 5
    batch.append(cstr(total_amount)[:17]) #amt 17.2
    batch.append(sanitize_to_alphanumeric(doc.name)[:20])
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
    supplier_billing_address = frappe.get_doc('Address', addr_link)
    detail = OrderedDict(
        record_identifier='D',
        payment_ref_no=sanitize_to_alphanumeric(ref_doc.payment_entry),
        payment_type=ref_doc.mode_of_payment[:10],
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
        beneficiary_name=sanitize_to_alphanumeric(payment_entry.party)[:160],
        beneficiary_bank=sanitize_to_alphanumeric(supplier_bank_details.bank)[:10],
        beneficiary_branch_ifsc_code=supplier_bank_details.branch_code,
        beneficiary_acc_no=supplier_bank_details.bank_account_no,
        location=supplier_billing_address.city,
        print_location=supplier_billing_address.city,
        beneficiary_address_1=supplier_billing_address.address_line1,
        beneficiary_address_2=supplier_billing_address.address_line2,
        beneficiary_address_3='',
        beneficiary_address_4='',
        beneficiary_address_5='',
        beneficiary_city=supplier_billing_address.address_line1,
        beneficiary_zipcode=supplier_billing_address.pincode,
        beneficiary_state=supplier_billing_address.state,
        beneficiary_email=supplier_billing_address.email_address,
        beneficiary_mobile=supplier_billing_address.phone,
        payment_details_1='',
        payment_details_2='',
        payment_details_3='',
        payment_details_4='',
        delivery_mode=''
    )
    return "~".join(list(detail.values()))

def get_advice_row(doc):
    advice = ['A']

def get_trailer_row(no_of_records, total_amount):
    trailer = ["T"]
    trailer.append(cstr(no_of_records)[:5]) # 5
    trailer.append(cstr(total_amount)[:17]) # 17.2
    return "~".join(trailer)

def sanitize_to_alphanumeric(val):
    ''' Remove all the non-alphanumeric characters from string '''
    pattern = pattern = re.compile('[\W_]+')
    return pattern.sub(' ', val)

def format_date(val):
    ''' Convert a datetime object to DD/MM/YYYY format '''
    return val.strftime("%d/%m/%Y")