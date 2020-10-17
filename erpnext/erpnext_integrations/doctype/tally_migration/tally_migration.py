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
	with open(os.path.join(os.path.dirname(__file__), "pincode_info.json"), "r") as f:
		return json.loads(f.read())

class TallyMigration(Document):
	def validate(self):
		pass

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

	def set_account_defaults(self):
		self.default_cost_center, self.default_round_off_account = frappe.db.get_value("Company", self.erpnext_company, ["cost_center", "round_off_account"])
		self.default_warehouse = frappe.db.get_value("Stock Settings", "Stock Settings", "default_warehouse")

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

					pincode = account.PINCODE.string.strip() if account.PINCODE else ""
					city, pincode_state = "", ""
					if pincode:
						pincode = str(pincode).replace("-", "").replace(" ", "")
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
						"links": links,
						"flags": { "ignore_mandatory": True }
					})
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

			self.publish(_("Processing Items, UOMs and Groups"), 3, 4)
			items, uoms = get_stock_items_uoms(collection)
			item_groups = get_item_groups(collection)

			data = uoms + item_groups + items[:100] + customers + suppliers + addresses[:20]

			coa = self.dump_processed_data(chart_of_accounts, filename="chart_of_accounts")
			masters = self.dump_processed_data(data, filename="masters")

			self.publish(_("Done"), 4, 4)

			self.update_field("chart_of_accounts", coa)
			self.update_field("masters", masters)
			self.update_field("payload_length", len(data))
			self.update_field("is_master_data_processed", 1)

		except:
			self.publish(_("Process Failed"), -1, 4)
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

		self.update_field("is_chart_of_accounts_imported", 1)

	def _import_master_data(self):
		try:
			progress_total = self.payload_length + 1

			if not self.is_chart_of_accounts_imported:
				self.publish(_("Importing Chart of Accounts"), 0, progress_total)
				self.import_coa()

			masters = self.fetch_processed_data(self.masters)
			skipped_docs, error_log = self.start_import(masters)

			remaining_masters = self.dump_processed_data(skipped_docs, "masters")
			self.update_field("masters", remaining_masters)
			self.update_field("payload_length", len(skipped_docs))

			if not skipped_docs and not error_log:
				self.publish(_("Master Data Import Complete"), 1, 1)
				self.after_master_data_import()
			else:
				self.publish(_("Resolve Errors and Try Again"), 1, 1)

		except:
			self.publish(_("Process Failed"), -1, progress_total)
			frappe.db.rollback()
			self.log()

		finally:
			self.set_status()
	
	def after_master_data_import(self):
		self.set_account_defaults()
		self.update_field("is_master_data_imported", 1)
	
	def get_dependencies(self, doctype):
		return {
			"Item": set(("UOM", "Item Group")),
			"Address": set(("Customer", "Supplier"))
		}.get(doctype, set())
	
	def start_import(self, data):
		error_log = json.loads(self.error_log)
		error_log = [d for d in error_log if d["status"] == "Failed"]
		progress_total = len(data)
		skipped_docs = []

		for i, doc in enumerate(data):
			try:
				doctype = doc['doctype']
				dependent_on = self.get_dependencies(doctype)
				errored_doctypes = set([d["doc"]["doctype"] for d in error_log])

				if dependent_on & errored_doctypes:
					skipped_docs.append(doc)
					self.publish(_("Skipping {}").format(doctype), i + 1, progress_total)
					continue
				
				self.publish(_("Importing {}").format(doctype), i + 1, progress_total)

				flags = doc.pop("flags") if doc.get("flags") else {}
				d = frappe.get_doc(doc)
				d.flags.update(flags)
				d.insert()
				frappe.db.commit()
			except Exception as e:
				frappe.db.rollback()
				error = str(e)

				if len(e.args) == 3 and frappe.db.is_unique_key_violation(e.args[2]):
					error = _("{0} named {1} already exists").format(doctype, frappe.bold(d.name))

				error_log.append({ "doc": doc, "error": error, "status": "Failed" })

		self.update_field("error_log", json.dumps(error_log))

		return skipped_docs, error_log
	
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
				self.failed_import_log = json.dumps(failed_import_log, separators=(",", ":"))
				self.save()
				frappe.db.commit()

		else:
			data = data or self.status
			message = "\n".join(["Data:", json.dumps(data, default=str, indent=4), "--" * 50, "\nException:", traceback.format_exc()])
			return frappe.log_error(title="Tally Migration Error", message=message)