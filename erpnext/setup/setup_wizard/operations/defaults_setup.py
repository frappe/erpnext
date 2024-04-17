# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import cstr, getdate


# nosemgrep
def set_default_settings(args):
	# enable default currency
	frappe.db.set_value("Currency", args.get("currency"), "enabled", 1)

	global_defaults = frappe.get_doc("Global Defaults", "Global Defaults")
	global_defaults.update(
		{
			"current_fiscal_year": get_fy_details(args.get("fy_start_date"), args.get("fy_end_date")),
			"default_currency": args.get("currency"),
			"default_company": args.get("company_name"),
			"country": args.get("country"),
		}
	)

	global_defaults.save()

	system_settings = frappe.get_doc("System Settings")
	system_settings.email_footer_address = args.get("company_name")
	system_settings.save()

	stock_settings = frappe.get_doc("Stock Settings")
	stock_settings.item_naming_by = "Item Code"
	stock_settings.valuation_method = "FIFO"
	stock_settings.default_warehouse = frappe.db.get_value("Warehouse", {"warehouse_name": _("Stores")})
	stock_settings.stock_uom = _("Nos")
	stock_settings.auto_indent = 1
	stock_settings.auto_insert_price_list_rate_if_missing = 1
	stock_settings.set_qty_in_transactions_based_on_serial_no_input = 1
	stock_settings.save()

	selling_settings = frappe.get_doc("Selling Settings")
	selling_settings.cust_master_name = "Customer Name"
	selling_settings.so_required = "No"
	selling_settings.dn_required = "No"
	selling_settings.allow_multiple_items = 1
	selling_settings.sales_update_frequency = "Each Transaction"
	selling_settings.save()

	buying_settings = frappe.get_doc("Buying Settings")
	buying_settings.supp_master_name = "Supplier Name"
	buying_settings.po_required = "No"
	buying_settings.pr_required = "No"
	buying_settings.maintain_same_rate = 1
	buying_settings.allow_multiple_items = 1
	buying_settings.save()

	delivery_settings = frappe.get_doc("Delivery Settings")
	delivery_settings.dispatch_template = _("Dispatch Notification")
	delivery_settings.save()


def set_no_copy_fields_in_variant_settings():
	# set no copy fields of an item doctype to item variant settings
	doc = frappe.get_doc("Item Variant Settings")
	doc.set_default_fields()
	doc.save()


def create_price_lists(args):
	for pl_type, pl_name in (("Selling", _("Standard Selling")), ("Buying", _("Standard Buying"))):
		frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": pl_name,
				"enabled": 1,
				"buying": 1 if pl_type == "Buying" else 0,
				"selling": 1 if pl_type == "Selling" else 0,
				"currency": args["currency"],
			}
		).insert()


def create_employee_for_self(args):
	if frappe.session.user == "Administrator":
		return

	# create employee for self
	emp = frappe.get_doc(
		{
			"doctype": "Employee",
			"employee_name": " ".join(filter(None, [args.get("first_name"), args.get("last_name")])),
			"user_id": frappe.session.user,
			"status": "Active",
			"company": args.get("company_name"),
		}
	)
	emp.flags.ignore_mandatory = True
	emp.insert(ignore_permissions=True)


def create_territories():
	"""create two default territories, one for home country and one named Rest of the World"""
	from frappe.utils.nestedset import get_root_of

	country = frappe.db.get_default("country")
	root_territory = get_root_of("Territory")

	for name in (country, _("Rest Of The World")):
		if name and not frappe.db.exists("Territory", name):
			frappe.get_doc(
				{
					"doctype": "Territory",
					"territory_name": name.replace("'", ""),
					"parent_territory": root_territory,
					"is_group": "No",
				}
			).insert()


def create_feed_and_todo():
	"""update Activity feed and create todo for creation of item, customer, vendor"""
	return


def get_fy_details(fy_start_date, fy_end_date):
	start_year = getdate(fy_start_date).year
	if start_year == getdate(fy_end_date).year:
		fy = cstr(start_year)
	else:
		fy = cstr(start_year) + "-" + cstr(start_year + 1)
	return fy
