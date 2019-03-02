# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
import re
import traceback
import zipfile
import frappe
from frappe.model.document import Document
from bs4 import BeautifulSoup as bs
from  erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import create_charts

PRIMARY_ACCOUNT = "Primary"

class TallyMigration(Document):
	def _preprocess(self):
		company, chart_of_accounts_tree, customers, suppliers = self._process_master_data()
		parties, addresses = self._process_parties(customers, suppliers)
		self.tally_company = company
		self.erpnext_company = company
		self.status = "Preprocessed"

		coa_file = frappe.get_doc({
			"doctype": "File",
			"file_name": "COA.json",
			"attached_to_doctype": self.doctype,
			"attached_to_name": self.name,
			"content": json.dumps(chart_of_accounts_tree)
		}).insert()
		self.chart_of_accounts = coa_file.file_url

		parties_file = frappe.get_doc({
			"doctype": "File",
			"file_name": "Parties.json",
			"attached_to_doctype": self.doctype,
			"attached_to_name": self.name,
			"content": json.dumps(parties)
		}).insert()
		self.parties = parties_file.file_url

		addresses_file = frappe.get_doc({
			"doctype": "File",
			"file_name": "Addresses.json",
			"attached_to_doctype": self.doctype,
			"attached_to_name": self.name,
			"content": json.dumps(addresses)
		}).insert()
		self.addresses = addresses_file.file_url

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
				parents[account].update(parents.get(parent, []))
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

	def _process_parties(self, customers, suppliers):
		def get_master_collection(master_data):
			master_file = frappe.get_doc("File", {"file_url": master_data})

			with zipfile.ZipFile(master_file.get_full_path()) as zf:
				content = zf.read(zf.namelist()[0]).decode("utf-16")

			master = bs(sanitize(emptify(content)), "xml")
			collection = master.BODY.IMPORTDATA.REQUESTDATA
			return collection

		def get_parties_addresses(collection, customers, suppliers):
			parties, addresses = [], []
			for account in collection.find_all("LEDGER"):
				party_type = None
				if account.NAME.string in customers:
					party_type = "Customer"
					parties.append({
						"doctype": party_type,
						"customer_name": account.NAME.string,
						"tax_id": account.INCOMETAXNUMBER.string if account.INCOMETAXNUMBER else None,
						"customer_group": "All Customer Groups",
						"territory": "All Territories",
						"customer_type": "Individual",
					})
				elif account.NAME.string in suppliers:
					party_type = "Supplier"
					parties.append({
						"doctype": party_type,
						"supplier_name": account.NAME.string,
						"pan": account.INCOMETAXNUMBER.string if account.INCOMETAXNUMBER else None,
						"supplier_group": "All Supplier Groups",
						"supplier_type": "Individual",
					})
				if party_type:
					address = "\n".join([a.string for a in account.find_all("ADDRESS")[:2]])
					addresses.append({
						"doctype": "Address",
						"address_line1": address[:140].strip(),
						"address_line2": address[140:].strip(),
						"country": account.COUNTRYNAME.string if account.COUNTRYNAME else None,
						"state": account.STATENAME.string if account.STATENAME else None,
						"gst_state": account.STATENAME.string if account.STATENAME else None,
						"pin_code": account.PINCODE.string if account.PINCODE else None,
						"gstin": account.PARTYGSTIN.string if account.PARTYGSTIN else None,
						"links": [{"link_doctype": party_type, "link_name": account["NAME"]}],
					})
			return parties, addresses

		collection = get_master_collection(self.master_data)
		parties, addresses = get_parties_addresses(collection, customers, suppliers)
		return parties, addresses

	def preprocess(self):
		frappe.enqueue_doc(self.doctype, self.name, "_preprocess")

	def _start_import(self):
		def create_company_and_coa(coa_file_url):
			coa_file = frappe.get_doc("File", {"file_url": coa_file_url})
			frappe.local.flags.ignore_chart_of_accounts = True
			company = frappe.get_doc({
				"doctype": "Company",
				"company_name": self.erpnext_company,
				"default_currency": "INR",
			}).insert()
			frappe.local.flags.ignore_chart_of_accounts = False
			create_charts(company.name, json.loads(coa_file.get_content()))

		def create_parties_addresses(parties_file_url, addresses_file_url):
			parties_file = frappe.get_doc("File", {"file_url": parties_file_url})
			for party in json.loads(parties_file.get_content()):
				try:
					frappe.get_doc(party).insert()
				except:
					log(party)
			addresses_file = frappe.get_doc("File", {"file_url": addresses_file_url})
			for address in json.loads(addresses_file.get_content()):
				try:
					frappe.get_doc(address).insert(ignore_mandatory=True)
				except:
					log(address)

		create_company_and_coa(self.chart_of_accounts)
		create_parties_addresses(self.parties, self.addresses)

	def start_import(self):
		frappe.enqueue_doc(self.doctype, self.name, "_start_import")


def log(data=None):
	message = json.dumps({"data": data, "exception": traceback.format_exc()}, indent=4)
	frappe.log_error(title="Tally Migration Error", message=message)

def sanitize(string):
	return re.sub("&#4;", "", string)

def emptify(string):
	string = re.sub(r"<\w+/>", "", string)
	string = re.sub(r"<([\w.]+)>\s*<\/\1>", "", string)
	string = re.sub(r"\r\n", "", string)
	return string
