# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

import frappe


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
        root_type = frappe.form_dict.get('root_type')
        report_type = frappe.form_dict.get('report_type')
        parent_account = frappe.form_dict.get('parent_account')
        account_type = frappe.form_dict.get('account_type')
        tax_rate = frappe.form_dict.get('tax_rate')
        freeze_account = frappe.form_dict.get('freeze_account')
        balance_must_be = frappe.form_dict.get('balance_must_be')
        
        if not parent_account and not (
            root_type or report_type or account_type or tax_rate or freeze_account or balance_must_be):
            frappe.throw("You must send all data since this is a parent account")
        if parent_account:
            parent_account_data = frappe.get_value("Account", parent_account, 
                            [
                                "root_type", 
                                "report_type", 
                                "account_type", 
                                "tax_rate",
                                "freeze_account",
                                "balance_must_be"
                            ], as_dict=True)
            
            if not parent_account_data:
                frappe.throw("The parent account you chose does not existing.")
            if not root_type:
                root_type = parent_account_data.root_type
            if not report_type:
                report_type = parent_account_data.report_type
            if not account_type:
                account_type = parent_account_data.account_type
            if not tax_rate:
                tax_rate = parent_account_data.tax_rate
            if not freeze_account:
                freeze_account = parent_account_data.freeze_account
            if not balance_must_be:
                balance_must_be = parent_account_data.balance_must_be
                
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

