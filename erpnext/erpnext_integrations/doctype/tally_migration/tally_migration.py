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
from frappe.utils.data import format_datetime, cint, flt
from frappe.utils import cstr
from frappe.utils.csvutils import to_csv

PRIMARY_ACCOUNT = "Primary"
CHUNK_SIZE = 500


@frappe.whitelist()
def new_doc(document):
	document = json.loads(document)
	doctype = document.pop("doctype")
	document.pop("name", None)
	doc = frappe.new_doc(doctype)
	doc.update(document)

	return doc

def get_pincode_city_map():
	with open(os.path.join(os.path.dirname(__file__), "pincode_info.json"), "r") as f:
		return json.loads(f.read())

class TallyMigration(Document):
	def validate(self):
		pass

	def autoname(self):
		if not self.name:
			self.name = "Tally Migration on " + format_datetime(self.creation)
	
	def fetch_xml(self, data_file):
		def sanitize(string):
			return re.sub("&#4;", "", string)

		def emptify(string):
			string = re.sub(r"<\w+/>", "", string)
			string = re.sub(r"<([\w.]+)>\s*<\/\1>", "", string)
			string = re.sub(r"\r\n", "", string)
			return string

		zip_file = frappe.get_doc("File", {"file_url": data_file})
		zip_file_path = zip_file.get_full_path()

		if zipfile.is_zipfile(zip_file_path):
			with zipfile.ZipFile(zip_file_path) as zf:
				encoded_content = zf.read(zf.namelist()[0])
				try:
					content = encoded_content.decode("utf-8-sig")
				except UnicodeDecodeError:
					content = encoded_content.decode("utf-16")

		xml = bs(sanitize(emptify(content)), "xml")
		return xml

	def get_collection(self, data_file):
		xml = self.fetch_xml(data_file)
		collection = xml.BODY.IMPORTDATA.REQUESTDATA
		return collection

	def dump_processed_data(self, data, filename):
		f = frappe.get_doc({
			"doctype": "File",
			"file_name": filename + ".json",
			"attached_to_doctype": self.doctype,
			"attached_to_name": self.name,
			"content": json.dumps(data),
			"is_private": True
		})
		try:
			f.insert()
			f.reload()
		except frappe.DuplicateEntryError:
			pass
		return f.name
	
	def fetch_processed_data(self, filename):
		file = frappe.get_doc("File", filename)
		content = file.get_content()
		return json.loads(content)

	def _process_master_data(self):
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
				return "", ""
			
			def get_party_doc(party_type, party, account):
				if party_type == "Customer":
					return {
						"doctype": party_type,
						"customer_name": party,
						"tax_id": account.INCOMETAXNUMBER.string.strip() if account.INCOMETAXNUMBER else None,
						"customer_group": "All Customer Groups",
						"territory": "All Territories",
						"customer_type": "Individual",
					}
				else:
					return {
						"doctype": party_type,
						"supplier_name": party,
						"pan": account.INCOMETAXNUMBER.string.strip() if account.INCOMETAXNUMBER else None,
						"supplier_group": "All Supplier Groups",
						"supplier_type": "Individual",
					}

			def get_address_doc(account, links):
				tally_state = account.LEDSTATENAME.string.strip().title().replace('&', 'and') if account.LEDSTATENAME else ""
				pincode = account.PINCODE.string.strip() if account.PINCODE else ""
				city, pincode_state = "", ""
				if pincode:
					pincode = str(pincode).replace("-", "").replace(" ", "")
					city, pincode_state = get_city_state_from_pincode(cint(pincode))

				address = "\n".join([a.string.strip() for a in account.find_all("ADDRESS")])
				return {
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
					"links": links,
					"flags": { "ignore_mandatory": True }
				}

			customers, suppliers, addresses = [], [], []
			for account in collection.find_all("LEDGER"):
				party, party_type, links = None, None, []
				party = account.NAME.string.strip()

				if party in customer_ledgers:
					party_type = "Customer"
					customer_doc = get_party_doc(party_type, party, account)
					customers.append(customer_doc)
					links.append({"link_doctype": party_type, "link_name": party})

				if party in supplier_ledgers:
					party_type = "Supplier"
					supplier_doc = get_party_doc(party_type, party, account)
					suppliers.append(supplier_doc)
					links.append({"link_doctype": party_type, "link_name": party})

				if party_type:
					address_doc = get_address_doc(account, links)
					addresses.append(address_doc)

			return customers, suppliers, addresses

		def get_item_groups(collection):
			root = "All Item Groups"
			item_groups = []

			for item_group in collection.find_all("STOCKGROUP"):
				group_name = item_group.NAME.string.strip().title()
				parent = item_group.PARENT.string.strip().title() if item_group.PARENT else root

				if parent != root:
					for d in item_groups:
						if d.get("item_group_name") == group_name:
							d.setdefault("is_group", 1)
							break

				item_groups.append({
					"doctype": "Item Group",
					"item_group_name": group_name,
					"parent_item_group": parent
				})

			return item_groups

		def get_stock_items_uoms(collection):
			uoms = []
			for uom in collection.find_all("UNIT"):
				uoms.append({"doctype": "UOM", "uom_name": uom.NAME.string.strip().title()})

			items = []
			for item in collection.find_all("STOCKITEM"):
				stock_uom = item.BASEUNITS.string.strip().title() if item.BASEUNITS else self.default_uom
				items.append({
					"doctype": "Item",
					"item_code" : item.NAME.string.strip(),
					"stock_uom": stock_uom.strip(),
					"is_stock_item": 1,
					"item_group": item.PARENT.string.strip().title() if item.PARENT else "All Item Groups",
					"item_defaults": [{"company": self.erpnext_company}]
				})

			return items, uoms

		try:
			self.publish(_("Reading Uploaded File"), 0, 4)
			collection = self.get_collection(self.master_data)

			self.publish(_("Processing Chart of Accounts and Parties"), 1, 4)
			chart_of_accounts, customer_ledgers, supplier_ledgers = get_coa_customers_suppliers(collection)

			self.publish(_("Processing Party Addresses"), 2, 4)
			customers, suppliers, addresses = get_parties_addresses(collection, customer_ledgers, supplier_ledgers)

			self.publish(_("Processing Items, Groups and UOMs"), 3, 4)
			items, uoms = get_stock_items_uoms(collection)
			item_groups = get_item_groups(collection)

			data = uoms + item_groups + items + customers + suppliers + addresses

			coa_file = self.dump_processed_data(chart_of_accounts, filename="chart_of_accounts")
			master_file = self.dump_processed_data(data, filename="masters")

			self.update_field("chart_of_accounts", coa_file)
			self.update_field("masters", master_file)
			self.update_field("is_master_data_processed", 1)

			self.publish(_("Done"), 4, 4)

		except:
			self.publish(_("Process Failed"), -1, 4)
			frappe.db.rollback()
			self.log()

		finally:
			self.set_status()
	
	def import_coa(self):
		coa = self.fetch_processed_data(self.chart_of_accounts)
		company = frappe.get_doc("Company", self.erpnext_company)

		frappe.local.flags.ignore_chart_of_accounts = True
		unset_existing_data(self.erpnext_company)
		create_charts(company.name, custom_chart=coa)
		company.on_update()
		company.validate()
		frappe.local.flags.ignore_chart_of_accounts = False

	def _import_master_data(self):
		try:
			if not self.is_chart_of_accounts_imported:
				self.publish(_("Importing Chart of Accounts"), 0, 100)
				self.import_coa()
				self.update_field("is_chart_of_accounts_imported", 1)

			masters = self.fetch_processed_data(self.masters)
			self.enqueue_import(masters)

		except:
			self.publish(_("Process Failed"), -1, 100)
			frappe.db.rollback()
			self.log()

		finally:
			self.set_status()
	
	def after_master_data_import(self):
		self.default_cost_center, self.default_round_off_account = frappe.db.get_value("Company", self.erpnext_company, ["cost_center", "round_off_account"])
		self.default_warehouse = frappe.db.get_value("Stock Settings", "Stock Settings", "default_warehouse")
		self.update_field("is_master_data_imported", 1)

	def get_opening_entry(self, trial_balance_report):
		ledgers = trial_balance_report.find_all('DSPDISPNAME')
		credit_amounts = trial_balance_report.find_all('DSPCLCRAMT')
		debit_amounts = trial_balance_report.find_all('DSPCLDRAMT')

		jv_accounts = []
		for idx, ledger in enumerate(ledgers):
			if ledger.string.strip() == 'Opening Stock':
				continue
			
			account_name = encode_company_abbr(ledger.string.strip(), self.erpnext_company)
			cr_amount = Decimal(credit_amounts[idx].get_text().strip() or 0)
			dr_amount = Decimal(debit_amounts[idx].get_text().strip() or 0)
			row = {
				"account": account_name,
				"cost_center": self.default_cost_center,
				"credit_in_account_currency": str(abs(cr_amount)),
				"debit_in_account_currency": str(abs(dr_amount))
			}
			party_details = self.get_party(ledger.string.strip())
			if party_details:
				party_type, party_account = party_details
				row["party_type"] = party_type
				row["account"] = party_account
				row["party"] = ledger.string.strip()

			jv_accounts.append(row)

		journal_entry = {
			"doctype": "Journal Entry",
			"title": "Tally Opening Balance",
			"voucher_type": "Opening Entry",
			"is_opening": "Yes",
			"posting_date": frappe.utils.now(), # TODO
			"company": self.erpnext_company,
			"accounts": jv_accounts,
		}
		return journal_entry
	
	def voucher_to_journal_entry(self, voucher):
		accounts = []
		ledger_entries = voucher.find_all("ALLLEDGERENTRIES.LIST") + voucher.find_all("LEDGERENTRIES.LIST")
		for entry in ledger_entries:
			account = {
				"account": encode_company_abbr(entry.LEDGERNAME.string.strip(), self.erpnext_company),
				"cost_center": self.default_cost_center
			}
			if entry.ISPARTYLEDGER.string.strip() == "Yes":
				party_details = self.get_party(entry.LEDGERNAME.string.strip())
				if party_details:
					party_type, party_account = party_details
					account["party_type"] = party_type
					account["account"] = party_account
					account["party"] = entry.LEDGERNAME.string.strip()
			
			amount = entry.AMOUNT.string.strip()
			if '@' in amount:
				# eg. "-JPY363953.00 @ ₹ 0.6931/JPY = -₹ 252255.82"
				amount = amount.split("=")[-1].strip().replace("₹ ", "") # handle multicurrency

			amount = Decimal(amount)
			cr_or_dr = "debit_in_account_currency" if amount < 0 else "credit_in_account_currency"
			account[cr_or_dr] = str(abs(amount))
			accounts.append(account)
		
		if not accounts:
			return {}

		journal_entry = {
			"doctype": "Journal Entry",
			"tally_guid": voucher.GUID.string.strip(),
			"tally_voucher_no": voucher.VOUCHERNUMBER.string.strip() if voucher.VOUCHERNUMBER else "",
			"posting_date": voucher.DATE.string.strip(),
			"company": self.erpnext_company,
			"accounts": accounts,
		}
		return journal_entry

	def voucher_to_invoice(self, voucher):
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
			"items": self.get_voucher_items(voucher, doctype),
			"taxes": self.get_voucher_taxes(voucher),
			account_field: account_name,
			price_list_field: "Tally Price List",
			"set_posting_time": 1,
			"disable_rounded_total": 1,
			"company": self.erpnext_company,
		}
		return invoice

	def get_voucher_items(self, voucher, doctype):
		inventory_entries = voucher.find_all("INVENTORYENTRIES.LIST") + voucher.find_all("ALLINVENTORYENTRIES.LIST") + voucher.find_all("INVENTORYENTRIESIN.LIST") + voucher.find_all("INVENTORYENTRIESOUT.LIST")
		if doctype == "Sales Invoice":
			account_field = "income_account"
		elif doctype == "Purchase Invoice":
			account_field = "expense_account"
		items = []
		for entry in inventory_entries:
			item_code = entry.STOCKITEMNAME.string.strip()
			if entry.ACTUALQTY:
				qty, uom = entry.ACTUALQTY.string.strip().split()
			else:
				qty, uom = "1", frappe.db.get_value("Item", item_code, "stock_uom")
			items.append({
				"item_code": item_code,
				"item_name": item_code,
				"description": item_code,
				"qty": qty.strip(),
				"uom": uom.strip().title(),
				"conversion_factor": 1,
				"rate": entry.RATE.string.strip().split("/")[0],
				"price_list_rate": entry.RATE.string.strip().split("/")[0],
				"cost_center": self.default_cost_center,
				"warehouse": self.default_warehouse,
				account_field: encode_company_abbr(entry.find_all("ACCOUNTINGALLOCATIONS.LIST")[0].LEDGERNAME.string.strip(), self.erpnext_company),
			})
		return items

	def get_voucher_taxes(self, voucher):
		ledger_entries = voucher.find_all("ALLLEDGERENTRIES.LIST") + voucher.find_all("LEDGERENTRIES.LIST")
		taxes = []
		for entry in ledger_entries:
			if entry.ISPARTYLEDGER.string.strip() == "No":
				tax_account = encode_company_abbr(entry.LEDGERNAME.string.strip(), self.erpnext_company)
				tax_amount = Decimal(entry.AMOUNT.string.strip()) if entry.AMOUNT else 0
				taxes.append({
					"charge_type": "Actual",
					"category": "Total",
					"add_deduct_tax": "Add",
					"account_head": tax_account,
					"description": tax_account,
					"rate": 0,
					"tax_amount": str(abs(tax_amount)),
					"cost_center": self.default_cost_center,
				})
		return taxes

	def get_party(self, party):
		if frappe.db.exists({"doctype": "Supplier", "supplier_name": party}):
			return "Supplier", encode_company_abbr(self.tally_creditors_account, self.erpnext_company)
		elif frappe.db.exists({"doctype": "Customer", "customer_name": party}):
			return "Customer", encode_company_abbr(self.tally_debtors_account, self.erpnext_company)

	def get_vouchers(self, day_book_data):
		vouchers = []
		invalid_vouchers = []
		for voucher in day_book_data.find_all("VOUCHER"):
			if voucher.ISCANCELLED.string.strip() == "Yes":
				continue
			inventory_entries = voucher.find_all("INVENTORYENTRIES.LIST") + voucher.find_all("ALLINVENTORYENTRIES.LIST") + voucher.find_all("INVENTORYENTRIESIN.LIST") + voucher.find_all("INVENTORYENTRIESOUT.LIST")
			if voucher.VOUCHERTYPENAME.string.strip() not in ["Journal", "Receipt", "Payment", "Contra"] and inventory_entries:
				function = self.voucher_to_invoice
			else:
				function = self.voucher_to_journal_entry
			try:
				processed_voucher = function(voucher)
				if processed_voucher:
					vouchers.append(processed_voucher)
				else:
					invalid_vouchers.append(voucher)
			except:
				self.log(voucher)
				raise

		return vouchers, invalid_vouchers

	def log_invalid_vouchers(self, vouchers):
		[self.log(d) for d in vouchers]

	def _process_day_book_data(self):
		try:
			self.publish(_("Reading Trial Balance Report"), 1, 5)
			trial_balance_report = self.fetch_xml(self.trial_balance_report)

			self.publish(_("Processing Trial Balance Report"), 2, 5)
			opening_entry = self.get_opening_entry(trial_balance_report)

			self.publish(_("Reading Day Book Data"), 2, 5)
			day_book_data = self.get_collection(self.day_book_data)

			self.publish(_("Processing Vouchers"), 4, 5)
			vouchers, invalid_vouchers = self.get_vouchers(day_book_data)

			self.log_invalid_vouchers(invalid_vouchers)

			data = [opening_entry] + vouchers
			voucher_file = self.dump_processed_data(data, filename="vouchers")

			self.update_field("vouchers", voucher_file)
			self.update_field("is_day_book_data_processed", 1)

			self.publish(_("Done"), 5, 5)

		except:
			self.publish(_("Process Failed"), -1, 5)
			frappe.db.rollback()
			self.log()

		finally:
			self.set_status()
	
	def adjust_difference_with_temporary_opening(self, jv):
		total_debit = sum([Decimal(d["debit_in_account_currency"]) for d in jv.get("accounts")])
		total_credit = sum([Decimal(d["credit_in_account_currency"]) for d in jv.get("accounts")])

		difference = flt(total_debit - total_credit, 2)
		if difference:
			temporary_opening_acc = encode_company_abbr("Temporary Opening", self.erpnext_company)
			if not frappe.db.exists("Account", temporary_opening_acc):
				frappe.get_doc({
					"doctype": "Account",
					"company": self.erpnext_company,
					"account_name": "Temporary Opening",
					"account_type": "Temporary",
					"is_group": 0,
					"report_type": "Balance Sheet",
					"root_type": "Asset",
					"parent_account": encode_company_abbr("Application of Funds (Assets)", self.erpnext_company)
				}).insert()

			row = {
				"account": temporary_opening_acc,
				"cost_center": self.default_cost_center
			}
			amount = Decimal(difference)
			cr_or_dr = "debit_in_account_currency" if amount < 0 else "credit_in_account_currency"
			row[cr_or_dr] = str(abs(amount))
			jv.get('accounts').append(row)

		return jv
	
	def import_opening_balances(self, entry):
		try:
			entry = self.adjust_difference_with_temporary_opening(entry)
			jv = frappe.get_doc(entry)
			jv.insert()
			jv.submit()
			self.update_field("is_opening_balances_imported", 1)
		except:
			frappe.db.rollback()
			self.log(entry)
			raise

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

		def before_day_book_data_import():
			self.update_field("error_log", "[]")
			creditors = encode_company_abbr(self.tally_creditors_account, self.erpnext_company)
			debtors = encode_company_abbr(self.tally_debtors_account, self.erpnext_company)

			frappe.db.set_value("Account", creditors, "account_type", "Payable")
			frappe.db.set_value("Account", debtors, "account_type", "Receivable")
			company = frappe.get_doc("Company", self.erpnext_company)
			company.round_off_account = self.default_round_off_account
			company.enable_perpetual_inventory = 0

			exp_included_in_val = encode_company_abbr("Expenses Included In Valuation", self.erpnext_company)
			if not frappe.db.exists("Account", exp_included_in_val):
				accounts = [
					["Direct Expenses", "Expenses", 1],
					["Stock Expenses", "Direct Expenses", 1],
					["Expenses Included In Valuation", "Stock Expenses", 0]
				]
				for acc in accounts:
					frappe.get_doc({
						"doctype": "Account",
						"company": self.erpnext_company,
						"account_name": acc[0],
						"is_group": acc[2],
						"report_type": "Profit and Loss",
						"root_type": "Expense",
						"parent_account": encode_company_abbr(acc[1], self.erpnext_company)
					}).insert(ignore_if_duplicate=True)

				company.expenses_included_in_valuation = exp_included_in_val

			company.save()

			# create_fiscal_years(vouchers)
			create_custom_fields(["Journal Entry", "Purchase Invoice", "Sales Invoice"])
			create_price_list()

		def is_price_list_created():
			return frappe.db.exists("Price List", {"price_list_name": "Tally Price List"})

		try:
			if not is_price_list_created(): # check if `before_day_book_data_import` has already executed
				before_day_book_data_import()

			vouchers = self.fetch_processed_data(self.vouchers)
			if not self.is_opening_balances_imported:
				self.publish(_("Importing Opening Balances"), 0, 100)
				self.import_opening_balances(vouchers[0])

			self.enqueue_import(vouchers[1:])

		except:
			self.publish(_("Process Failed"), -1, 100)
			frappe.db.rollback()
			self.log()

		finally:
			self.set_status()
	
	def enqueue_import(self, payload):
		total = len(payload)
		is_last = False

		for index in range(0, total, CHUNK_SIZE):
			if index + CHUNK_SIZE >= total:
				is_last = True

			frappe.enqueue_doc(
				self.doctype, self.name, "start_import",
				queue="long", timeout=3600, data=payload,
				start=index+1, is_last=is_last
			)
	
	def get_dependencies(self, doctype):
		return {
			"Item": set(("UOM", "Item Group")),
			"Address": set(("Customer", "Supplier"))
		}.get(doctype, set())
	
	def start_import(self, data, start, is_last):
		frappe.flags.in_migrate = True
		chunk = data[start: start + CHUNK_SIZE]

		skipped_docs = self.fetch_processed_data(self.skipped_docs) if self.skipped_docs else []
		error_log = json.loads(self.error_log)
		failed_log = [d for d in error_log if d["status"] == "Failed"]
		progress_total = len(data)

		for i, doc in enumerate(chunk, start=start):
			try:
				doctype = doc['doctype']
				dependent_on = self.get_dependencies(doctype)
				failed_doctypes = set([d["doc"]["doctype"] for d in failed_log])

				if dependent_on & failed_doctypes:
					 # if curr doctype is dependent on failed doctype then skip
					skipped_docs.append(doc)
					self.publish(_("Skipping {}").format(doctype), i + 1, progress_total)
					continue
				
				self.publish(_("Importing {}").format(doctype), i + 1, progress_total)

				flags = doc.pop("flags") if doc.get("flags") else {}
				d = frappe.get_doc(doc)
				d.flags.update(flags)
				d.insert()
				if d.meta.is_submittable:
					d.submit()

				frappe.db.commit()

			except Exception as e:
				frappe.db.rollback()
				error = str(e)

				if len(e.args) == 3 and frappe.db.is_unique_key_violation(e.args[2]):
					error = _("{0} named {1} already exists").format(doctype, frappe.bold(d.name))

				error_log.append({ "doc": doc, "error": error, "status": "Failed" })

		self.update_field("error_log", json.dumps(error_log))
		if skipped_docs:
			remaining_docs = self.dump_processed_data(skipped_docs, "skipped_docs")
			self.update_field("skipped_docs", remaining_docs)

		if is_last:
			remaining_docs = self.dump_processed_data(skipped_docs, "skipped_docs")
			self.update_field("skipped_docs", remaining_docs)
			self.finish_import(skipped_docs)

		frappe.flags.in_migrate = False

	def finish_import(self, skipped_docs):
		if not self.is_master_data_imported:
			remaining_masters = self.dump_processed_data(skipped_docs, "masters")
			self.update_field("masters", remaining_masters)

			if not skipped_docs:
				self.publish(_("Master Data Import Complete"), 1, 1)
				self.after_master_data_import()
			else:
				self.publish(_("Resolve Errors and Try Again"), -1, 1)

		else:
			remaining_vouchers = self.dump_processed_data(skipped_docs, "vouchers")
			self.update_field("vouchers", remaining_vouchers)

			if not skipped_docs:
				self.publish(_("Day Book Data Import Complete"), 1, 1)
				self.after_day_book_data_import()
			else:
				self.publish(_("Resolve Errors and Try Again"), -1, 1)
	
	def publish(self, message, progress, total):
		frappe.publish_realtime("tally_migration_progress_update", {
			"title": "Tally Migration",
			"progress": progress,
			"total": total,
			"user": frappe.session.user,
			"message": message
		})
	
	def set_status(self, status=""):
		self.update_field("status", status)

	def update_field(self, field, value):
		self.db_set(field, value, update_modified=False, commit=True)
	
	def after_day_book_data_import(self):
		self.status = ""
		self.is_day_book_data_imported = 1
		self.save()
		frappe.db.set_value("Price List", "Tally Price List", "enabled", 0)

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
		data = data or self.status
		tb = traceback.format_exc()
		error_msg = frappe.bold(str(sys.exc_info()[1]))

		message = "\n".join([
			f"Error: {error_msg}",
			"--" * 50,
			"Data:", json.dumps(data, default=str, indent=4),
			"--" * 50,
			"\nException:", tb
		])
		frappe.log_error(title="Tally Migration Error", message=message)
		frappe.db.commit()