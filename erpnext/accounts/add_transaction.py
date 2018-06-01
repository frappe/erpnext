# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

import frappe
from erpnext.accounts.general_ledger import make_gl_entries
from frappe.utils import flt


@frappe.whitelist(allow_guest=True)
def add_transaction():
    # 'account',
    # 'amount_type' => 'credit | debit’,
    # 'amount',
    # 'statement',
    # ‘operation’,
    # ‘contract_id’,
    # ‘payment_id’,
    # ‘property_id’,
    # ‘unit_id’,
    # ‘user_id’
    # ‘customer_id’
    # ‘transaction_id’

    account = frappe.form_dict['account']
    to_account = frappe.form_dict['to_account']
    amount_type = frappe.form_dict['amount_type']
    amount = frappe.form_dict['amount']
    # statement = frappe.form_dict['statement']
    # operation = frappe.form_dict['operation']
    contract_id = frappe.form_dict['contract_id']
    # payment_id = frappe.form_dict['payment_id']
    # property_id = frappe.form_dict['property_id']
    # unit_id = frappe.form_dict['unit_id']
    user_id = frappe.form_dict['user_id']
    customer_id = frappe.form_dict['customer_id']
    transaction_id = frappe.form_dict['transaction_id']

    if frappe.db.exists(
            "Customer",
            dict(
                customer_name=customer_id
            )
    ):
        to_customer = frappe.get_doc(
            doctype="Customer",
            naming_series="CUST-",
            customer_name=customer_id,
            customer_type="Individual",
            customer_group="Individual",
            territory="All Territories",
            disabled=0,
            default_currency="SAR",
            language="ar"
        )
        to_customer.insert(ignore_permissions=True)
    else:
        to_customer = frappe.get_doc(
            "Customer",
            dict(
                customer_name=customer_id
            )
        )

    if frappe.db.exists(
            "Customer",
            dict(
                customer_name=user_id
            )
    ):
        customer = frappe.get_doc(
            doctype="Customer",
            naming_series="CUST-",
            customer_name=user_id,
            customer_type="Company",
            customer_group="Commercial",
            territory="All Territories",
            disabled=0,
            default_currency="SAR",
            language="ar"
        )
        customer.insert(ignore_permissions=True)
    else:
        customer = frappe.get_doc(
            "Customer",
            dict(
                customer_name=user_id
            )
        )
    if amount_type == "credit":
        customer, to_customer = to_customer, customer
        payment_type = "Receive"
    else:
        payment_type = "Pay"
    company_id = frappe.get_value("Company", dict(), "name")
    payment_entry = frappe.get_doc(
        dict(
            doctype="Payment Entry",
            naming_series="PE-",
            payment_type=payment_type,
            posting_date=datetime.now().date(),
            company=company_id,
            mode_of_payment="Cash",
            party_type="Customer",
            party=to_customer.name,
            party_name=to_customer.customer_name,
            paid_from=account,
            paid_from_account_currency="SAR",
            paid_to=to_account,
            paid_to_account_currency="SAR",
            paid_amount=abs(amount),
            source_exchange_rate=1,
            base_paid_amount=abs(amount),
            received_amount=0,
            target_exchange_rate=1,
            base_received_amount=0,
            reference_no="{0}-{1}".format(transaction_id, contract_id),
            reference_date=datetime.now().date()
        )
    )
    payment_entry.insert(ignore_permissions=True)

    gl_entries = get_gl_entries(payment_entry=payment_entry)

    if gl_entries:
        # if POS and amount is written off, updating outstanding amt after posting all gl entries
        update_outstanding = "Yes"
        make_gl_entries(
            gl_entries,
            cancel=False,
            update_outstanding=update_outstanding,
            merge_entries=False)
    frappe.db.commit()
    return dict(status=True, message="Transactions are added to erpnext successfully")


def get_gl_entries(payment_entry):
    # from erpnext.accounts.general_ledger import merge_similar_entries
    gl_entries = []

    make_transaction(gl_entries, payment_entry)

    # make_sales_gl_entry(gl_entries)
    #
    # make_purchase_gl_entries(gl_entries)

    # self.add_extra_loss_or_benifit(gl_entries)
    # gl_entries = merge_similar_entries(gl_entries)

    return gl_entries


def make_sales_gl_entry(gl_entries):
    pass


def make_purchase_gl_entries(gl_entries):
    pass


def make_transaction(gl_entries, payment_entry):
    cash_grand_total = flt(payment_entry.paid_amount, payment_entry.precision("paid_amount"))

    if cash_grand_total:
        payment_entry.remarks = payment_entry.reference_no

        gl_entries.append(
            get_gl_dict({
                "account": payment_entry.paid_from,
                "party_type": payment_entry.party_type,
                "party": payment_entry.party,
                "against": payment_entry.paid_to,
                "credit": cash_grand_total,
                "credit_in_account_currency": cash_grand_total,
                "against_voucher": payment_entry.name,
                "against_voucher_type": payment_entry.doctype
            }, payment_entry)
        )
        payment_entry.remarks = payment_entry.reference_no

        gl_entries.append(
            get_gl_dict({
                "account": payment_entry.paid_to,
                "party_type": payment_entry.party_type,
                "party": payment_entry.party,
                "against": payment_entry.paid_from,
                "debit": cash_grand_total,
                "debit_in_account_currency": cash_grand_total,
                "against_voucher": payment_entry.name,
                "against_voucher_type": payment_entry.doctype
            }, payment_entry)
        )


def get_gl_dict(data, payment_entry):
    """this method populates the common properties of a gl entry record"""

    fiscal_year = str(datetime.now().year)

    gl_dict = frappe._dict({
        'company': payment_entry.company,
        'posting_date': payment_entry.posting_date,
        'fiscal_year': fiscal_year,
        'voucher_type': payment_entry.doctype,
        'voucher_no': payment_entry.name,
        'remarks': payment_entry.get("remarks"),
        'debit': 0,
        'credit': 0,
        'debit_in_account_currency': 0,
        'credit_in_account_currency': 0,
        'is_opening': payment_entry.get("is_opening") or "No",
        'party_type': None,
        'party': None,
        'project': frappe.get_value("Project", dict(), "name")
    })
    gl_dict.update(data)

    return gl_dict
