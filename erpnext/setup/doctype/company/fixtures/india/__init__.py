# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def install(company):
	docs = [
		{'doctype': 'Deduction Type', 'name': 'Professional Tax', 'description': 'Professional Tax', 'deduction_name': 'Professional Tax'},
		{'doctype': 'Deduction Type', 'name': 'Provident Fund', 'description': 'Provident fund', 'deduction_name': 'Provident Fund'},
		{'doctype': 'Earning Type', 'name': 'House Rent Allowance', 'description': 'House Rent Allowance', 'earning_name': 'House Rent Allowance', 'taxable': 'No'},
	]

	for d in docs:
		try:
			frappe.get_doc(d).insert()
		except frappe.NameError:
			pass


	# accounts

	fld_dict = {
		'account_name': 0,
		'parent_account': 1,
		'group_or_ledger': 2,
		'account_type': 3,
		'report_type': 4,
		'tax_rate': 5
	}

	acc_list_india = [
		['CENVAT Capital Goods','Tax Assets','Ledger','Chargeable','Balance Sheet',''],
		['CENVAT','Tax Assets','Ledger','Chargeable','Balance Sheet',''],
		['CENVAT Service Tax','Tax Assets','Ledger','Chargeable','Balance Sheet',''],
		['CENVAT Service Tax Cess 1','Tax Assets','Ledger','Chargeable','Balance Sheet',''],
		['CENVAT Service Tax Cess 2','Tax Assets','Ledger','Chargeable','Balance Sheet',''],
		['CENVAT Edu Cess','Tax Assets','Ledger','Chargeable','Balance Sheet',''],
		['CENVAT SHE Cess','Tax Assets','Ledger','Chargeable','Balance Sheet',''],
		['Excise Duty 4','Tax Assets','Ledger','Tax','Balance Sheet','4.00'],
		['Excise Duty 8','Tax Assets','Ledger','Tax','Balance Sheet','8.00'],
		['Excise Duty 10','Tax Assets','Ledger','Tax','Balance Sheet','10.00'],
		['Excise Duty 14','Tax Assets','Ledger','Tax','Balance Sheet','14.00'],
		['Excise Duty Edu Cess 2','Tax Assets','Ledger','Tax','Balance Sheet','2.00'],
		['Excise Duty SHE Cess 1','Tax Assets','Ledger','Tax','Balance Sheet','1.00'],
		['P L A','Tax Assets','Ledger','Chargeable','Balance Sheet',''],
		['P L A - Cess Portion','Tax Assets','Ledger','Chargeable','Balance Sheet',''],
		['Edu. Cess on Excise','Duties and Taxes','Ledger','Tax','Balance Sheet','2.00'],
		['Edu. Cess on Service Tax','Duties and Taxes','Ledger','Tax','Balance Sheet','2.00'],
		['Edu. Cess on TDS','Duties and Taxes','Ledger','Tax','Balance Sheet','2.00'],
		['Excise Duty @ 4','Duties and Taxes','Ledger','Tax','Balance Sheet','4.00'],
		['Excise Duty @ 8','Duties and Taxes','Ledger','Tax','Balance Sheet','8.00'],
		['Excise Duty @ 10','Duties and Taxes','Ledger','Tax','Balance Sheet','10.00'],
		['Excise Duty @ 14','Duties and Taxes','Ledger','Tax','Balance Sheet','14.00'],
		['Service Tax','Duties and Taxes','Ledger','Tax','Balance Sheet','10.3'],
		['SHE Cess on Excise','Duties and Taxes','Ledger','Tax','Balance Sheet','1.00'],
		['SHE Cess on Service Tax','Duties and Taxes','Ledger','Tax','Balance Sheet','1.00'],
		['SHE Cess on TDS','Duties and Taxes','Ledger','Tax','Balance Sheet','1.00'],
		['Professional Tax','Duties and Taxes','Ledger','Chargeable','Balance Sheet',''],
		['VAT','Duties and Taxes','Ledger','Chargeable','Balance Sheet',''],
		['TDS (Advertisement)','Duties and Taxes','Ledger','Chargeable','Balance Sheet',''],
		['TDS (Commission)','Duties and Taxes','Ledger','Chargeable','Balance Sheet',''],
		['TDS (Contractor)','Duties and Taxes','Ledger','Chargeable','Balance Sheet',''],
		['TDS (Interest)','Duties and Taxes','Ledger','Chargeable','Balance Sheet',''],
		['TDS (Rent)','Duties and Taxes','Ledger','Chargeable','Balance Sheet',''],
		['TDS (Salary)','Duties and Taxes','Ledger','Chargeable','Balance Sheet','']
	 ]

	for lst in acc_list_india:
		account = frappe.get_doc({
			"doctype": "Account",
			"freeze_account": "No",
			"master_type": "",
			"company": company.name
		})

		for d in fld_dict.keys():
			account.set(d, (d == 'parent_account' and lst[fld_dict[d]]) and lst[fld_dict[d]] +' - '+ company.abbr or lst[fld_dict[d]])

		account.insert()
