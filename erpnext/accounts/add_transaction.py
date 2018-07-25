# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

import frappe
from erpnext.accounts.general_ledger import make_gl_entries
from frappe.utils import flt


@frappe.whitelist(allow_guest=True)
def add_transaction():
    # 'from_account',
    # 'to_account',
    # 'credit_amount',
    # 'debit_amount',
    # 'statement',
    # ‘company’
    # ‘branch’
    # ‘user_id’
    # ‘customer_id’
    # ‘contract_id’
    # `vat_amount`

    frappe.set_user("Administrator")
    from_account = frappe.form_dict.get('from_account', frappe.local.form_dict.get('from_account'))
    to_account = frappe.form_dict.get('to_account', frappe.local.form_dict.get('to_account'))
    credit_amount = float(frappe.form_dict.get('credit_amount', frappe.local.form_dict.get('credit_amount')))
    debit_amount = float(frappe.form_dict.get('debit_amount', frappe.local.form_dict.get('debit_amount')))
    statement = frappe.form_dict.get('statement', frappe.local.form_dict.get('statement'))
    # operation = frappe.form_dict['operation']
    contract_id = frappe.form_dict.get('contract_id', frappe.local.form_dict.get('contract_id'))
    # payment_id = frappe.form_dict['payment_id']
    # property_id = frappe.form_dict['property_id']
    # unit_id = frappe.form_dict['unit_id']
    user_id = frappe.form_dict.get('user_id', frappe.local.form_dict.get('user_id'))
    customer_id = frappe.form_dict.get('customer_id', frappe.local.form_dict.get('customer_id'))
    # transaction_id = frappe.form_dict['transaction_id']
    company_id = frappe.form_dict.get('company', frappe.local.form_dict.get('company'))
    branch_id = frappe.form_dict.get('branch', frappe.local.form_dict.get('branch'))
    vat_amount = float(frappe.form_dict.get('vat_amount', frappe.local.form_dict.get('vat_amount')))

    if branch_id:
        company_id = branch_id

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
    if credit_amount:
        customer, to_customer = to_customer, customer
        payment_type = "Receive"
        amount = credit_amount
    elif debit_amount:
        payment_type = "Pay"
        amount = debit_amount
    else:
        frappe.throw("Debit and credit cannot be both zero")

    journal_entry = frappe.get_doc(
        dict(
            doctype="Journal Entry",
            title=statement,
            voucher_type="Journal Entry",
            naming_series="JV-",
            posting_date=datetime.now(),
            company=company_id,
            user_remark=statement,
            total_debit=abs(debit_amount),
            total_credit=abs(credit_amount),
            difference=abs(debit_amount - credit_amount),
            multi_currency=0,
            remark=statement,
            bill_no=contract_id,
            bill_date=datetime.now(),
            is_opening="No",
            accounts=[]
        )
    )
    project = frappe.get_value("Project", dict(), "name")
    if credit_amount:
        journal_entry.append("accounts", dict(
            account=from_account,
            party_type="Customer",
            party=to_customer.name,
            exchange_rate=1,
            debit_in_account_currency=0,
            debit=0,
            credit_in_account_currency=abs(credit_amount),
            credit=abs(credit_amount),
            project=project,
            is_advance="No",
            against_account=to_account,
        ))
        journal_entry.append("accounts", dict(
            account=to_account,
            party_type="Company",
            party=company_id,
            exchange_rate=1,
            debit_in_account_currency=0,
            debit=0,
            credit_in_account_currency=abs(credit_amount) - abs(vat_amount),
            credit=abs(credit_amount) - abs(vat_amount),
            project=project,
            is_advance="No",
            against_account=from_account,
        ))
        if vat_amount:
            vat_account = frappe.get_value(
                "Account",
                dict(
                    account_name=("like", "%vat%")
                ),
                "account_name"
            )
            journal_entry.append("accounts", dict(
                account=vat_account,
                party_type="Company",
                party=company_id,
                exchange_rate=1,
                debit_in_account_currency=0,
                debit=0,
                credit_in_account_currency=abs(vat_amount),
                credit=abs(vat_amount),
                project=project,
                is_advance="No",
                against_account=from_account,
            ))
    else:
        journal_entry.append("accounts", dict(
            account=from_account,
            party_type="Customer",
            party=to_customer.name,
            exchange_rate=1,
            debit_in_account_currency=abs(credit_amount),
            debit=abs(credit_amount),
            credit_in_account_currency=0,
            credit=0,
            project=project,
            is_advance="No",
            against_account=to_account,
        ))
        journal_entry.append("accounts", dict(
            account=to_account,
            party_type="Company",
            party=company_id,
            exchange_rate=1,
            debit_in_account_currency=abs(credit_amount) - abs(vat_amount),
            debit=abs(credit_amount) - abs(vat_amount),
            credit_in_account_currency=0,
            credit=0,
            project=project,
            is_advance="No",
            against_account=from_account,
        ))
        if vat_amount:
            vat_account = frappe.get_value(
                "Account",
                dict(
                    account_name=("like", "%vat 5%"),
                    company=company_id
                ),
                "account_name"
            )
            journal_entry.append("accounts", dict(
                account=vat_account,
                party_type="Company",
                party=company_id,
                exchange_rate=1,
                debit_in_account_currency=abs(vat_amount),
                debit=abs(vat_amount),
                credit_in_account_currency=0,
                credit=0,
                project=project,
                is_advance="No",
                against_account=from_account,
            ))
    journal_entry.insert(ignore_permissions=True)
    # payment_entry = frappe.get_doc(
    #     dict(
    #         doctype="Payment Entry",
    #         naming_series="PE-",
    #         payment_type=payment_type,
    #         posting_date=datetime.now().date(),
    #         company=company_id,
    #         mode_of_payment="Cash",
    #         party_type="Customer",
    #         party=to_customer.name,
    #         party_name=to_customer.customer_name,
    #         paid_from=from_account,
    #         paid_from_account_currency="SAR",
    #         paid_to=to_account,
    #         paid_to_account_currency="SAR",
    #         paid_amount=abs(amount),
    #         source_exchange_rate=1,
    #         base_paid_amount=abs(amount),
    #         received_amount=0,
    #         target_exchange_rate=1,
    #         base_received_amount=0,
    #         reference_no="{0} - {1}".format(contract_id, statement),
    #         reference_date=datetime.now().date()
    #     )
    # )
    # payment_entry.insert(ignore_permissions=True)

    # gl_entries = get_gl_entries(payment_entry=payment_entry)

    # if gl_entries:
    #     # if POS and amount is written off, updating outstanding amt after posting all gl entries
    #     update_outstanding = "Yes"
    #     make_gl_entries(
    #         gl_entries,
    #         cancel=False,
    #         update_outstanding=update_outstanding,
    #         merge_entries=False)
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
