# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
import re
import zipfile
import frappe
from frappe.model.document import Document
from bs4 import BeautifulSoup as bs

PRIMARY_ACCOUNT = "Primary"

class TallyMigration(Document):
	def _preprocess(self):
		company, chart_of_accounts_tree, customers, suppliers = self._process_master_data()
		self.tally_company = company
		self.erpnext_company = company
		self.status = "Preprocessed"
		self.save()

	def _process_master_data(self):
		def get_master_collection(master_data):
			master_file = frappe.get_doc("File", {"file_url": master_data})

			with zipfile.ZipFile(master_file.get_full_path()) as zf:
				content = zf.read(zf.namelist()[0]).decode("utf-16")

			master = bs(sanitize(emptify(content)), "xml")
			collection = master.BODY.IMPORTDATA.REQUESTDATA
			return collection

		def get_company_name(collection):
			return collection.find_all("REMOTECMPINFO.LIST")[0].REMOTECMPNAME.string

		def get_coa_customers_suppliers(collection):
			root_type_map = {
				"Application of Funds (Assets)": "Asset",
				"Expenses": "Expense",
				"Income": "Income",
				"Source of Funds (Liabilities)": "Liability"
			}
			roots = set(root_type_map.keys())
			accounts = list(get_groups(collection.find_all("GROUP"))) + list(get_ledgers(collection.find_all("LEDGER")))
			children, parents = get_children_and_parent_dict(accounts)
			group_set =  [acc[1] for acc in accounts if acc[2]]
			children, customers, suppliers = remove_parties(parents, children, group_set)
			coa = traverse({}, children, roots, roots, group_set)

			for account in coa:
				coa[account]["root_type"] = root_type_map[account]

			return coa, customers, suppliers

		def get_groups(accounts):
			for account in accounts:
				if account["NAME"] in (self.tally_creditors_account, self.tally_debtors_account):
					yield get_parent(account), account["NAME"], 0
				else:
					yield get_parent(account), account["NAME"], 1

		def get_ledgers(accounts):
			for account in accounts:
				# If Ledger doesn't have PARENT field then don't create Account
				# For example "Profit & Loss A/c"
				if account.PARENT:
					yield account.PARENT.string, account["NAME"], 0

		def get_parent(account):
			if account.PARENT:
				return account.PARENT.string
			return {
				("Yes", "No"): "Application of Funds (Assets)",
				("Yes", "Yes"): "Expenses",
				("No", "Yes"): "Income",
				("No", "No"): "Source of Funds (Liabilities)",
			}[(account.ISDEEMEDPOSITIVE.string, account.ISREVENUE.string)]

		def get_children_and_parent_dict(accounts):
			children, parents = {}, {}
			for parent, account, is_group in accounts:
				children.setdefault(parent, set()).add(account)
				parents.setdefault(account, set()).add(parent)
			return children, parents

		def remove_parties(parents, children, group_set):
			customers, suppliers = set(), set()
			for account in parents:
				if self.tally_creditors_account in parents[account]:
					children.pop(account, None)
					if account not in group_set:
						customers.add(account)
				elif self.tally_debtors_account in parents[account]:
					children.pop(account, None)
					if account not in group_set:
							suppliers.add(account)
			return children, customers, suppliers

		def traverse(tree, children, accounts, roots, group_set):
			for account in accounts:
				if account in group_set or account in roots:
					if account in children:
						tree[account] = traverse({}, children, children[account], roots, group_set)
					else:
						tree[account] = {"is_group": 1}
				else:
					tree[account] = {}
			return tree

		collection = get_master_collection(self.master_data)

		company = get_company_name(collection)
		chart_of_accounts_tree, customer_names, supplier_names = get_coa_customers_suppliers(collection)

		return company, chart_of_accounts_tree, customer_names, supplier_names

	def preprocess(self):
		frappe.enqueue_doc(self.doctype, self.name, "_preprocess")

	def start_import(self):
		pass

def sanitize(string):
	return re.sub("&#4;", "", string)

def emptify(string):
	string = re.sub(r"<\w+/>", "", string)
	string = re.sub(r"<([\w.]+)>\s*<\/\1>", "", string)
	string = re.sub(r"\r\n", "", string)
	return string
