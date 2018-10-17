# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from requests_oauthlib import OAuth2Session
import json, requests
from erpnext import encode_company_abbr

# QuickBooks requires a redirect URL, User will be redirect to this URL
# This will be a GET request
# Request parameters will have two parameters `code` and `realmId`
# `code` is required to acquire refresh_token and access_token
# `realmId` is the QuickBooks Company ID. It is Needed to actually fetch data.
@frappe.whitelist()
def callback(*args, **kwargs):
	migrator = frappe.get_doc("QuickBooks Migrator")
	migrator.set_indicator("Connecting to QuickBooks")
	migrator.code = kwargs.get("code")
	migrator.quickbooks_company_id = kwargs.get("realmId")
	migrator.save()
	migrator.get_tokens()
	frappe.db.commit()
	migrator.set_indicator("Connected to QuickBooks")
	# We need this page to automatically close afterwards
	frappe.respond_as_web_page("Quickbooks Authentication", html="<script>window.close()</script>")


class QuickBooksMigrator(Document):
	def __init__(self, *args, **kwargs):
		super(QuickBooksMigrator, self).__init__(*args, **kwargs)
		from pprint import pprint
		self.oauth = OAuth2Session(
			client_id=self.client_id,
			redirect_uri=self.redirect_url,
			scope=self.scope
		)
		if not self.authorization_url and self.authorization_endpoint:
			self.authorization_url = self.oauth.authorization_url(self.authorization_endpoint)[0]


	def on_update(self):
		if self.company:
			# We need a Cost Center corresponding to the selected erpnext Company
			self.default_cost_center = frappe.db.get_value('Company', self.company, 'cost_center')
			self.default_warehouse = frappe.get_all('Warehouse', filters={"company": self.company, "is_group": 0})[0]["name"]
		if self.authorization_endpoint:
			self.authorization_url = self.oauth.authorization_url(self.authorization_endpoint)[0]


	def migrate(self):
		frappe.enqueue_doc("QuickBooks Migrator", "QuickBooks Migrator", "_migrate", queue="long")


	def _migrate(self):
		try:
			self.set_indicator("In Progress")
			# Add quickbooks_id field to every document so that we can lookup by Id reference
			# provided by documents in API responses.
			# Also add a company field to Customer Supplier and Item
			self._make_custom_fields()

			self._migrate_accounts()

			# Some Quickbooks Entities like Advance Payment, Payment aren't available firectly from API
			# Sales Invoice also sometimes needs to be saved as a Journal Entry
			# (When Item table is not present, This appens when Invoice is attached with a "StatementCharge" "ReimburseCharge
			# Details of both of these cannot be fetched from API)
			# Their GL entries need to be generated from GeneralLedger Report.
			self._fetch_general_ledger()

			# QuickBooks data can have transactions that do not fall in existing fiscal years in ERPNext
			self._create_fiscal_years()

			self._allow_fraction_in_unit()

			# Following entities are directly available from API
			# Invoice can be an exception sometimes though (as explained above).
			entities_for_normal_transform = [
				"Customer", "Item", "Vendor",
				"Preferences",
				"JournalEntry", "Purchase", "Deposit",
				"Invoice", "CreditMemo", "SalesReceipt", "RefundReceipt",
				"Bill", "VendorCredit",
				"Payment", "BillPayment",
			]
			for entity in entities_for_normal_transform:
				self._migrate_entries(entity)

			# Following entries are not available directly from API, Need to be regenrated from GeneralLedger Report
			entities_for_gl_transform = ["Advance Payment", "Tax Payment", "Sales Tax Payment", "Purchase Tax Payment", "Inventory Qty Adjust"]
			for entity in entities_for_gl_transform:
				self._migrate_entries_from_gl(entity)
			self.set_indicator("Complete")
		except Exception as e:
			self.set_indicator("Failed")
			self._log_error(e)

		frappe.db.commit()


	def get_tokens(self):
		token = self.oauth.fetch_token(
			token_url=self.token_endpoint,
			client_secret=self.client_secret,
			code=self.code
		)
		self.access_token = token["access_token"]
		self.refresh_token = token["refresh_token"]
		self.save()


	def _refresh_tokens(self):
		token = self.oauth.refresh_token(
			token_url=self.token_endpoint,
			client_id=self.client_id,
			refresh_token=self.refresh_token,
			client_secret=self.client_secret,
			code=self.code
		)
		self.access_token = token["access_token"]
		self.refresh_token = token["refresh_token"]
		self.save()


	def _make_custom_fields(self):
		doctypes_for_quickbooks_id_field = ["Account", "Customer", "Address", "Item", "Supplier", "Sales Invoice", "Journal Entry", "Purchase Invoice"]
		for doctype in doctypes_for_quickbooks_id_field:
			self._make_custom_quickbooks_id_field(doctype)

		doctypes_for_company_field = ["Customer", "Item", "Supplier"]
		for doctype in doctypes_for_company_field:
			self._make_custom_company_field(doctype)

		frappe.db.commit()


	def _make_custom_quickbooks_id_field(self, doctype):
		if not frappe.get_meta(doctype).has_field("quickbooks_id"):
			frappe.get_doc({
				"doctype": "Custom Field",
				"label": "QuickBooks ID",
				"dt": doctype,
				"fieldname": "quickbooks_id",
				"fieldtype": "Data",
			}).insert()


	def _make_custom_company_field(self, doctype):
		if not frappe.get_meta(doctype).has_field("company"):
			frappe.get_doc({
				"doctype": "Custom Field",
				"label": "Company",
				"dt": doctype,
				"fieldname": "company",
				"fieldtype": "Link",
				"options": "Company",
			}).insert()


	def _migrate_accounts(self):
		self._make_root_accounts()
		for entity in ["Account", "TaxRate", "TaxCode"]:
			self._migrate_entries(entity)


	def _make_root_accounts(self):
		roots = ["Asset", "Equity", "Expense", "Liability", "Income"]
		for root in roots:
			try:
				if not frappe.db.exists({"doctype": "Account", "name": encode_company_abbr("{} - QB".format(root), self.company), "company": self.company}):
					frappe.get_doc({
						"doctype": "Account",
						"account_name": "{} - QB".format(root),
						"root_type": root,
						"is_group": "1",
						"company": self.company,
					}).insert(ignore_mandatory=True)
			except Exception as e:
				self._log_error(e, root)
		frappe.db.commit()


	def _migrate_entries(self, entity):
		try:
			query_uri = "{}/company/{}/query".format(
				self.api_endpoint,
				self.quickbooks_company_id,
			)
			max_result_count = 1000
			# Count number of entries
			response = self._get(query_uri,
				params={
					"query": """SELECT COUNT(*) FROM {}""".format(entity)
				}
			)
			entry_count = response.json()["QueryResponse"]["totalCount"]

			# fetch pages and accumulate
			entries = []
			for start_position in range(1, entry_count + 1, max_result_count):
				response = self._get(query_uri,
					params={
						"query": """SELECT * FROM {} STARTPOSITION {} MAXRESULTS {}""".format(
							entity, start_position, max_result_count
						)
					}
				)
				entries.extend(response.json()["QueryResponse"][entity])
			entries = self._preprocess_entries(entity, entries)
			self._save_entries(entity, entries)
		except Exception as e:
			self._log_error(e, response.text)


	def _fetch_general_ledger(self):
		try:
			query_uri = "{}/company/{}/reports/GeneralLedger".format(self.api_endpoint ,self.quickbooks_company_id)
			response = self._get(query_uri,
				params={
					"columns": ",".join(["tx_date", "txn_type", "credit_amt", "debt_amt"]),
					"date_macro": "All",
					"minorversion": 3,
				}
			)
			self.gl_entries = {}
			for section in response.json()["Rows"]["Row"]:
				if section["type"] == "Section":
					self._get_gl_entries_from_section(section)
			self.general_ledger = {}
			for account in self.gl_entries.values():
				for line in account:
					type_dict = self.general_ledger.setdefault(line["type"], {})
					if line["id"] not in type_dict:
						type_dict[line["id"]] = {
							"id": line["id"],
							"date": line["date"],
							"lines": [],
						}
					type_dict[line["id"]]["lines"].append(line)
		except Exception as e:
			self._log_error(e, response.text)


	def _create_fiscal_years(self):
		try:
			# Assumes that exactly one fiscal year has been created so far
			# Creates fiscal years till oldest ledger entry date is covered
			from frappe.utils.data import add_years, getdate
			from itertools import chain
			smallest_ledger_entry_date = getdate(min(entry["date"] for entry in chain(*self.gl_entries.values()) if entry["date"]))
			oldest_fiscal_year = frappe.get_all("Fiscal Year",
				fields=["year_start_date", "year_end_date"],
				order_by="year_start_date"
			)[0]
			# Keep on creating fiscal years
			# until smallest_ledger_entry_date is no longer smaller than the oldest fiscal year's start date
			while smallest_ledger_entry_date < oldest_fiscal_year.year_start_date:
				new_fiscal_year = frappe.get_doc({"doctype": "Fiscal Year"})
				new_fiscal_year.year_start_date = add_years(oldest_fiscal_year.year_start_date, -1)
				new_fiscal_year.year_end_date = add_years(oldest_fiscal_year.year_end_date, -1)
				if new_fiscal_year.year_start_date.year == new_fiscal_year.year_end_date.year:
					new_fiscal_year.year = new_fiscal_year.year_start_date.year
				else:
					new_fiscal_year.year = "{}-{}".format(new_fiscal_year.year_start_date.year, new_fiscal_year.year_end_date.year)
				new_fiscal_year.save()
				oldest_fiscal_year = new_fiscal_year

			frappe.db.commit()
		except Exception as e:
			self._log_error(e)


	def _migrate_entries_from_gl(self, entity):
		if entity in self.general_ledger:
			self._save_entries(entity, self.general_ledger[entity].values())


	def _save_entries(self, entity, entries):
		entity_method_map = {
			"Account": self._save_account,
			"TaxRate": self._save_tax_rate,
			"TaxCode": self._save_tax_code,

			"Preferences": self._save_preference,

			"Customer": self._save_customer,
			"Item": self._save_item,
			"Vendor": self._save_vendor,

			"Invoice": self._save_invoice,
			"CreditMemo": self._save_credit_memo,
			"SalesReceipt": self._save_sales_receipt,
			"RefundReceipt": self._save_refund_receipt,

			"JournalEntry": self._save_journal_entry,

			"Bill": self._save_bill,
			"VendorCredit": self._save_vendor_credit,

			"Payment": self._save_payment,
			"BillPayment": self._save_bill_payment,

			"Purchase": self._save_purchase,
			"Deposit": self._save_deposit,

			"Advance Payment": self._save_advance_payment,
			"Tax Payment": self._save_tax_payment,
			"Sales Tax Payment": self._save_tax_payment,
			"Purchase Tax Payment": self._save_tax_payment,
			"Inventory Qty Adjust": self._save_inventory_qty_adjust,
		}
		total = len(entries)
		for index, entry in enumerate(entries, start=1):
			self._publish({"event": "progress", "message": _("Saving {0}").format(entity), "count": index, "total": total})
			entity_method_map[entity](entry)
		frappe.db.commit()


	def _preprocess_entries(self, entity, entries):
		entity_method_map = {
			"Account": self._preprocess_accounts,
			"TaxRate": self._preprocess_tax_rates,
			"TaxCode": self._preprocess_tax_codes,
		}
		preprocessor = entity_method_map.get(entity)
		if preprocessor:
			entries = preprocessor(entries)
		return entries


	def _get_gl_entries_from_section(self, section, account=None):
		if "Header" in section:
			if "id" in section["Header"]["ColData"][0]:
				account = self._get_account_name_by_id(section["Header"]["ColData"][0]["id"])
			elif "value" in section["Header"]["ColData"][0] and section["Header"]["ColData"][0]["value"]:
				# For some reason during migrating UK company, account id is not available.
				# preprocess_accounts retains name:account mapping in self.accounts
				# This mapping can then be used to obtain quickbooks_id for correspondong account
				# Rest is trivial

				# Some Lines in General Leder Report are shown under Not Specified
				# These should be skipped
				if section["Header"]["ColData"][0]["value"] == "Not Specified":
					return
				account_id = self.accounts[section["Header"]["ColData"][0]["value"]]["Id"]
				account = self._get_account_name_by_id(account_id)
		entries = []
		for row in section["Rows"]["Row"]:
			if row["type"] == "Data":
				data = row["ColData"]
				entries.append({
					"account": account,
					"date": data[0]["value"],
					"type": data[1]["value"],
					"id": data[1].get("id"),
					"credit": frappe.utils.flt(data[2]["value"]),
					"debit": frappe.utils.flt(data[3]["value"]),
				})
			if row["type"] == "Section":
				self._get_gl_entries_from_section(row, account)
		self.gl_entries.setdefault(account, []).extend(entries)


	def _preprocess_accounts(self, accounts):
		self.accounts = {account["Name"]: account for account in accounts}
		for account in accounts:
			if any(acc["SubAccount"] and acc["ParentRef"]["value"] == account["Id"] for acc in accounts):
				account["is_group"] = 1
			else:
				account["is_group"] = 0
		return sorted(accounts, key=lambda account: int(account["Id"]))


	def _save_account(self, account):
		mapping = {
			"Bank": "Asset",
			"Other Current Asset": "Asset",
			"Fixed Asset": "Asset",
			"Other Asset": "Asset",
			"Accounts Receivable": "Asset",

			"Equity": "Equity",

			"Expense": "Expense",
			"Other Expense": "Expense",
			"Cost of Goods Sold": "Expense",

			"Accounts Payable": "Liability",
			"Credit Card": "Liability",
			"Long Term Liability": "Liability",
			"Other Current Liability": "Liability",

			"Income": "Income",
			"Other Income": "Income",
		}
		# Map Quickbooks Account Types to ERPNext root_accunts and and root_type
		try:
			if not frappe.db.exists({"doctype": "Account", "quickbooks_id": account["Id"], "company": self.company}):
				is_child = account["SubAccount"]
				is_group = account["is_group"]
				# Create Two Accounts for every Group Account
				if is_group:
					account_id = "Group - {}".format(account["Id"])
				else:
					account_id = account["Id"]

				if is_child:
					parent_account = self._get_account_name_by_id("Group - {}".format(account["ParentRef"]["value"]))
				else:
					parent_account = encode_company_abbr("{} - QB".format(mapping[account["AccountType"]]), self.company)

				frappe.get_doc({
					"doctype": "Account",
					"quickbooks_id": account_id,
					"account_name": self._get_unique_account_name(account["Name"]),
					"root_type": mapping[account["AccountType"]],
					"account_type": self._get_account_type(account),
					"account_currency": account["CurrencyRef"]["value"],
					"parent_account": parent_account,
					"is_group": is_group,
					"company": self.company,
				}).insert()

				if is_group:
					# Create a Leaf account corresponding to the group account
					frappe.get_doc({
						"doctype": "Account",
						"quickbooks_id": account["Id"],
						"account_name": self._get_unique_account_name(account["Name"]),
						"root_type": mapping[account["AccountType"]],
						"account_type": self._get_account_type(account),
						"account_currency": account["CurrencyRef"]["value"],
						"parent_account": self._get_account_name_by_id(account_id),
						"is_group": 0,
						"company": self.company,
					}).insert()
				if account.get("AccountSubType") == "UndepositedFunds":
					self.undeposited_funds_account = self._get_account_name_by_id(account["Id"])
					self.save()
		except Exception as e:
			self._log_error(e, account)


	def _get_account_type(self, account):
		account_subtype_mapping = {"UndepositedFunds": "Cash"}
		account_type = account_subtype_mapping.get(account.get("AccountSubType"))
		if account_type is None:
			account_type_mapping = {"Accounts Payable": "Payable", "Accounts Receivable": "Receivable", "Bank": "Bank", "Credit Card": "Bank"}
			account_type = account_type_mapping.get(account["AccountType"])
		return account_type


	def _preprocess_tax_rates(self, tax_rates):
		self.tax_rates = {tax_rate["Id"]: tax_rate for tax_rate in tax_rates}
		return tax_rates


	def _save_tax_rate(self, tax_rate):
		try:
			if not frappe.db.exists({"doctype": "Account", "quickbooks_id": "TaxRate - {}".format(tax_rate["Id"]), "company": self.company}):
				frappe.get_doc({
					"doctype": "Account",
					"quickbooks_id": "TaxRate - {}".format(tax_rate["Id"]),
					"account_name": "{} - QB".format(tax_rate["Name"]),
					"root_type": "Liability",
					"parent_account": encode_company_abbr("{} - QB".format("Liability"), self.company),
					"is_group": "0",
					"company": self.company,
				}).insert()
		except Exception as e:
			self._log_error(e, tax_rate)


	def _preprocess_tax_codes(self, tax_codes):
		self.tax_codes = {tax_code["Id"]: tax_code for tax_code in tax_codes}
		return tax_codes


	def _save_tax_code(self, tax_code):
		pass


	def _save_customer(self, customer):
		try:
			if not frappe.db.exists({"doctype": "Customer", "quickbooks_id": customer["Id"], "company": self.company}):
				try:
					receivable_account = frappe.get_all("Account", filters={
						"account_type": "Receivable",
						"account_currency": customer["CurrencyRef"]["value"],
						"company": self.company,
					})[0]["name"]
				except Exception as e:
					receivable_account = None
				erpcustomer = frappe.get_doc({
					"doctype": "Customer",
					"quickbooks_id": customer["Id"],
					"customer_name" : encode_company_abbr(customer["DisplayName"], self.company),
					"customer_type" : "Individual",
					"customer_group" : "Commercial",
					"default_currency": customer["CurrencyRef"]["value"],
					"accounts": [{"company": self.company, "account": receivable_account}],
					"territory" : "All Territories",
					"company": self.company,
				}).insert()
				if "BillAddr" in customer:
					self._create_address(erpcustomer, "Customer", customer["BillAddr"], "Billing")
				if "ShipAddr" in customer:
					self._create_address(erpcustomer, "Customer", customer["ShipAddr"], "Shipping")
		except Exception as e:
			self._log_error(e, customer)


	def _save_item(self, item):
		try:
			if not frappe.db.exists({"doctype": "Item", "quickbooks_id": item["Id"], "company": self.company}):
				if item["Type"] in ("Service", "Inventory"):
					item_dict = {
						"doctype": "Item",
						"quickbooks_id": item["Id"],
						"item_code" : encode_company_abbr(item["Name"], self.company),
						"stock_uom": "Unit",
						"is_stock_item": 0,
						"item_group": "All Item Groups",
						"company": self.company,
						"item_defaults": [{"company": self.company, "default_warehouse": self.default_warehouse}]
					}
					if "ExpenseAccountRef" in item:
						expense_account = self._get_account_name_by_id(item["ExpenseAccountRef"]["value"])
						item_dict["item_defaults"][0]["expense_account"] = expense_account
					if "IncomeAccountRef" in item:
						income_account = self._get_account_name_by_id(item["IncomeAccountRef"]["value"])
						item_dict["item_defaults"][0]["income_account"] = income_account
					frappe.get_doc(item_dict).insert()
		except Exception as e:
			self._log_error(e, item)


	def _allow_fraction_in_unit(self):
		frappe.db.set_value("UOM", "Unit", "must_be_whole_number", 0)


	def _save_vendor(self, vendor):
		try:
			if not frappe.db.exists({"doctype": "Supplier", "quickbooks_id": vendor["Id"], "company": self.company}):
				erpsupplier = frappe.get_doc({
					"doctype": "Supplier",
					"quickbooks_id": vendor["Id"],
					"supplier_name" : encode_company_abbr(vendor["DisplayName"], self.company),
					"supplier_group" : "All Supplier Groups",
					"company": self.company,
				}).insert()
				if "BillAddr" in vendor:
					self._create_address(erpsupplier, "Supplier", vendor["BillAddr"], "Billing")
				if "ShipAddr" in vendor:
					self._create_address(erpsupplier, "Supplier",vendor["ShipAddr"], "Shipping")
		except Exception as e:
			self._log_error(e)


	def _save_preference(self, preference):
		try:
			if preference["SalesFormsPrefs"]["AllowShipping"]:
				default_shipping_account_id = preference["SalesFormsPrefs"]["DefaultShippingAccount"]
				self.default_shipping_account = self._get_account_name_by_id(self, default_shipping_account_id)
				self.save()
		except Exception as e:
			self._log_error(e, preference)


	def _save_invoice(self, invoice):
		# Invoice can be Linked with Another Transactions
		# If any of these transactions is a "StatementCharge" or "ReimburseCharge" then in the UI
		# item list is populated from the corresponding transaction, these items are not shown in api response
		# Also as of now there is no way of fetching the corresponding transaction from api
		# We in order to correctly reflect account balance make an equivalent Journal Entry
		quickbooks_id = "Invoice - {}".format(invoice["Id"])
		if any(linked["TxnType"] in ("StatementCharge", "ReimburseCharge") for linked in invoice["LinkedTxn"]):
			self._save_invoice_as_journal_entry(invoice, quickbooks_id)
		else:
			self._save_sales_invoice(invoice, quickbooks_id)


	def _save_credit_memo(self, credit_memo):
		# Credit Memo is equivalent to a return Sales Invoice
		quickbooks_id = "Credit Memo - {}".format(credit_memo["Id"])
		self._save_sales_invoice(credit_memo, quickbooks_id, is_return=True)


	def _save_sales_receipt(self, sales_receipt):
		# Sales Receipt is equivalent to a POS Sales Invoice
		quickbooks_id = "Sales Receipt - {}".format(sales_receipt["Id"])
		self._save_sales_invoice(sales_receipt, quickbooks_id, is_pos=True)


	def _save_refund_receipt(self, refund_receipt):
		# Refund Receipt is equivalent to a return POS Sales Invoice
		quickbooks_id = "Refund Receipt - {}".format(refund_receipt["Id"])
		self._save_sales_invoice(refund_receipt, quickbooks_id, is_return=True, is_pos=True)


	def _save_sales_invoice(self, invoice, quickbooks_id, is_return=False, is_pos=False):
		try:
			if not frappe.db.exists({"doctype": "Sales Invoice", "quickbooks_id": quickbooks_id, "company": self.company}):
				invoice_dict = {
					"doctype": "Sales Invoice",
					"quickbooks_id": quickbooks_id,

					# Quickbooks uses ISO 4217 Code
					# of course this gonna come back to bite me
					"currency": invoice["CurrencyRef"]["value"],

					# Exchange Rate is provided if multicurrency is enabled
					# It is not provided if multicurrency is not enabled
					"conversion_rate": invoice.get("ExchangeRate", 1),
					"posting_date": invoice["TxnDate"],

					# QuickBooks doesn't make Due Date a mandatory field this is a hack
					"due_date": invoice.get("DueDate", invoice["TxnDate"]),
					"customer": frappe.get_all("Customer",
						filters={
							"quickbooks_id": invoice["CustomerRef"]["value"],
							"company": self.company,
						})[0]["name"],
					"items": self._get_si_items(invoice, is_return=is_return),
					"taxes": self._get_taxes(invoice),

					# Do not change posting_date upon submission
					"set_posting_time": 1,

					# QuickBooks doesn't round total
					"disable_rounded_total": 1,
					"is_return": is_return,
					"is_pos": is_pos,
					"payments": self._get_invoice_payments(invoice, is_return=is_return, is_pos=is_pos),
					"company": self.company,
				}
				discount = self._get_discount(invoice["Line"])
				if discount:
					if invoice["ApplyTaxAfterDiscount"]:
						invoice_dict["apply_discount_on"] = "Net Total"
					else:
						invoice_dict["apply_discount_on"] = "Grand Total"
					invoice_dict["discount_amount"] = discount["Amount"]

				invoice_doc = frappe.get_doc(invoice_dict)
				invoice_doc.insert()
				invoice_doc.submit()
		except Exception as e:
			self._log_error(e, [invoice, invoice_dict, json.loads(invoice_doc.as_json())])


	def _get_si_items(self, invoice, is_return=False):
		items = []
		for line in invoice["Line"]:
			if line["DetailType"] == "SalesItemLineDetail":
				if line["SalesItemLineDetail"]["TaxCodeRef"]["value"] != "TAX":
					tax_code = line["SalesItemLineDetail"]["TaxCodeRef"]["value"]
				else:
					if "TxnTaxCodeRef" in invoice["TxnTaxDetail"]:
						tax_code = invoice["TxnTaxDetail"]["TxnTaxCodeRef"]["value"]
					else:
						tax_code = "NON"
				if line["SalesItemLineDetail"]["ItemRef"]["value"] != "SHIPPING_ITEM_ID":
					item = frappe.db.get_all("Item",
						filters={
							"quickbooks_id": line["SalesItemLineDetail"]["ItemRef"]["value"],
							"company": self.company,
						},
						fields=["name", "stock_uom"]
					)[0]
					items.append({
						"item_code": item["name"],
						"conversion_factor": 1,
						"uom": item["stock_uom"],
						"description": line.get("Description", line["SalesItemLineDetail"]["ItemRef"]["name"]),
						"qty": line["SalesItemLineDetail"]["Qty"],
						"price_list_rate": line["SalesItemLineDetail"]["UnitPrice"],
						"cost_center": self.default_cost_center,
						"warehouse": self.default_warehouse,
						"item_tax_rate": json.dumps(self._get_item_taxes(tax_code))
					})
				else:
					items.append({
						"item_name": "Shipping",
						"conversion_factor": 1,
						"expense_account": self._get_account_name_by_id("TaxRate - {}".format(line["SalesItemLineDetail"]["TaxCodeRef"]["value"])),
						"uom": "Unit",
						"description": "Shipping",
						"income_account": self.default_shipping_account,
						"qty": 1,
						"price_list_rate": line["Amount"],
						"cost_center": self.default_cost_center,
						"warehouse": self.default_warehouse,
						"item_tax_rate": json.dumps(self._get_item_taxes(tax_code))
					})
				if is_return:
					items[-1]["qty"] *= -1
			elif line["DetailType"] == "DescriptionOnly":
				items[-1].update({
					"margin_type": "Percentage",
					"margin_rate_or_amount": int(line["Description"].split("%")[0]),
				})
		return items


	def _get_item_taxes(self, tax_code):
		tax_rates = self.tax_rates
		item_taxes = {}
		if tax_code != "NON":
			tax_code = self.tax_codes[tax_code]
			for rate_list_type in ("SalesTaxRateList", "PurchaseTaxRateList"):
				if rate_list_type in tax_code:
					for tax_rate_detail in tax_code[rate_list_type]["TaxRateDetail"]:
						if tax_rate_detail["TaxTypeApplicable"] == "TaxOnAmount":
							tax_head = self._get_account_name_by_id("TaxRate - {}".format(tax_rate_detail["TaxRateRef"]["value"]))
							tax_rate = tax_rates[tax_rate_detail["TaxRateRef"]["value"]]
							item_taxes[tax_head] = tax_rate["RateValue"]
		return item_taxes


	def _get_invoice_payments(self, invoice, is_return=False, is_pos=False):
		if is_pos:
			amount = invoice["TotalAmt"]
			if is_return:
				amount = -amount
			return [{
				"mode_of_payment": "Cash",
				"account": self._get_account_name_by_id(invoice["DepositToAccountRef"]["value"]),
				"amount": amount,
			}]


	def _get_discount(self, lines):
		for line in lines:
			if line["DetailType"] == "DiscountLineDetail" and "Amount" in line["DiscountLineDetail"]:
				return line


	def _save_invoice_as_journal_entry(self, invoice, quickbooks_id):
		try:
			accounts = []
			for line in self.general_ledger["Invoice"][invoice["Id"]]["lines"]:
				account_line = {"account": line["account"], "cost_center": self.default_cost_center}
				if line["debit"]:
					account_line["debit_in_account_currency"] = line["debit"]
				elif line["credit"]:
					account_line["credit_in_account_currency"] = line["credit"]
				if frappe.db.get_value("Account", line["account"], "account_type") == "Receivable":
					account_line["party_type"] = "Customer"
					account_line["party"] = frappe.get_all("Customer",
						filters={"quickbooks_id": invoice["CustomerRef"]["value"], "company": self.company}
					)[0]["name"]

				accounts.append(account_line)

			posting_date = invoice["TxnDate"]
			self.__save_journal_entry(quickbooks_id, accounts, posting_date)
		except Exception as e:
			self._log_error(e, [invoice, accounts])


	def _save_journal_entry(self, journal_entry):
		# JournalEntry is equivalent to a Journal Entry

		def _get_je_accounts(lines):
			# Converts JounalEntry lines to accounts list
			posting_type_field_mapping = {
				"Credit": "credit_in_account_currency",
				"Debit": "debit_in_account_currency",
			}
			accounts = []
			for line in lines:
				if line["DetailType"] == "JournalEntryLineDetail":
					account_name = self._get_account_name_by_id(line["JournalEntryLineDetail"]["AccountRef"]["value"])
					posting_type = line["JournalEntryLineDetail"]["PostingType"]
					accounts.append({
						"account": account_name,
						posting_type_field_mapping[posting_type]: line["Amount"],
						"cost_center": self.default_cost_center,
					})
			return accounts

		quickbooks_id = "Journal Entry - {}".format(journal_entry["Id"])
		accounts = _get_je_accounts(journal_entry["Line"])
		posting_date = journal_entry["TxnDate"]
		self.__save_journal_entry(quickbooks_id, accounts, posting_date)


	def __save_journal_entry(self, quickbooks_id, accounts, posting_date):
		try:
			if not frappe.db.exists({"doctype": "Journal Entry", "quickbooks_id": quickbooks_id, "company": self.company}):
				je = frappe.get_doc({
					"doctype": "Journal Entry",
					"quickbooks_id": quickbooks_id,
					"company": self.company,
					"posting_date": posting_date,
					"accounts": accounts,
					"multi_currency": 1,
				})
				je.insert()
				je.submit()
		except Exception as e:
			self._log_error(e, [accounts, json.loads(je.as_json())])


	def _save_bill(self, bill):
		# Bill is equivalent to a Purchase Invoice
		quickbooks_id = "Bill - {}".format(bill["Id"])
		self.__save_purchase_invoice(bill, quickbooks_id)


	def _save_vendor_credit(self, vendor_credit):
		# Vendor Credit is equivalent to a return Purchase Invoice
		quickbooks_id = "Vendor Credit - {}".format(vendor_credit["Id"])
		self.__save_purchase_invoice(vendor_credit, quickbooks_id, is_return=True)


	def __save_purchase_invoice(self, invoice, quickbooks_id, is_return=False):
		try:
			if not frappe.db.exists({"doctype": "Purchase Invoice", "quickbooks_id": quickbooks_id, "company": self.company}):
				credit_to_account = self._get_account_name_by_id(invoice["APAccountRef"]["value"])
				invoice_dict = {
					"doctype": "Purchase Invoice",
					"quickbooks_id": quickbooks_id,
					"currency": invoice["CurrencyRef"]["value"],
					"conversion_rate": invoice.get("ExchangeRate", 1),
					"posting_date": invoice["TxnDate"],
					"due_date":  invoice.get("DueDate", invoice["TxnDate"]),
					"credit_to": credit_to_account,
					"supplier": frappe.get_all("Supplier",
						filters={
							"quickbooks_id": invoice["VendorRef"]["value"],
							"company": self.company,
						})[0]["name"],
					"items": self._get_pi_items(invoice, is_return=is_return),
					"taxes": self._get_taxes(invoice),
					"set_posting_time": 1,
					"disable_rounded_total": 1,
					"is_return": is_return,
					"udpate_stock": 0,
					"company": self.company,
				}
				invoice_doc = frappe.get_doc(invoice_dict)
				invoice_doc.insert()
				invoice_doc.submit()
		except Exception as e:
			self._log_error(e, [invoice, invoice_dict, json.loads(invoice_doc.as_json())])


	def _get_pi_items(self, purchase_invoice, is_return=False):
		items = []
		for line in purchase_invoice["Line"]:
			if line["DetailType"] == "ItemBasedExpenseLineDetail":
				if line["ItemBasedExpenseLineDetail"]["TaxCodeRef"]["value"] != "TAX":
					tax_code = line["ItemBasedExpenseLineDetail"]["TaxCodeRef"]["value"]
				else:
					if "TxnTaxCodeRef" in purchase_invoice["TxnTaxDetail"]:
						tax_code = purchase_invoice["TxnTaxDetail"]["TxnTaxCodeRef"]["value"]
					else:
						tax_code = "NON"
				item = frappe.db.get_all("Item",
					filters={
						"quickbooks_id": line["ItemBasedExpenseLineDetail"]["ItemRef"]["value"],
						"company": self.company
					},
					fields=["name", "stock_uom"]
				)[0]
				items.append({
					"item_code": item["name"],
					"conversion_factor": 1,
					"uom": item["stock_uom"],
					"description": line.get("Description", line["ItemBasedExpenseLineDetail"]["ItemRef"]["name"]),
					"qty": line["ItemBasedExpenseLineDetail"]["Qty"],
					"price_list_rate": line["ItemBasedExpenseLineDetail"]["UnitPrice"],
					"warehouse": self.default_warehouse,
					"cost_center": self.default_cost_center,
					"item_tax_rate": json.dumps(self._get_item_taxes(tax_code)),
				})
			elif line["DetailType"] == "AccountBasedExpenseLineDetail":
				if line["AccountBasedExpenseLineDetail"]["TaxCodeRef"]["value"] != "TAX":
					tax_code = line["AccountBasedExpenseLineDetail"]["TaxCodeRef"]["value"]
				else:
					if "TxnTaxCodeRef" in purchase_invoice["TxnTaxDetail"]:
						tax_code = purchase_invoice["TxnTaxDetail"]["TxnTaxCodeRef"]["value"]
					else:
						tax_code = "NON"
				items.append({
					"item_name": line.get("Description", line["AccountBasedExpenseLineDetail"]["AccountRef"]["name"]),
					"conversion_factor": 1,
					"expense_account": self._get_account_name_by_id(line["AccountBasedExpenseLineDetail"]["AccountRef"]["value"]),
					"uom": "Unit",
					"description": line.get("Description", line["AccountBasedExpenseLineDetail"]["AccountRef"]["name"]),
					"qty": 1,
					"price_list_rate": line["Amount"],
					"warehouse": self.default_warehouse,
					"cost_center": self.default_cost_center,
					"item_tax_rate": json.dumps(self._get_item_taxes(tax_code)),
				})
			if is_return:
				items[-1]["qty"] *= -1
		return items


	def _save_payment(self, payment):
		try:
			quickbooks_id = "Payment - {}".format(payment["Id"])
			# If DepositToAccountRef is not set on payment that means it actually doesn't affect any accounts
			# No need to record such payment
			# Such payment record is created QuickBooks Payments API
			if "DepositToAccountRef" not in payment:
				return

			# A Payment can be linked to multiple transactions
			accounts = []
			for line in payment["Line"]:
				linked_transaction = line["LinkedTxn"][0]
				if linked_transaction["TxnType"] == "Invoice":
					si_quickbooks_id = "Invoice - {}".format(linked_transaction["TxnId"])
					# Invoice could have been saved as a Sales Invoice or a Journal Entry
					if frappe.db.exists({"doctype": "Sales Invoice", "quickbooks_id": si_quickbooks_id, "company": self.company}):
						sales_invoice = frappe.get_all("Sales Invoice",
							filters={
								"quickbooks_id": si_quickbooks_id,
								"company": self.company,
							},
							fields=["name", "customer", "debit_to"],
						)[0]
						reference_type = "Sales Invoice"
						reference_name = sales_invoice["name"]
						party = sales_invoice["customer"]
						party_account = sales_invoice["debit_to"]

					if frappe.db.exists({"doctype": "Journal Entry", "quickbooks_id": si_quickbooks_id, "company": self.company}):
						journal_entry = frappe.get_doc("Journal Entry",
							{
								"quickbooks_id": si_quickbooks_id,
								"company": self.company,
							}
						)
						# Invoice saved as a Journal Entry must have party and party_type set on line containing Receivable Account
						customer_account_line = list(filter(lambda acc: acc.party_type == "Customer", journal_entry.accounts))[0]

						reference_type = "Journal Entry"
						reference_name = journal_entry.name
						party = customer_account_line.party
						party_account = customer_account_line.account

					accounts.append({
						"party_type": "Customer",
						"party": party,
						"reference_type": reference_type,
						"reference_name": reference_name,
						"account": party_account,
						"credit_in_account_currency": line["Amount"],
						"cost_center": self.default_cost_center,
					})

			deposit_account = self._get_account_name_by_id(payment["DepositToAccountRef"]["value"])
			accounts.append({
				"account": deposit_account,
				"debit_in_account_currency": payment["TotalAmt"],
				"cost_center": self.default_cost_center,
			})
			posting_date = payment["TxnDate"]
			self.__save_journal_entry(quickbooks_id, accounts, posting_date)
		except Exception as e:
			self._log_error(e, [payment, accounts])


	def _save_bill_payment(self, bill_payment):
		try:
			quickbooks_id = "BillPayment - {}".format(bill_payment["Id"])
			# A BillPayment can be linked to multiple transactions
			accounts = []
			for line in bill_payment["Line"]:
				linked_transaction = line["LinkedTxn"][0]
				if linked_transaction["TxnType"] == "Bill":
					pi_quickbooks_id = "Bill - {}".format(linked_transaction["TxnId"])
					if frappe.db.exists({"doctype": "Purchase Invoice", "quickbooks_id": pi_quickbooks_id, "company": self.company}):
						purchase_invoice = frappe.get_all("Purchase Invoice",
							filters={
								"quickbooks_id": pi_quickbooks_id,
								"company": self.company,
							},
							fields=["name", "supplier", "credit_to"],
						)[0]
						reference_type = "Purchase Invoice"
						reference_name = purchase_invoice["name"]
						party = purchase_invoice["supplier"]
						party_account = purchase_invoice["credit_to"]
					accounts.append({
						"party_type": "Supplier",
						"party": party,
						"reference_type": reference_type,
						"reference_name": reference_name,
						"account": party_account,
						"debit_in_account_currency": line["Amount"],
						"cost_center": self.default_cost_center,
					})

			if bill_payment["PayType"] == "Check":
				bank_account_id = bill_payment["CheckPayment"]["BankAccountRef"]["value"]
			elif bill_payment["PayType"] == "CreditCard":
				bank_account_id = bill_payment["CreditCardPayment"]["CCAccountRef"]["value"]

			bank_account = self._get_account_name_by_id(bank_account_id)
			accounts.append({
				"account": bank_account,
				"credit_in_account_currency": bill_payment["TotalAmt"],
				"cost_center": self.default_cost_center,
			})
			posting_date = bill_payment["TxnDate"]
			self.__save_journal_entry(quickbooks_id, accounts, posting_date)
		except Exception as e:
			self._log_error(e, [bill_payment, accounts])


	def _save_purchase(self, purchase):
		try:
			quickbooks_id = "Purchase - {}".format(purchase["Id"])
			# Credit Bank Account
			accounts = [{
				"account": self._get_account_name_by_id(purchase["AccountRef"]["value"]),
				"credit_in_account_currency": purchase["TotalAmt"],
				"cost_center": self.default_cost_center,
			}]

			# Debit Mentioned Accounts
			for line in purchase["Line"]:
				if line["DetailType"] == "AccountBasedExpenseLineDetail":
					account = self._get_account_name_by_id(line["AccountBasedExpenseLineDetail"]["AccountRef"]["value"])
				elif line["DetailType"] == "ItemBasedExpenseLineDetail":
					account = frappe.get_doc("Item",
						{"quickbooks_id": line["ItemBasedExpenseLineDetail"]["ItemRef"]["value"], "company": self.company}
					).item_defaults[0].expense_account
				accounts.append({
					"account": account,
					"debit_in_account_currency": line["Amount"],
					"cost_center": self.default_cost_center,
				})

			# Debit Tax Accounts
			if "TxnTaxDetail" in purchase:
				for line in purchase["TxnTaxDetail"]["TaxLine"]:
					accounts.append({
						"account": self._get_account_name_by_id("TaxRate - {}".format(line["TaxLineDetail"]["TaxRateRef"]["value"])),
						"debit_in_account_currency": line["Amount"],
						"cost_center": self.default_cost_center,
					})

			# If purchase["Credit"] is set to be True then it represents a refund
			if purchase.get("Credit"):
				for account in accounts:
					if "debit_in_account_currency" in account:
						account["credit_in_account_currency"] = account["debit_in_account_currency"]
						del account["debit_in_account_currency"]
					else:
						account["debit_in_account_currency"] = account["credit_in_account_currency"]
						del account["credit_in_account_currency"]

			posting_date = purchase["TxnDate"]
			self.__save_journal_entry(quickbooks_id, accounts, posting_date)
		except Exception as e:
			self._log_error(e, [purchase, accounts])


	def _save_deposit(self, deposit):
		try:
			quickbooks_id = "Deposit - {}".format(deposit["Id"])
			# Debit Bank Account
			accounts = [{
				"account": self._get_account_name_by_id(deposit["DepositToAccountRef"]["value"]),
				"debit_in_account_currency": deposit["TotalAmt"],
				"cost_center": self.default_cost_center,
			}]

			# Credit Mentioned Accounts
			for line in deposit["Line"]:
				if "LinkedTxn" in line:
					accounts.append({
						"account": self.undeposited_funds_account,
						"credit_in_account_currency": line["Amount"],
						"cost_center": self.default_cost_center,
					})
				else:
					accounts.append({
						"account": self._get_account_name_by_id(line["DepositLineDetail"]["AccountRef"]["value"]),
						"credit_in_account_currency": line["Amount"],
						"cost_center": self.default_cost_center,
					})

			# Debit Cashback if mentioned
			if "CashBack" in deposit:
				accounts.append({
					"account": self._get_account_name_by_id(deposit["CashBack"]["AccountRef"]["value"]),
					"debit_in_account_currency": deposit["CashBack"]["Amount"],
					"cost_center": self.default_cost_center,
				})

			posting_date = deposit["TxnDate"]
			self.__save_journal_entry(quickbooks_id, accounts, posting_date)
		except Exception as e:
			self._log_error(e, [deposit, accounts])


	def _save_advance_payment(self, advance_payment):
		quickbooks_id = "Advance Payment - {}".format(advance_payment["id"])
		self.__save_ledger_entry_as_je(advance_payment, quickbooks_id)


	def _save_tax_payment(self, tax_payment):
		quickbooks_id = "Tax Payment - {}".format(tax_payment["id"])
		self.__save_ledger_entry_as_je(tax_payment, quickbooks_id)


	def _save_inventory_qty_adjust(self, inventory_qty_adjust):
		quickbooks_id = "Inventory Qty Adjust - {}".format(inventory_qty_adjust["id"])
		self.__save_ledger_entry_as_je(inventory_qty_adjust, quickbooks_id)


	def __save_ledger_entry_as_je(self, ledger_entry, quickbooks_id):
		try:
			accounts = []
			for line in ledger_entry["lines"]:
				account_line = {"account": line["account"], "cost_center": self.default_cost_center}
				if line["credit"]:
					account_line["credit_in_account_currency"] = line["credit"]
				else:
					account_line["debit_in_account_currency"] = line["debit"]
				accounts.append(account_line)

			posting_date = ledger_entry["date"]
			self.__save_journal_entry(quickbooks_id, accounts, posting_date)
		except Exception as e:
			self._log_error(e, ledger_entry)


	def _get_taxes(self, entry):
		taxes = []
		if "TxnTaxDetail" not in entry or "TaxLine" not in entry["TxnTaxDetail"]:
			return taxes
		for line in entry["TxnTaxDetail"]["TaxLine"]:
			tax_rate = line["TaxLineDetail"]["TaxRateRef"]["value"]
			account_head = self._get_account_name_by_id("TaxRate - {}".format(tax_rate))
			tax_type_applicable = self._get_tax_type(tax_rate)
			if tax_type_applicable == "TaxOnAmount":
				taxes.append({
					"charge_type": "On Net Total",
					"account_head": account_head,
					"description": account_head,
					"cost_center": self.default_cost_center,
					"rate": 0,
				})
			else:
				parent_tax_rate = self._get_parent_tax_rate(tax_rate)
				parent_row_id = self._get_parent_row_id(parent_tax_rate, taxes)
				taxes.append({
					"charge_type": "On Previous Row Amount",
					"row_id": parent_row_id,
					"account_head": account_head,
					"description": account_head,
					"cost_center": self.default_cost_center,
					"rate": line["TaxLineDetail"]["TaxPercent"],
				})
		return taxes


	def _get_tax_type(self, tax_rate):
		for tax_code in self.tax_codes.values():
			for rate_list_type in ("SalesTaxRateList", "PurchaseTaxRateList"):
				if rate_list_type in tax_code:
					for tax_rate_detail in tax_code[rate_list_type]["TaxRateDetail"]:
						if tax_rate_detail["TaxRateRef"]["value"] == tax_rate:
							return tax_rate_detail["TaxTypeApplicable"]


	def _get_parent_tax_rate(self, tax_rate):
		parent = None
		for tax_code in self.tax_codes.values():
			for rate_list_type in ("SalesTaxRateList", "PurchaseTaxRateList"):
				if rate_list_type in tax_code:
					for tax_rate_detail in tax_code[rate_list_type]["TaxRateDetail"]:
						if tax_rate_detail["TaxRateRef"]["value"] == tax_rate:
							parent = tax_rate_detail["TaxOnTaxOrder"]
					if parent:
						for tax_rate_detail in tax_code[rate_list_type]["TaxRateDetail"]:
							if tax_rate_detail["TaxOrder"] == parent:
								return tax_rate_detail["TaxRateRef"]["value"]


	def _get_parent_row_id(self, tax_rate, taxes):
		tax_account = self._get_account_name_by_id("TaxRate - {}".format(tax_rate))
		for index, tax in enumerate(taxes):
			if tax["account_head"] == tax_account:
				return index + 1


	def _create_address(self, entity, doctype, address, address_type):
		try :
			if not frappe.db.exists({"doctype": "Address", "quickbooks_id": address["Id"]}):
				frappe.get_doc({
					"doctype": "Address",
					"quickbooks_address_id": address["Id"],
					"address_title": entity.name,
					"address_type": address_type,
					"address_line1": address["Line1"],
					"city": address["City"],
					"links": [{"link_doctype": doctype, "link_name": entity.name}]
				}).insert()
		except Exception as e:
			self._log_error(e, address)


	def _get(self, *args, **kwargs):
		kwargs["headers"] = {
			"Accept": "application/json",
			"Authorization": "Bearer {}".format(self.access_token)
		}
		response = requests.get(*args, **kwargs)
		# HTTP Status code 401 here means that the access_token is expired
		# We can refresh tokens and retry
		# However limitless recursion does look dangerous
		if response.status_code == 401:
			self._refresh_tokens()
			response = self._get(*args, **kwargs)
		return response


	def _get_account_name_by_id(self, quickbooks_id):
		return frappe.get_all("Account", filters={"quickbooks_id": quickbooks_id, "company": self.company})[0]["name"]


	def _publish(self, *args, **kwargs):
		frappe.publish_realtime("quickbooks_progress_update", *args, **kwargs)


	def _get_unique_account_name(self, quickbooks_name, number=0):
		if number:
			quickbooks_account_name = "{} - {} - QB".format(quickbooks_name, number)
		else:
			quickbooks_account_name = "{} - QB".format(quickbooks_name)
		company_encoded_account_name = encode_company_abbr(quickbooks_account_name, self.company)
		if frappe.db.exists({"doctype": "Account", "name": company_encoded_account_name, "company": self.company}):
			unique_account_name = self._get_unique_account_name(quickbooks_name, number + 1)
		else:
			unique_account_name = quickbooks_account_name
		return unique_account_name


	def _log_error(self, execption, data=""):
		import json, traceback
		traceback.print_exc()
		frappe.log_error(title="QuickBooks Migration Error",
			message="\n".join([
				"Data",
				json.dumps(data,
					sort_keys=True,
					indent=4,
					separators=(',', ': ')
				),
				"Exception",
				traceback.format_exc()
			])
		)


	def set_indicator(self, status):
		self.status = status
		self.save()
		frappe.db.commit()
