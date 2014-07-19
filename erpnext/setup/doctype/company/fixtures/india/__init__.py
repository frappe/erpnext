# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

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
		'tax_rate': 5,
		'root_type': 6
	}

	acc_list_india = [
		[_('CENVAT Capital Goods'),_(_('Tax Assets')),'Ledger','Chargeable','Balance Sheet', None, 'Asset'],
		[_('CENVAT'),_('Tax Assets'),'Ledger','Chargeable','Balance Sheet', None, 'Asset'],
		[_('CENVAT Service Tax'),_('Tax Assets'),'Ledger','Chargeable','Balance Sheet', None, 'Asset'],
		[_('CENVAT Service Tax Cess 1'),_('Tax Assets'),'Ledger','Chargeable','Balance Sheet', None, 'Asset'],
		[_('CENVAT Service Tax Cess 2'),_('Tax Assets'),'Ledger','Chargeable','Balance Sheet', None, 'Asset'],
		[_('CENVAT Edu Cess'),_('Tax Assets'),'Ledger','Chargeable','Balance Sheet', None, 'Asset'],
		[_('CENVAT SHE Cess'),_('Tax Assets'),'Ledger','Chargeable','Balance Sheet', None, 'Asset'],
		[_('Excise Duty 4'),_('Tax Assets'),'Ledger','Tax','Balance Sheet','4.00', 'Asset'],
		[_('Excise Duty 8'),_('Tax Assets'),'Ledger','Tax','Balance Sheet','8.00', 'Asset'],
		[_('Excise Duty 10'),_('Tax Assets'),'Ledger','Tax','Balance Sheet','10.00', 'Asset'],
		[_('Excise Duty 14'),_('Tax Assets'),'Ledger','Tax','Balance Sheet','14.00', 'Asset'],
		[_('Excise Duty Edu Cess 2'),_('Tax Assets'),'Ledger','Tax','Balance Sheet','2.00', 'Asset'],
		[_('Excise Duty SHE Cess 1'),_('Tax Assets'),'Ledger','Tax','Balance Sheet','1.00', 'Asset'],
		[_('P L A'),_('Tax Assets'),'Ledger','Chargeable','Balance Sheet', None, 'Asset'],
		[_('P L A - Cess Portion'),_('Tax Assets'),'Ledger','Chargeable','Balance Sheet', None, 'Asset'],
		[_('Edu. Cess on Excise'),_('Duties and Taxes'),'Ledger','Tax','Balance Sheet','2.00', 'Liability'],
		[_('Edu. Cess on Service Tax'),_('Duties and Taxes'),'Ledger','Tax','Balance Sheet','2.00', 'Liability'],
		[_('Edu. Cess on TDS'),_('Duties and Taxes'),'Ledger','Tax','Balance Sheet','2.00', 'Liability'],
		[_('Excise Duty @ 4'),_('Duties and Taxes'),'Ledger','Tax','Balance Sheet','4.00', 'Liability'],
		[_('Excise Duty @ 8'),_('Duties and Taxes'),'Ledger','Tax','Balance Sheet','8.00', 'Liability'],
		[_('Excise Duty @ 10'),_('Duties and Taxes'),'Ledger','Tax','Balance Sheet','10.00', 'Liability'],
		[_('Excise Duty @ 14'),_('Duties and Taxes'),'Ledger','Tax','Balance Sheet','14.00', 'Liability'],
		[_('Service Tax'),_('Duties and Taxes'),'Ledger','Tax','Balance Sheet','10.3', 'Liability'],
		[_('SHE Cess on Excise'),_('Duties and Taxes'),'Ledger','Tax','Balance Sheet','1.00', 'Liability'],
		[_('SHE Cess on Service Tax'),_('Duties and Taxes'),'Ledger','Tax','Balance Sheet','1.00', 'Liability'],
		[_('SHE Cess on TDS'),_('Duties and Taxes'),'Ledger','Tax','Balance Sheet','1.00', 'Liability'],
		[_('Professional Tax'),_('Duties and Taxes'),'Ledger','Chargeable','Balance Sheet', None, 'Liability'],
		[_('VAT'),_('Duties and Taxes'),'Ledger','Chargeable','Balance Sheet', None, 'Liability'],
		[_('TDS (Advertisement)'),_('Duties and Taxes'),'Ledger','Chargeable','Balance Sheet', None, 'Liability'],
		[_('TDS (Commission)'),_('Duties and Taxes'),'Ledger','Chargeable','Balance Sheet', None, 'Liability'],
		[_('TDS (Contractor)'),_('Duties and Taxes'),'Ledger','Chargeable','Balance Sheet', None, 'Liability'],
		[_('TDS (Interest)'),_('Duties and Taxes'),'Ledger','Chargeable','Balance Sheet', None, 'Liability'],
		[_('TDS (Rent)'),_('Duties and Taxes'),'Ledger','Chargeable','Balance Sheet', None, 'Liability'],
		[_('TDS (Salary)'),_('Duties and Taxes'),'Ledger','Chargeable','Balance Sheet', None, 'Liability']
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
