# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

import frappe
from erpnext.accounts.general_ledger import make_gl_entries
from frappe.utils import flt


@frappe.whitelist(allow_guest=True)
def create_account():
    # 'account_name',
    # 'is_group' => 'True | False’,
    # 'company',
    # 'root_type' => 'Asset | Liability | Income |Expense |Equity',
    # ‘report_type’ => 'Balance Sheet | Profit and Loss',
    # ‘parent_account’,
    # ‘account_type’ => 'Accumulated Depreciation | Bank | Cash | Chargeable | Cost of Goods Sold | Depreciation | Equity | Expense Account | Expenses Included In Valuation | Fixed Asset | Income Account | Payable | Receivable | Round Off | Stock | Stock Adjustment | Stock Received But Not Billed\nTax | Temporary',
    # ‘tax_rate’,
    # ‘freeze_account’ => 'No | Yes',
    # ‘balance_must_be’ => 'Debit | Credit'
    
    try:
        account_name = frappe.form_dict['account_name']
        # is_group = frappe.form_dict['is_group']
        company = frappe.form_dict['company']
        root_type = frappe.form_dict['root_type']
        report_type = frappe.form_dict['report_type']
        parent_account = frappe.form_dict.get('parent_account')
        account_type = frappe.form_dict['account_type']
        tax_rate = frappe.form_dict['tax_rate']
        freeze_account = frappe.form_dict['freeze_account']
        balance_must_be = frappe.form_dict['balance_must_be']


        account = frappe.get_doc(
            dict(
                doctype="Account",
                account_name=account_name,
                is_group=0 if parent_account else 1,
                company=company,
                root_type=root_type,
                report_type=report_type,
                parent_account=parent_account,
                account_type=account_type,
                tax_rate=tax_rate,
                freeze_account=freeze_account,
                balance_must_be=balance_must_be
            )
        )
        account.insert(ignore_permissions=True)
        frappe.db.commit()

        return dict(status=True, message="Account is added to erpnext successfully")
    except Exception as e:
        return dict(status=False, message=str(e))

