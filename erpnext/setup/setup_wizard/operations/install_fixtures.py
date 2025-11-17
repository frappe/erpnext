# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
import os
from pathlib import Path

import frappe
from frappe.desk.doctype.global_search_settings.global_search_settings import (
	update_global_search_doctypes,
)
from frappe.desk.page.setup_wizard.setup_wizard import make_records
from frappe.utils import cstr, getdate

from erpnext.accounts.doctype.account.account import RootNotEditable
from erpnext.regional.address_template.setup import set_up_address_templates
from erpnext.setup.utils import identity as _


def read_lines(filename: str) -> list[str]:
	"""Return a list of lines from a file in the data directory."""
	return (Path(__file__).parent.parent / "data" / filename).read_text().splitlines()


def install(country=None):
	records = [
		# ensure at least an empty Address Template exists for this Country
		{"doctype": "Address Template", "country": country},
		# item group
		{
			"doctype": "Item Group",
			"item_group_name": _("All Item Groups"),
			"is_group": 1,
			"parent_item_group": "",
		},
		{
			"doctype": "Item Group",
			"item_group_name": _("Products"),
			"is_group": 0,
			"parent_item_group": _("All Item Groups"),
			"show_in_website": 1,
		},
		{
			"doctype": "Item Group",
			"item_group_name": _("Raw Material"),
			"is_group": 0,
			"parent_item_group": _("All Item Groups"),
		},
		{
			"doctype": "Item Group",
			"item_group_name": _("Services"),
			"is_group": 0,
			"parent_item_group": _("All Item Groups"),
		},
		{
			"doctype": "Item Group",
			"item_group_name": _("Sub Assemblies"),
			"is_group": 0,
			"parent_item_group": _("All Item Groups"),
		},
		{
			"doctype": "Item Group",
			"item_group_name": _("Consumable"),
			"is_group": 0,
			"parent_item_group": _("All Item Groups"),
		},
		# Stock Entry Type
		{
			"doctype": "Stock Entry Type",
			"name": _("Material Issue"),
			"purpose": "Material Issue",
			"is_standard": 1,
		},
		{
			"doctype": "Stock Entry Type",
			"name": _("Material Receipt"),
			"purpose": "Material Receipt",
			"is_standard": 1,
		},
		{
			"doctype": "Stock Entry Type",
			"name": _("Material Transfer"),
			"purpose": "Material Transfer",
			"is_standard": 1,
		},
		{
			"doctype": "Stock Entry Type",
			"name": _("Manufacture"),
			"purpose": "Manufacture",
			"is_standard": 1,
		},
		{
			"doctype": "Stock Entry Type",
			"name": _("Repack"),
			"purpose": "Repack",
			"is_standard": 1,
		},
		{"doctype": "Stock Entry Type", "name": "Disassemble", "purpose": "Disassemble", "is_standard": 1},
		{
			"doctype": "Stock Entry Type",
			"name": _("Send to Subcontractor"),
			"purpose": "Send to Subcontractor",
			"is_standard": 1,
		},
		{
			"doctype": "Stock Entry Type",
			"name": _("Material Transfer for Manufacture"),
			"purpose": "Material Transfer for Manufacture",
			"is_standard": 1,
		},
		{
			"doctype": "Stock Entry Type",
			"name": _("Material Consumption for Manufacture"),
			"purpose": "Material Consumption for Manufacture",
			"is_standard": 1,
		},
		{
			"doctype": "Stock Entry Type",
			"name": _("Receive from Customer"),
			"purpose": "Receive from Customer",
			"is_standard": 1,
		},
		{
			"doctype": "Stock Entry Type",
			"name": _("Return Raw Material to Customer"),
			"purpose": "Return Raw Material to Customer",
			"is_standard": 1,
		},
		{
			"doctype": "Stock Entry Type",
			"name": _("Subcontracting Delivery"),
			"purpose": "Subcontracting Delivery",
			"is_standard": 1,
		},
		{
			"doctype": "Stock Entry Type",
			"name": _("Subcontracting Return"),
			"purpose": "Subcontracting Return",
			"is_standard": 1,
		},
		# territory: with two default territories, one for home country and one named Rest of the World
		{
			"doctype": "Territory",
			"territory_name": _("All Territories"),
			"is_group": 1,
			"name": _("All Territories"),
			"parent_territory": "",
		},
		{
			"doctype": "Territory",
			"territory_name": country.replace("'", ""),
			"is_group": 0,
			"parent_territory": _("All Territories"),
		},
		{
			"doctype": "Territory",
			"territory_name": _("Rest Of The World"),
			"is_group": 0,
			"parent_territory": _("All Territories"),
		},
		# customer group
		{
			"doctype": "Customer Group",
			"customer_group_name": _("All Customer Groups"),
			"is_group": 1,
			"name": _("All Customer Groups"),
			"parent_customer_group": "",
		},
		{
			"doctype": "Customer Group",
			"customer_group_name": _("Individual"),
			"is_group": 0,
			"parent_customer_group": _("All Customer Groups"),
		},
		{
			"doctype": "Customer Group",
			"customer_group_name": _("Commercial"),
			"is_group": 0,
			"parent_customer_group": _("All Customer Groups"),
		},
		{
			"doctype": "Customer Group",
			"customer_group_name": _("Non Profit"),
			"is_group": 0,
			"parent_customer_group": _("All Customer Groups"),
		},
		{
			"doctype": "Customer Group",
			"customer_group_name": _("Government"),
			"is_group": 0,
			"parent_customer_group": _("All Customer Groups"),
		},
		# supplier group
		{
			"doctype": "Supplier Group",
			"supplier_group_name": _("All Supplier Groups"),
			"is_group": 1,
			"name": _("All Supplier Groups"),
			"parent_supplier_group": "",
		},
		{
			"doctype": "Supplier Group",
			"supplier_group_name": _("Services"),
			"is_group": 0,
			"parent_supplier_group": _("All Supplier Groups"),
		},
		{
			"doctype": "Supplier Group",
			"supplier_group_name": _("Local"),
			"is_group": 0,
			"parent_supplier_group": _("All Supplier Groups"),
		},
		{
			"doctype": "Supplier Group",
			"supplier_group_name": _("Raw Material"),
			"is_group": 0,
			"parent_supplier_group": _("All Supplier Groups"),
		},
		{
			"doctype": "Supplier Group",
			"supplier_group_name": _("Electrical"),
			"is_group": 0,
			"parent_supplier_group": _("All Supplier Groups"),
		},
		{
			"doctype": "Supplier Group",
			"supplier_group_name": _("Hardware"),
			"is_group": 0,
			"parent_supplier_group": _("All Supplier Groups"),
		},
		{
			"doctype": "Supplier Group",
			"supplier_group_name": _("Pharmaceutical"),
			"is_group": 0,
			"parent_supplier_group": _("All Supplier Groups"),
		},
		{
			"doctype": "Supplier Group",
			"supplier_group_name": _("Distributor"),
			"is_group": 0,
			"parent_supplier_group": _("All Supplier Groups"),
		},
		# Sales Person
		{
			"doctype": "Sales Person",
			"sales_person_name": _("Sales Team"),
			"is_group": 1,
			"parent_sales_person": "",
		},
		# Mode of Payment
		{
			"doctype": "Mode of Payment",
			"mode_of_payment": "Check" if country == "United States" else _("Cheque"),
			"type": "Bank",
		},
		{"doctype": "Mode of Payment", "mode_of_payment": _("Cash"), "type": "Cash"},
		{"doctype": "Mode of Payment", "mode_of_payment": _("Credit Card"), "type": "Bank"},
		{"doctype": "Mode of Payment", "mode_of_payment": _("Wire Transfer"), "type": "Bank"},
		{"doctype": "Mode of Payment", "mode_of_payment": _("Bank Draft"), "type": "Bank"},
		# Activity Type
		{"doctype": "Activity Type", "activity_type": _("Planning")},
		{"doctype": "Activity Type", "activity_type": _("Research")},
		{"doctype": "Activity Type", "activity_type": _("Proposal Writing")},
		{"doctype": "Activity Type", "activity_type": _("Execution")},
		{"doctype": "Activity Type", "activity_type": _("Communication")},
		{
			"doctype": "Item Attribute",
			"attribute_name": _("Size"),
			"item_attribute_values": [
				{"attribute_value": _("Extra Small"), "abbr": "XS"},
				{"attribute_value": _("Small"), "abbr": "S"},
				{"attribute_value": _("Medium"), "abbr": "M"},
				{"attribute_value": _("Large"), "abbr": "L"},
				{"attribute_value": _("Extra Large"), "abbr": "XL"},
			],
		},
		{
			"doctype": "Item Attribute",
			"attribute_name": _("Colour"),
			"item_attribute_values": [
				{"attribute_value": _("Red"), "abbr": "RED"},
				{"attribute_value": _("Green"), "abbr": "GRE"},
				{"attribute_value": _("Blue"), "abbr": "BLU"},
				{"attribute_value": _("Black"), "abbr": "BLA"},
				{"attribute_value": _("White"), "abbr": "WHI"},
			],
		},
		# Issue Priority
		{"doctype": "Issue Priority", "name": _("Low")},
		{"doctype": "Issue Priority", "name": _("Medium")},
		{"doctype": "Issue Priority", "name": _("High")},
		{"doctype": "Party Type", "party_type": "Customer", "account_type": "Receivable"},
		{"doctype": "Party Type", "party_type": "Supplier", "account_type": "Payable"},
		{"doctype": "Party Type", "party_type": "Employee", "account_type": "Payable"},
		{"doctype": "Party Type", "party_type": "Shareholder", "account_type": "Payable"},
		{"doctype": "Opportunity Type", "name": _("Sales")},
		{"doctype": "Opportunity Type", "name": _("Support")},
		{"doctype": "Opportunity Type", "name": _("Maintenance")},
		{"doctype": "Project Type", "project_type": _("Internal")},
		{"doctype": "Project Type", "project_type": _("External")},
		{"doctype": "Project Type", "project_type": _("Other")},
		{"doctype": "Print Heading", "print_heading": _("Credit Note")},
		{"doctype": "Print Heading", "print_heading": _("Debit Note")},
		# Share Management
		{"doctype": "Share Type", "title": _("Equity")},
		{"doctype": "Share Type", "title": _("Preference")},
		# Market Segments
		{"doctype": "Market Segment", "market_segment": _("Lower Income")},
		{"doctype": "Market Segment", "market_segment": _("Middle Income")},
		{"doctype": "Market Segment", "market_segment": _("Upper Income")},
		# Warehouse Type
		{"doctype": "Warehouse Type", "name": "Transit"},
		{"doctype": "Workstation Operating Component", "component_name": _("Electricity")},
		{"doctype": "Workstation Operating Component", "component_name": _("Consumables")},
		{"doctype": "Workstation Operating Component", "component_name": _("Rent")},
		{"doctype": "Workstation Operating Component", "component_name": _("Wages")},
	]

	for doctype, title_field, filename in (
		("Designation", "designation_name", "designation.txt"),
		("Sales Stage", "stage_name", "sales_stage.txt"),
		("Industry Type", "industry", "industry_type.txt"),
		("UTM Source", "name", "marketing_source.txt"),
		("Sales Partner Type", "sales_partner_type", "sales_partner_type.txt"),
	):
		records += [{"doctype": doctype, title_field: title} for title in read_lines(filename)]

	base_path = frappe.get_app_path("erpnext", "stock", "doctype")
	response = frappe.read_file(os.path.join(base_path, "delivery_trip/dispatch_notification_template.html"))

	records += [
		{
			"doctype": "Email Template",
			"name": _("Dispatch Notification"),
			"response": response,
			"subject": _("Your order is out for delivery!"),
			"owner": frappe.session.user,
		}
	]

	# Records for the Supplier Scorecard
	from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import make_default_records

	make_default_records()
	make_records(records)
	set_up_address_templates(default_country=country)
	update_selling_defaults()
	update_buying_defaults()
	add_uom_data()
	update_item_variant_settings()
	update_global_search_doctypes()


def update_selling_defaults():
	selling_settings = frappe.get_doc("Selling Settings")
	selling_settings.cust_master_name = "Customer Name"
	selling_settings.so_required = "No"
	selling_settings.dn_required = "No"
	selling_settings.allow_multiple_items = 1
	selling_settings.sales_update_frequency = "Each Transaction"
	selling_settings.save()


def update_buying_defaults():
	buying_settings = frappe.get_doc("Buying Settings")
	buying_settings.supp_master_name = "Supplier Name"
	buying_settings.po_required = "No"
	buying_settings.pr_required = "No"
	buying_settings.maintain_same_rate = 1
	buying_settings.allow_multiple_items = 1
	buying_settings.save()


def update_item_variant_settings():
	# set no copy fields of an item doctype to item variant settings
	doc = frappe.get_doc("Item Variant Settings")
	doc.set_default_fields()
	doc.save()


def add_uom_data():
	# add UOMs
	uoms = json.loads(
		open(frappe.get_app_path("erpnext", "setup", "setup_wizard", "data", "uom_data.json")).read()
	)
	for d in uoms:
		if not frappe.db.exists("UOM", d.get("uom_name")):
			doc = frappe.new_doc("UOM")
			doc.update(d)
			doc.insert(ignore_permissions=True)

	# bootstrap uom conversion factors
	uom_conversions = json.loads(
		open(
			frappe.get_app_path("erpnext", "setup", "setup_wizard", "data", "uom_conversion_data.json")
		).read()
	)
	for d in uom_conversions:
		if not frappe.db.exists("UOM Category", d.get("category")):
			frappe.get_doc({"doctype": "UOM Category", "category_name": d.get("category")}).db_insert()

		if not frappe.db.exists(
			"UOM Conversion Factor",
			{"from_uom": d.get("from_uom"), "to_uom": d.get("to_uom")},
		):
			frappe.get_doc(
				{
					"doctype": "UOM Conversion Factor",
					"category": d.get("category"),
					"from_uom": d.get("from_uom"),
					"to_uom": d.get("to_uom"),
					"value": d.get("value"),
				}
			).db_insert()


def add_market_segments():
	records = [
		# Market Segments
		{"doctype": "Market Segment", "market_segment": _("Lower Income")},
		{"doctype": "Market Segment", "market_segment": _("Middle Income")},
		{"doctype": "Market Segment", "market_segment": _("Upper Income")},
	]

	make_records(records)


def add_sale_stages():
	# Sale Stages
	records = [
		{"doctype": "Sales Stage", "stage_name": _("Prospecting")},
		{"doctype": "Sales Stage", "stage_name": _("Qualification")},
		{"doctype": "Sales Stage", "stage_name": _("Needs Analysis")},
		{"doctype": "Sales Stage", "stage_name": _("Value Proposition")},
		{"doctype": "Sales Stage", "stage_name": _("Identifying Decision Makers")},
		{"doctype": "Sales Stage", "stage_name": _("Perception Analysis")},
		{"doctype": "Sales Stage", "stage_name": _("Proposal/Price Quote")},
		{"doctype": "Sales Stage", "stage_name": _("Negotiation/Review")},
	]
	for sales_stage in records:
		frappe.get_doc(sales_stage).db_insert()


def install_company(args):
	records = [
		# Fiscal Year
		{
			"doctype": "Fiscal Year",
			"year": get_fy_details(args.fy_start_date, args.fy_end_date),
			"year_start_date": args.fy_start_date,
			"year_end_date": args.fy_end_date,
		},
		# Company
		{
			"doctype": "Company",
			"company_name": args.company_name,
			"enable_perpetual_inventory": 1,
			"abbr": args.company_abbr,
			"default_currency": args.currency,
			"country": args.country,
			"create_chart_of_accounts_based_on": "Standard Template",
			"chart_of_accounts": args.chart_of_accounts,
			"domain": args.domain,
		},
	]

	make_records(records)


def install_defaults(args=None):  # nosemgrep
	records = [
		# Price Lists
		{
			"doctype": "Price List",
			"price_list_name": _("Standard Buying"),
			"enabled": 1,
			"buying": 1,
			"selling": 0,
			"currency": args.currency,
		},
		{
			"doctype": "Price List",
			"price_list_name": _("Standard Selling"),
			"enabled": 1,
			"buying": 0,
			"selling": 1,
			"currency": args.currency,
		},
	]

	make_records(records)

	# enable default currency
	frappe.db.set_value("Currency", args.get("currency"), "enabled", 1)
	frappe.db.set_single_value("Stock Settings", "email_footer_address", args.get("company_name"))

	set_global_defaults(args)
	update_stock_settings()

	args.update({"set_default": 1})
	create_bank_account(args)


def set_global_defaults(kwargs):
	global_defaults = frappe.get_doc("Global Defaults", "Global Defaults")
	company = frappe.db.get_value(
		"Company",
		{"company_name": kwargs.get("company_name")},
		"name",
	)

	global_defaults.update(
		{
			"default_currency": kwargs.get("currency"),
			"default_company": company,
			"country": kwargs.get("country"),
		}
	)

	global_defaults.save()


def update_stock_settings():
	stock_settings = frappe.get_doc("Stock Settings")
	stock_settings.item_naming_by = "Item Code"
	stock_settings.valuation_method = "FIFO"
	stock_settings.default_warehouse = frappe.db.get_value("Warehouse", {"warehouse_name": _("Stores")})
	stock_settings.stock_uom = "Nos"
	stock_settings.auto_indent = 1
	stock_settings.auto_insert_price_list_rate_if_missing = 1
	stock_settings.update_price_list_based_on = "Rate"
	stock_settings.set_qty_in_transactions_based_on_serial_no_input = 1
	stock_settings.flags.ignore_permissions = True
	stock_settings.save()


def create_bank_account(args, demo=False):
	if not args.get("bank_account"):
		if not demo:
			return
		args["bank_account"] = _("Demo Bank Account")

	company_name = args.get("company_name")
	bank_account_group = frappe.db.get_value(
		"Account",
		{"account_type": "Bank", "is_group": 1, "root_type": "Asset", "company": company_name},
	)
	if bank_account_group:
		bank_account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": args.get("bank_account"),
				"parent_account": bank_account_group,
				"is_group": 0,
				"company": company_name,
				"account_type": "Bank",
			}
		)
		try:
			doc = bank_account.insert()

			if args.get("set_default"):
				frappe.db.set_value(
					"Company",
					args.get("company_name"),
					"default_bank_account",
					bank_account.name,
					update_modified=False,
				)

			return doc

		except RootNotEditable:
			frappe.throw(frappe._("Bank account cannot be named as {0}").format(args.get("bank_account")))
		except frappe.DuplicateEntryError:
			# bank account same as a CoA entry
			pass


def get_fy_details(fy_start_date, fy_end_date):
	start_year = getdate(fy_start_date).year
	if start_year == getdate(fy_end_date).year:
		fy = cstr(start_year)
	else:
		fy = cstr(start_year) + "-" + cstr(start_year + 1)
	return fy
