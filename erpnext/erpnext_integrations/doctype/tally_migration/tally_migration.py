# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
import os
import re
import sys
import traceback
import zipfile
from decimal import Decimal

from bs4 import BeautifulSoup as bs

import frappe
from erpnext import encode_company_abbr
from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import create_charts
from erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer import unset_existing_data

from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.model.document import Document
from frappe.model.naming import getseries, revert_series_if_last
from frappe.utils.data import format_datetime, cint
from frappe.utils import cstr
from frappe.utils.csvutils import to_csv

PRIMARY_ACCOUNT = "Primary"
VOUCHER_CHUNK_SIZE = 500


@frappe.whitelist()
def new_doc(document):
	document = json.loads(document)
	doctype = document.pop("doctype")
	document.pop("name", None)
	doc = frappe.new_doc(doctype)
	doc.update(document)

	return doc

def get_pincode_city_map():
	with open(os.path.join(os.path.dirname(__file__), "pincode_info.json"), "r") as local_info:
		all_data = json.loads(local_info.read())
	return all_data

class TallyMigration(Document):
	def validate(self):
		failed_import_log = json.loads(self.failed_import_log)
		sorted_failed_import_log = sorted(failed_import_log, key=lambda row: row["doc"]["creation"])
		self.failed_import_log = json.dumps(sorted_failed_import_log)

	def autoname(self):
		if not self.name:
			self.name = "Tally Migration on " + format_datetime(self.creation)

	def get_collection(self, data_file):
		def sanitize(string):
			return re.sub("&#4;", "", string)

		def emptify(string):
			string = re.sub(r"<\w+/>", "", string)
			string = re.sub(r"<([\w.]+)>\s*<\/\1>", "", string)
			string = re.sub(r"\r\n", "", string)
			return string

		master_file = frappe.get_doc("File", {"file_url": data_file})
		master_file_path = master_file.get_full_path()

		if zipfile.is_zipfile(master_file_path):
			with zipfile.ZipFile(master_file_path) as zf:
				encoded_content = zf.read(zf.namelist()[0])
				try:
					content = encoded_content.decode("utf-8-sig")
				except UnicodeDecodeError:
					content = encoded_content.decode("utf-16")

		master = bs(sanitize(emptify(content)), "xml")
		collection = master.BODY.IMPORTDATA.REQUESTDATA
		return collection

	def dump_processed_data(self, data):
		doctype_content_map = {}

		def make_doctype_content_map(data):
			for docs in data:
				if not docs: continue

				if isinstance(docs, list) and isinstance(docs[0], list):
					make_doctype_content_map(docs)
				else:
					doctype = docs[0].get("doctype")
					filename = frappe.scrub(doctype) + ".csv"
					content = make_csv_for_data_import(doctype, docs)
					doctype_content_map.setdefault(doctype, []).append(content)

		make_doctype_content_map(data)

		for doctype, contents in doctype_content_map.items():
			for i, content in enumerate(contents):
				filename = frappe.scrub(doctype) + "{}.csv".format(i+1 if len(contents) > 1 else "")
				f = self.attach_file(filename, content)
				data_import_doc = self.make_data_import_doc(doctype, f.file_url)
	
	def attach_file(self, filename, content):
		f = frappe.get_doc({
			"doctype": "File",
			"file_name":  filename,
			"attached_to_doctype": self.doctype,
			"attached_to_name": self.name,
			"content": content,
			"is_private": True
		})
		try:
			f.insert()
		except frappe.DuplicateEntryError:
			pass
		return f
	
	def make_data_import_doc(self, doctype, file_url):
		doc = frappe.get_doc({
			"doctype": "Data Import",
			"reference_doctype": doctype,
			"import_type": "Insert New Records",
			"mute_emails": 1,
			"import_file": file_url
		})
		doc.insert()
		return doc

	def set_account_defaults(self):
		self.default_cost_center, self.default_round_off_account = frappe.db.get_value("Company", self.erpnext_company, ["cost_center", "round_off_account"])
		self.default_warehouse = frappe.db.get_value("Stock Settings", "Stock Settings", "default_warehouse")

	def _process_master_data(self):
		def get_company_name(collection):
			return collection.find_all("REMOTECMPINFO.LIST")[0].REMOTECMPNAME.string.strip()

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
					yield account.PARENT.string.strip(), account["NAME"], 0

		def get_parent(account):
			if account.PARENT:
				return account.PARENT.string.strip()
			return {
				("Yes", "No"): "Application of Funds (Assets)",
				("Yes", "Yes"): "Expenses",
				("No", "Yes"): "Income",
				("No", "No"): "Source of Funds (Liabilities)",
			}[(account.ISDEEMEDPOSITIVE.string.strip(), account.ISREVENUE.string.strip())]

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
				found = False
				if self.tally_creditors_account in parents[account]:
					found = True
					if account not in group_set:
						suppliers.add(account)
				if self.tally_debtors_account in parents[account]:
					found = True
					if account not in group_set:
						customers.add(account)
				if found:
					children.pop(account, None)

			return children, customers, suppliers

		def traverse(tree, children, accounts, roots, group_set):
			for account in accounts:
				if account in group_set or account in roots:
					if account in children:
						tree[account] = traverse({}, children, children.pop(account), roots, group_set)
					else:
						tree[account] = {}
				else:
					tree[account] = {}
			return tree

		def get_parties_addresses(collection, customer_ledgers, supplier_ledgers):
			pincode_city_map = get_pincode_city_map()

			def get_city_state_from_pincode(pincode):
				for state, cities in pincode_city_map.items():
					for city, pincodes in cities.items():
						if pincode in pincodes:
							return city, state
				return None, None

			customers, suppliers, addresses = [], [], []
			for account in collection.find_all("LEDGER"):
				party_type = None
				links = []
				if account.NAME.string.strip() in customer_ledgers:
					party_type = "Customer"
					customers.append({
						"doctype": party_type,
						"customer_name": account.NAME.string.strip(),
						"tax_id": account.INCOMETAXNUMBER.string.strip() if account.INCOMETAXNUMBER else None,
						"customer_group": "All Customer Groups",
						"territory": "All Territories",
						"customer_type": "Individual",
					})
					links.append({"link_doctype": party_type, "link_name": account["NAME"]})

				if account.NAME.string.strip() in supplier_ledgers:
					party_type = "Supplier"
					suppliers.append({
						"doctype": party_type,
						"supplier_name": account.NAME.string.strip(),
						"pan": account.INCOMETAXNUMBER.string.strip() if account.INCOMETAXNUMBER else None,
						"supplier_group": "All Supplier Groups",
						"supplier_type": "Individual",
					})
					links.append({"link_doctype": party_type, "link_name": account["NAME"]})

				if party_type:
					address = "\n".join([a.string.strip() for a in account.find_all("ADDRESS")])
					tally_state = account.LEDSTATENAME.string.strip() if account.LEDSTATENAME else ""

					pincode = account.PINCODE.string.strip() if account.PINCODE else None
					pincode = str(pincode).replace("-", "").replace(" ", "")
					city, pincode_state = "", ""
					if pincode:
						city, pincode_state = get_city_state_from_pincode(cint(pincode))
					addresses.append({
						"doctype": "Address",
						"address_line1": address[:140].strip(),
						"address_line2": address[140:].strip(),
						"country": account.COUNTRYNAME.string.strip() if account.COUNTRYNAME else None,
						"phone": account.LEDGERPHONE.string.strip() if account.LEDGERPHONE else None,
						"gstin": account.PARTYGSTIN.string.strip() if account.PARTYGSTIN else None,
						"state": (pincode_state or tally_state).title(),
						"gst_state": (pincode_state or tally_state).title(),
						"pincode": pincode,
						"city": city,
						"links": links
					})
			return customers, suppliers, addresses

		def get_item_group_list(collection):
			'''
				Make multiple document list according to the parent child relation.
				i.e create parent group list first then make child group list
				Spliting into multiple list will create multiple csv files to be imported in right order
			'''

			parent_child_map = {}
			root_group = "All Item Groups"

			for item_group in collection.find_all("STOCKGROUP"):
				item_group_name = item_group.NAME.string.strip()
				parent_group_name = item_group.PARENT.string.strip() if item_group.PARENT else root_group
				parent_child_map.setdefault(parent_group_name, []).append(item_group_name)

			def get_doc(name, parent):
				return {
					"doctype": "Item Group",
					"item_group_name": name,
					"parent_item_group": parent
				}
			
			def update_group_doc(ordered_list, name):
				for docs in ordered_list:
					[d.setdefault("is_group", 1) for d in docs if d.get("item_group_name") == name]
			
			def get_child_groups_of(parent_group):
				children = parent_child_map.get(parent_group) or []
				return [get_doc(group, parent_group) for group in children]
			
			def get_sequential_list(lst, parent_group):
				docs = get_child_groups_of(parent_group)
				if docs:
					if parent_group != root_group: update_group_doc(lst, parent_group)
					lst.append(docs)

				children = parent_child_map.get(parent_group) or []
				for child in children:
					get_sequential_list(lst, child)
				
				return lst

			item_group_list = get_sequential_list([], root_group)

			return item_group_list

		def get_stock_items_uoms(collection):
			uoms = []
			for uom in collection.find_all("UNIT"):
				uoms.append({"doctype": "UOM", "uom_name": uom.NAME.string.strip()})

			items = []
			for item in collection.find_all("STOCKITEM"):
				stock_uom = item.BASEUNITS.string.strip() if item.BASEUNITS else self.default_uom
				items.append({
					"doctype": "Item",
					"item_code" : item.NAME.string.strip(),
					"stock_uom": stock_uom.strip(),
					"is_stock_item": 1,
					"item_group": item.PARENT.string.strip() if item.PARENT else "All Item Groups",
					"item_defaults": [{"company": self.erpnext_company}]
				})

			return items, uoms

		try:
			self.publish("Process Master Data", _("Reading Uploaded File"), 1, 5)
			collection = self.get_collection(self.master_data)

			self.publish("Process Master Data", _("Processing Chart of Accounts and Parties"), 2, 5)
			chart_of_accounts, customer_ledgers, supplier_ledgers = get_coa_customers_suppliers(collection)

			self.publish("Process Master Data", _("Processing Party Addresses"), 3, 5)
			customers, suppliers, addresses = get_parties_addresses(collection, customer_ledgers, supplier_ledgers)

			self.publish("Process Master Data", _("Processing Items and UOMs"), 4, 5)
			items, uoms = get_stock_items_uoms(collection)
			item_groups = get_item_group_list(collection)
			data = [uoms, item_groups, items, customers, suppliers, addresses]
			# chart_of_accounts

			self.publish("Process Master Data", _("Done"), 5, 5)
			self.dump_processed_data(data)

			self.is_master_data_processed = 1

		except:
			self.publish("Process Master Data", _("Process Failed"), -1, 5)
			self.log()

		finally:
			self.set_status()

	def publish(self, title, message, count, total):
		frappe.publish_realtime("tally_migration_progress_update", {"title": title, "message": message, "count": count, "total": total})

	def _import_master_data(self):
		def create_company_and_coa(coa_file_url):
			coa_file = frappe.get_doc("File", {"file_url": coa_file_url})
			frappe.local.flags.ignore_chart_of_accounts = True

			try:
				company = frappe.get_doc({
					"doctype": "Company",
					"company_name": self.erpnext_company,
					"default_currency": "INR",
					"enable_perpetual_inventory": 0,
				}).insert()
			except frappe.DuplicateEntryError:
				company = frappe.get_doc("Company", self.erpnext_company)
				unset_existing_data(self.erpnext_company)

			frappe.local.flags.ignore_chart_of_accounts = False
			create_charts(company.name, custom_chart=json.loads(coa_file.get_content()))
			company.on_update()

		def create_parties_and_addresses(parties_file_url, addresses_file_url):
			parties_file = frappe.get_doc("File", {"file_url": parties_file_url})
			for party in json.loads(parties_file.get_content()):
				try:
					party_doc = frappe.get_doc(party)
					party_doc.insert()
				except:
					self.log(party_doc)
			addresses_file = frappe.get_doc("File", {"file_url": addresses_file_url})
			for address in json.loads(addresses_file.get_content()):
				try:
					address_doc = frappe.get_doc(address)
					address_doc.insert(ignore_mandatory=True)
				except:
					self.log(address_doc)

		def create_items_uoms(items_file_url, uoms_file_url):
			uoms_file = frappe.get_doc("File", {"file_url": uoms_file_url})
			for uom in json.loads(uoms_file.get_content()):
				if not frappe.db.exists(uom):
					try:
						uom_doc = frappe.get_doc(uom)
						uom_doc.insert()
					except:
						self.log(uom_doc)

			items_file = frappe.get_doc("File", {"file_url": items_file_url})
			for item in json.loads(items_file.get_content()):
				try:
					item_doc = frappe.get_doc(item)
					item_doc.insert()
				except:
					self.log(item_doc)

		try:
			self.publish("Import Master Data", _("Creating Company and Importing Chart of Accounts"), 1, 4)
			create_company_and_coa(self.chart_of_accounts)

			self.publish("Import Master Data", _("Importing Parties and Addresses"), 2, 4)
			create_parties_and_addresses(self.parties, self.addresses)

			self.publish("Import Master Data", _("Importing Items and UOMs"), 3, 4)
			create_items_uoms(self.items, self.uoms)

			self.publish("Import Master Data", _("Done"), 4, 4)

			self.set_account_defaults()
			self.is_master_data_imported = 1
			frappe.db.commit()

		except:
			self.publish("Import Master Data", _("Process Failed"), -1, 5)
			frappe.db.rollback()
			self.log()

		finally:
			self.set_status()

	def _process_day_book_data(self):
		def get_vouchers(collection):
			vouchers = []
			for voucher in collection.find_all("VOUCHER"):
				if voucher.ISCANCELLED.string.strip() == "Yes":
					continue
				inventory_entries = voucher.find_all("INVENTORYENTRIES.LIST") + voucher.find_all("ALLINVENTORYENTRIES.LIST") + voucher.find_all("INVENTORYENTRIESIN.LIST") + voucher.find_all("INVENTORYENTRIESOUT.LIST")
				if voucher.VOUCHERTYPENAME.string.strip() not in ["Journal", "Receipt", "Payment", "Contra"] and inventory_entries:
					function = voucher_to_invoice
				else:
					function = voucher_to_journal_entry
				try:
					processed_voucher = function(voucher)
					if processed_voucher:
						vouchers.append(processed_voucher)
					frappe.db.commit()
				except:
					frappe.db.rollback()
					self.log(voucher)
			return vouchers

		def voucher_to_journal_entry(voucher):
			accounts = []
			ledger_entries = voucher.find_all("ALLLEDGERENTRIES.LIST") + voucher.find_all("LEDGERENTRIES.LIST")
			for entry in ledger_entries:
				account = {"account": encode_company_abbr(entry.LEDGERNAME.string.strip(), self.erpnext_company), "cost_center": self.default_cost_center}
				if entry.ISPARTYLEDGER.string.strip() == "Yes":
					party_details = get_party(entry.LEDGERNAME.string.strip())
					if party_details:
						party_type, party_account = party_details
						account["party_type"] = party_type
						account["account"] = party_account
						account["party"] = entry.LEDGERNAME.string.strip()
				amount = Decimal(entry.AMOUNT.string.strip())
				if amount > 0:
					account["credit_in_account_currency"] = str(abs(amount))
				else:
					account["debit_in_account_currency"] = str(abs(amount))
				accounts.append(account)

			journal_entry = {
				"doctype": "Journal Entry",
				"tally_guid": voucher.GUID.string.strip(),
				"tally_voucher_no": voucher.VOUCHERNUMBER.string.strip() if voucher.VOUCHERNUMBER else "",
				"posting_date": voucher.DATE.string.strip(),
				"company": self.erpnext_company,
				"accounts": accounts,
			}
			return journal_entry

		def voucher_to_invoice(voucher):
			if voucher.VOUCHERTYPENAME.string.strip() in ["Sales", "Credit Note"]:
				doctype = "Sales Invoice"
				party_field = "customer"
				account_field = "debit_to"
				account_name = encode_company_abbr(self.tally_debtors_account, self.erpnext_company)
				price_list_field = "selling_price_list"
			elif voucher.VOUCHERTYPENAME.string.strip() in ["Purchase", "Debit Note"]:
				doctype = "Purchase Invoice"
				party_field = "supplier"
				account_field = "credit_to"
				account_name = encode_company_abbr(self.tally_creditors_account, self.erpnext_company)
				price_list_field = "buying_price_list"
			else:
				# Do not handle vouchers other than "Purchase", "Debit Note", "Sales" and "Credit Note"
				# Do not handle Custom Vouchers either
				return

			invoice = {
				"doctype": doctype,
				party_field: voucher.PARTYNAME.string.strip(),
				"tally_guid": voucher.GUID.string.strip(),
				"tally_voucher_no": voucher.VOUCHERNUMBER.string.strip() if voucher.VOUCHERNUMBER else "",
				"posting_date": voucher.DATE.string.strip(),
				"due_date": voucher.DATE.string.strip(),
				"items": get_voucher_items(voucher, doctype),
				"taxes": get_voucher_taxes(voucher),
				account_field: account_name,
				price_list_field: "Tally Price List",
				"set_posting_time": 1,
				"disable_rounded_total": 1,
				"company": self.erpnext_company,
			}
			return invoice

		def get_voucher_items(voucher, doctype):
			inventory_entries = voucher.find_all("INVENTORYENTRIES.LIST") + voucher.find_all("ALLINVENTORYENTRIES.LIST") + voucher.find_all("INVENTORYENTRIESIN.LIST") + voucher.find_all("INVENTORYENTRIESOUT.LIST")
			if doctype == "Sales Invoice":
				account_field = "income_account"
			elif doctype == "Purchase Invoice":
				account_field = "expense_account"
			items = []
			for entry in inventory_entries:
				qty, uom = entry.ACTUALQTY.string.strip().split()
				items.append({
					"item_code": entry.STOCKITEMNAME.string.strip(),
					"description": entry.STOCKITEMNAME.string.strip(),
					"qty": qty.strip(),
					"uom": uom.strip(),
					"conversion_factor": 1,
					"price_list_rate": entry.RATE.string.strip().split("/")[0],
					"cost_center": self.default_cost_center,
					"warehouse": self.default_warehouse,
					account_field: encode_company_abbr(entry.find_all("ACCOUNTINGALLOCATIONS.LIST")[0].LEDGERNAME.string.strip(), self.erpnext_company),
				})
			return items

		def get_voucher_taxes(voucher):
			ledger_entries = voucher.find_all("ALLLEDGERENTRIES.LIST") + voucher.find_all("LEDGERENTRIES.LIST")
			taxes = []
			for entry in ledger_entries:
				if entry.ISPARTYLEDGER.string.strip() == "No":
					tax_account = encode_company_abbr(entry.LEDGERNAME.string.strip(), self.erpnext_company)
					taxes.append({
						"charge_type": "Actual",
						"account_head": tax_account,
						"description": tax_account,
						"tax_amount": entry.AMOUNT.string.strip(),
						"cost_center": self.default_cost_center,
					})
			return taxes

		def get_party(party):
			if frappe.db.exists({"doctype": "Supplier", "supplier_name": party}):
				return "Supplier", encode_company_abbr(self.tally_creditors_account, self.erpnext_company)
			elif frappe.db.exists({"doctype": "Customer", "customer_name": party}):
				return "Customer", encode_company_abbr(self.tally_debtors_account, self.erpnext_company)

		try:
			self.publish("Process Day Book Data", _("Reading Uploaded File"), 1, 3)
			collection = self.get_collection(self.day_book_data)

			self.publish("Process Day Book Data", _("Processing Vouchers"), 2, 3)
			vouchers = get_vouchers(collection)

			self.publish("Process Day Book Data", _("Done"), 3, 3)
			self.dump_processed_data({"vouchers": vouchers})

			self.is_day_book_data_processed = 1

		except:
			self.publish("Process Day Book Data", _("Process Failed"), -1, 5)
			self.log()

		finally:
			self.set_status()

	def _import_day_book_data(self):
		def create_fiscal_years(vouchers):
			from frappe.utils.data import add_years, getdate
			earliest_date = getdate(min(voucher["posting_date"] for voucher in vouchers))
			oldest_year = frappe.get_all("Fiscal Year", fields=["year_start_date", "year_end_date"], order_by="year_start_date")[0]
			while earliest_date < oldest_year.year_start_date:
				new_year = frappe.get_doc({"doctype": "Fiscal Year"})
				new_year.year_start_date = add_years(oldest_year.year_start_date, -1)
				new_year.year_end_date = add_years(oldest_year.year_end_date, -1)
				if new_year.year_start_date.year == new_year.year_end_date.year:
					new_year.year = new_year.year_start_date.year
				else:
					new_year.year = "{}-{}".format(new_year.year_start_date.year, new_year.year_end_date.year)
				new_year.save()
				oldest_year = new_year

		def create_custom_fields(doctypes):
			tally_guid_df = {
				"fieldtype": "Data",
				"fieldname": "tally_guid",
				"read_only": 1,
				"label": "Tally GUID"
			}
			tally_voucher_no_df = {
				"fieldtype": "Data",
				"fieldname": "tally_voucher_no",
				"read_only": 1,
				"label": "Tally Voucher Number"
			}
			for df in [tally_guid_df, tally_voucher_no_df]:
				for doctype in doctypes:
					create_custom_field(doctype, df)

		def create_price_list():
			frappe.get_doc({
				"doctype": "Price List",
				"price_list_name": "Tally Price List",
				"selling": 1,
				"buying": 1,
				"enabled": 1,
				"currency": "INR"
			}).insert()

		try:
			frappe.db.set_value("Account", encode_company_abbr(self.tally_creditors_account, self.erpnext_company), "account_type", "Payable")
			frappe.db.set_value("Account", encode_company_abbr(self.tally_debtors_account, self.erpnext_company), "account_type", "Receivable")
			frappe.db.set_value("Company", self.erpnext_company, "round_off_account", self.default_round_off_account)

			vouchers_file = frappe.get_doc("File", {"file_url": self.vouchers})
			vouchers = json.loads(vouchers_file.get_content())

			create_fiscal_years(vouchers)
			create_price_list()
			create_custom_fields(["Journal Entry", "Purchase Invoice", "Sales Invoice"])

			total = len(vouchers)
			is_last = False

			for index in range(0, total, VOUCHER_CHUNK_SIZE):
				if index + VOUCHER_CHUNK_SIZE >= total:
					is_last = True
				frappe.enqueue_doc(self.doctype, self.name, "_import_vouchers", queue="long", timeout=3600, start=index+1, total=total, is_last=is_last)

		except:
			self.log()

		finally:
			self.set_status()

	def _import_vouchers(self, start, total, is_last=False):
		frappe.flags.in_migrate = True
		vouchers_file = frappe.get_doc("File", {"file_url": self.vouchers})
		vouchers = json.loads(vouchers_file.get_content())
		chunk = vouchers[start: start + VOUCHER_CHUNK_SIZE]

		for index, voucher in enumerate(chunk, start=start):
			try:
				voucher_doc = frappe.get_doc(voucher)
				voucher_doc.insert()
				voucher_doc.submit()
				self.publish("Importing Vouchers", _("{} of {}").format(index, total), index, total)
				frappe.db.commit()
			except:
				frappe.db.rollback()
				self.log(voucher_doc)

		if is_last:
			self.status = ""
			self.is_day_book_data_imported = 1
			self.save()
			frappe.db.set_value("Price List", "Tally Price List", "enabled", 0)
		frappe.flags.in_migrate = False

	def process_master_data(self):
		self.set_status("Processing Master Data")
		frappe.enqueue_doc(self.doctype, self.name, "_process_master_data", queue="long", timeout=3600)

	def import_master_data(self):
		self.set_status("Importing Master Data")
		frappe.enqueue_doc(self.doctype, self.name, "_import_master_data", queue="long", timeout=3600)

	def process_day_book_data(self):
		self.set_status("Processing Day Book Data")
		frappe.enqueue_doc(self.doctype, self.name, "_process_day_book_data", queue="long", timeout=3600)

	def import_day_book_data(self):
		self.set_status("Importing Day Book Data")
		frappe.enqueue_doc(self.doctype, self.name, "_import_day_book_data", queue="long", timeout=3600)

	def log(self, data=None):
		if isinstance(data, frappe.model.document.Document):
			if sys.exc_info()[1].__class__ != frappe.DuplicateEntryError:
				failed_import_log = json.loads(self.failed_import_log)
				doc = data.as_dict()
				failed_import_log.append({
					"doc": doc,
					"exc": traceback.format_exc()
				})
				self.failed_import_log = json.dumps(failed_import_log, separators=(',', ':'))
				self.save()
				frappe.db.commit()

		else:
			data = data or self.status
			message = "\n".join(["Data:", json.dumps(data, default=str, indent=4), "--" * 50, "\nException:", traceback.format_exc()])
			return frappe.log_error(title="Tally Migration Error", message=message)

	def set_status(self, status=""):
		self.status = status
		self.save()


def convert_fieldnames_to_labels(labelled_docs, doctype, docs):
	'''Converts fieldnames to field labels for easier csv header creation. Also helps in mapping data to proper columns.'''
	meta = frappe.get_meta(doctype)
	for doc in docs:
		labelled_doc = {}
		for fieldname, value in doc.items():
			if fieldname == "doctype": continue

			label = meta.get_label(fieldname)
			if isinstance(value, list) and value:
				labelled_child_docs = convert_fieldnames_to_labels([], meta.get_options(fieldname), value)
				labelled_doc[label] = labelled_child_docs
				continue
			labelled_doc[label] = doc[fieldname]
		labelled_docs.append(labelled_doc)
	return labelled_docs

def make_header(header, labelled_docs, parent_label=None):
	'''loop over every doc and child doc and extract unique labels (columns)'''
	for doc in labelled_docs:
		for label, value in doc.items():
			if label == "doctype": continue

			is_list = type(value) is list
			col = "{} ({})".format(label, parent_label) if parent_label else label
			if not is_list and col not in header:
				header.append(col)
			elif is_list and value:
				make_header(header, value, label)

	return ["ID"] + header

def make_csv_rows_from_doc(header, doc, has_tables=False):
	def get_single_row(doc):
		row = ['' for d in header] # make empty row
		for i, col in enumerate(header):
			if doc.get(col):
				row[i] = doc[col] # put doc value at proper header column
		return row

	if not has_tables:
		return [get_single_row(doc)]

	docs = split_nested_doc(doc)
	rows = []
	for d in docs:
		rows.append(get_single_row(d))
	return rows

def split_nested_doc(doc):
	dict_rows = [{}] # doc will be splitted into multiple dicts depening upon child items
	child_tables = [label for label, value in doc.items() if isinstance(value, list) and len(value) > 1]

	#make first row
	for label, value in doc.items():
		dict_row_one = dict_rows[0]
		if isinstance(value, list) and value:
			for child_label, child_value in value[0].items(): # only append values from first row of every child table
				header_label = "{} ({})".format(child_label, label)
				dict_row_one[header_label] = child_value
		else:
			dict_row_one[label] = value

	# loop over child tables in the doc and make new dict for each row
	for parent_label in child_tables:
		child_docs = doc[parent_label][1:] # skip first row
		for child_doc in child_docs:
			dict_row = {}
			for child_label, child_value in child_doc.items():
				header_label = "{} ({})".format(child_label, parent_label)
				dict_row[header_label] = child_value
			dict_rows.append(row)

	return dict_rows

def make_csv_for_data_import(doctype, docs):
	labelled_docs = convert_fieldnames_to_labels([], doctype, docs)
	header = make_header([], labelled_docs)
	has_tables = any([d for d in header if '(' in d])

	csv_array = [header]
	for doc in labelled_docs:
		csv_array += make_csv_rows_from_doc(header, doc, has_tables)

	csv_content = cstr(to_csv(csv_array))

	return csv_content