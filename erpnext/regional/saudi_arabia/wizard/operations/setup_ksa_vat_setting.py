import json
import os

import frappe


def create_ksa_vat_setting(company):
    """On creation of first company. Creates KSA VAT Setting"""

    company = frappe.get_doc('Company', company)

    file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'ksa_vat_settings.json')
    with open(file_path, 'r') as json_file:
        account_data = json.load(json_file)

    # Creating KSA VAT Setting
    ksa_vat_setting = frappe.get_doc({
        'doctype': 'KSA VAT Setting',
        'company': company.name
    })

    for data in account_data:
        if data['type'] == 'Sales Account':
            for row in data['accounts']:
                account = row['account']
                ksa_vat_setting.append('ksa_vat_sales_accounts', {
                    'title': row['title'],
                    'rate': row['rate'],
                    'account': f'{account} - {company.abbr}'
                })

        elif data['type'] == 'Purchase Account':
            for row in data['accounts']:
                account = row['account']
                ksa_vat_setting.append('ksa_vat_purchase_accounts', {
                    'title': row['title'],
                    'rate': row['rate'],
                    'account': f'{account} - {company.abbr}'
                })

    ksa_vat_setting.save()
