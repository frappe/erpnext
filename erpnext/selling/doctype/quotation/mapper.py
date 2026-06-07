# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt, getdate, nowdate


@frappe.whitelist()
def make_sales_order(
	source_name: str, target_doc: str | Document | None = None, args: str | dict | None = None
):
	if not frappe.db.get_singles_value(
		"Selling Settings", "allow_sales_order_creation_for_expired_quotation"
	):
		quotation = frappe.db.get_value(
			"Quotation", source_name, ["transaction_date", "valid_till"], as_dict=1
		)
		if quotation.valid_till and (
			quotation.valid_till < quotation.transaction_date or quotation.valid_till < getdate(nowdate())
		):
			frappe.throw(_("Validity period of this quotation has ended."))

	return _make_sales_order(source_name, target_doc, args=args)


def _make_sales_order(source_name, target_doc=None, ignore_permissions=False, args=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	customer = _make_customer(source_name, ignore_permissions)
	ordered_items = get_ordered_items(source_name)

	selected_rows = [x.get("name") for x in frappe.flags.get("args", {}).get("selected_items", [])]

	# 0 qty is accepted, as the qty uncertain for some items
	has_unit_price_items = frappe.db.get_value("Quotation", source_name, "has_unit_price_items")

	def is_unit_price_row(source) -> bool:
		return has_unit_price_items and source.qty == 0

	def set_missing_values(source, target):
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name

			# sales team
			if not target.get("sales_team"):
				for d in customer.get("sales_team") or []:
					target.append(
						"sales_team",
						{
							"sales_person": d.sales_person,
							"allocated_percentage": d.allocated_percentage or None,
							"commission_rate": d.commission_rate,
						},
					)

		if source.referral_sales_partner:
			target.sales_partner = source.referral_sales_partner
			target.commission_rate = frappe.get_value(
				"Sales Partner", source.referral_sales_partner, "commission_rate"
			)

		target.flags.ignore_permissions = ignore_permissions
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		balance_stock_qty = obj.stock_qty - ordered_items.get(obj.name, 0.0)
		target.stock_qty = balance_stock_qty if balance_stock_qty > 0 else 0
		target.qty = flt(target.stock_qty) / flt(obj.conversion_factor)

		if obj.against_blanket_order:
			target.against_blanket_order = obj.against_blanket_order
			target.blanket_order = obj.blanket_order
			target.blanket_order_rate = obj.blanket_order_rate

	def can_map_row(item) -> bool:
		"""
		Row mapping from Quotation to Sales order:
		1. If no selections, map all non-alternative rows (that sum up to the grand total)
		2. If selections: Is Alternative Item/Has Alternative Item: Map if selected and adequate qty
		3. If no selections: Simple row: Map if adequate qty
		"""
		if not ((item.stock_qty > ordered_items.get(item.name, 0.0)) or is_unit_price_row(item)):
			return False

		if not selected_rows:
			return not item.is_alternative

		if selected_rows and (item.is_alternative or item.has_alternative_item):
			return item.name in selected_rows

		# Simple row
		return True

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	automatically_fetch_payment_terms = cint(
		frappe.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
	)

	doclist = get_mapped_doc(
		"Quotation",
		source_name,
		{
			"Quotation": {
				"doctype": "Sales Order",
				"validation": {"docstatus": ["=", 1]},
				"field_no_map": ["payment_terms_template"],
			},
			"Quotation Item": {
				"doctype": "Sales Order Item",
				"field_map": {"parent": "prevdoc_docname", "name": "quotation_item"},
				"postprocess": update_item,
				"condition": lambda d: can_map_row(d) and select_item(d),
			},
			"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
			"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
		},
		target_doc,
		set_missing_values,
		ignore_permissions=ignore_permissions,
	)

	if automatically_fetch_payment_terms:
		from erpnext.accounts.services.payment_schedule import PaymentScheduleService

		PaymentScheduleService(doclist).set_payment_schedule()

	return doclist


@frappe.whitelist()
def make_sales_invoice(
	source_name: str, target_doc: str | Document | None = None, args: str | dict | None = None
):
	return _make_sales_invoice(source_name, target_doc, args=args)


def _make_sales_invoice(source_name, target_doc=None, ignore_permissions=False, args=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	customer = _make_customer(source_name, ignore_permissions)

	def set_missing_values(source, target):
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name

		target.flags.ignore_permissions = ignore_permissions
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		target.cost_center = None
		target.stock_qty = flt(obj.qty) * flt(obj.conversion_factor)

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	doclist = get_mapped_doc(
		"Quotation",
		source_name,
		{
			"Quotation": {"doctype": "Sales Invoice", "validation": {"docstatus": ["=", 1]}},
			"Quotation Item": {
				"doctype": "Sales Invoice Item",
				"postprocess": update_item,
				"condition": lambda row: not row.is_alternative and select_item(row),
			},
			"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
			"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
		},
		target_doc,
		set_missing_values,
		ignore_permissions=ignore_permissions,
	)

	return doclist


def _make_customer(source_name, ignore_permissions=False):
	quotation = frappe.db.get_value(
		"Quotation",
		source_name,
		["order_type", "quotation_to", "party_name", "customer_name"],
		as_dict=1,
	)

	if quotation.quotation_to == "Customer":
		return frappe.get_doc("Customer", quotation.party_name)
	elif quotation.quotation_to == "CRM Deal":
		customer_name = frappe.get_value("Customer", {"crm_deal": quotation.party_name})
		if customer_name:
			return frappe.get_doc("Customer", customer_name)

	# Check if a Customer already exists for the Lead or Prospect.
	existing_customer = None
	if quotation.quotation_to == "Lead":
		existing_customer = frappe.db.get_value("Customer", {"lead_name": quotation.party_name})
	elif quotation.quotation_to == "Prospect":
		existing_customer = frappe.db.get_value("Customer", {"prospect_name": quotation.party_name})

	if existing_customer:
		return frappe.get_doc("Customer", existing_customer)

	# If no Customer exists, create a new Customer or Prospect.
	if quotation.quotation_to == "Lead":
		return create_customer_from_lead(quotation.party_name, ignore_permissions=ignore_permissions)
	elif quotation.quotation_to == "Prospect":
		return create_customer_from_prospect(quotation.party_name, ignore_permissions=ignore_permissions)

	return None


def create_customer_from_lead(lead_name, ignore_permissions=False):
	from erpnext.crm.doctype.lead.lead import _make_customer

	customer = _make_customer(lead_name, ignore_permissions=ignore_permissions)
	customer.flags.ignore_permissions = ignore_permissions

	try:
		customer.insert()
		return customer
	except frappe.MandatoryError as e:
		handle_mandatory_error(e, customer, lead_name)


def create_customer_from_prospect(prospect_name, ignore_permissions=False):
	from erpnext.crm.doctype.prospect.prospect import make_customer as make_customer_from_prospect

	customer = make_customer_from_prospect(prospect_name)
	customer.flags.ignore_permissions = ignore_permissions

	try:
		customer.insert()
		return customer
	except frappe.MandatoryError as e:
		handle_mandatory_error(e, customer, prospect_name)


def handle_mandatory_error(e, customer, lead_name):
	from frappe.utils import get_link_to_form

	mandatory_fields = e.args[0].split(":")[1].split(",")
	mandatory_fields = [_(customer.meta.get_label(field.strip())) for field in mandatory_fields]

	frappe.local.message_log = []
	message = _("Could not auto create Customer due to the following missing mandatory field(s):") + "<br>"
	message += "<br><ul><li>" + "</li><li>".join(mandatory_fields) + "</li></ul>"
	message += _("Please create Customer from Lead {0}.").format(get_link_to_form("Lead", lead_name))

	frappe.throw(message, title=_("Mandatory Missing"))


def get_ordered_items(quotation: str) -> frappe._dict:
	return frappe._dict(
		frappe.get_all(
			"Quotation Item",
			{"docstatus": 1, "parent": quotation, "ordered_qty": (">", 0)},
			["name", "ordered_qty"],
			as_list=True,
		)
	)
