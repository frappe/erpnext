# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate, nowdate

from erpnext.controllers.selling_controller import SellingController

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class Quotation(SellingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.payment_schedule.payment_schedule import PaymentSchedule
		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.sales_taxes_and_charges.sales_taxes_and_charges import (
			SalesTaxesandCharges,
		)
		from erpnext.crm.doctype.competitor_detail.competitor_detail import CompetitorDetail
		from erpnext.selling.doctype.quotation_item.quotation_item import QuotationItem
		from erpnext.setup.doctype.quotation_lost_reason_detail.quotation_lost_reason_detail import (
			QuotationLostReasonDetail,
		)
		from erpnext.stock.doctype.packed_item.packed_item import PackedItem

		additional_discount_percentage: DF.Float
		address_display: DF.SmallText | None
		amended_from: DF.Link | None
		apply_discount_on: DF.Literal["", "Grand Total", "Net Total"]
		auto_repeat: DF.Link | None
		base_discount_amount: DF.Currency
		base_grand_total: DF.Currency
		base_in_words: DF.Data | None
		base_net_total: DF.Currency
		base_rounded_total: DF.Currency
		base_rounding_adjustment: DF.Currency
		base_total: DF.Currency
		base_total_taxes_and_charges: DF.Currency
		campaign: DF.Link | None
		company: DF.Link
		company_address: DF.Link | None
		company_address_display: DF.SmallText | None
		company_contact_person: DF.Link | None
		competitors: DF.TableMultiSelect[CompetitorDetail]
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		conversion_rate: DF.Float
		coupon_code: DF.Link | None
		currency: DF.Link
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		disable_rounded_total: DF.Check
		discount_amount: DF.Currency
		enq_det: DF.Text | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		items: DF.Table[QuotationItem]
		language: DF.Data | None
		letter_head: DF.Link | None
		lost_reasons: DF.TableMultiSelect[QuotationLostReasonDetail]
		named_place: DF.Data | None
		naming_series: DF.Literal["SAL-QTN-.YYYY.-"]
		net_total: DF.Currency
		opportunity: DF.Link | None
		order_lost_reason: DF.SmallText | None
		order_type: DF.Literal["", "Sales", "Maintenance", "Shopping Cart"]
		other_charges_calculation: DF.TextEditor | None
		packed_items: DF.Table[PackedItem]
		party_name: DF.DynamicLink | None
		payment_schedule: DF.Table[PaymentSchedule]
		payment_terms_template: DF.Link | None
		plc_conversion_rate: DF.Float
		price_list_currency: DF.Link
		pricing_rules: DF.Table[PricingRuleDetail]
		quotation_to: DF.Link
		referral_sales_partner: DF.Link | None
		rounded_total: DF.Currency
		rounding_adjustment: DF.Currency
		scan_barcode: DF.Data | None
		select_print_heading: DF.Link | None
		selling_price_list: DF.Link
		shipping_address: DF.SmallText | None
		shipping_address_name: DF.Link | None
		shipping_rule: DF.Link | None
		source: DF.Link | None
		status: DF.Literal[
			"Draft", "Open", "Replied", "Partially Ordered", "Ordered", "Lost", "Cancelled", "Expired"
		]
		supplier_quotation: DF.Link | None
		tax_category: DF.Link | None
		taxes: DF.Table[SalesTaxesandCharges]
		taxes_and_charges: DF.Link | None
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		territory: DF.Link | None
		title: DF.Data | None
		total: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		transaction_date: DF.Date
		valid_till: DF.Date | None
	# end: auto-generated types

	def set_indicator(self):
		if self.docstatus == 1:
			self.indicator_color = "blue"
			self.indicator_title = "Submitted"
		if self.valid_till and getdate(self.valid_till) < getdate(nowdate()):
			self.indicator_color = "gray"
			self.indicator_title = "Expired"

	def validate(self):
		super().validate()
		self.set_status()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_valid_till()
		self.set_customer_name()
		if self.items:
			self.with_items = 1

		from erpnext.stock.doctype.packed_item.packed_item import make_packing_list

		make_packing_list(self)

	def before_submit(self):
		self.set_has_alternative_item()

	def validate_valid_till(self):
		if self.valid_till and getdate(self.valid_till) < getdate(self.transaction_date):
			frappe.throw(_("Valid till date cannot be before transaction date"))

	def set_has_alternative_item(self):
		"""Mark 'Has Alternative Item' for rows."""
		if not any(row.is_alternative for row in self.get("items")):
			return

		items_with_alternatives = self.get_rows_with_alternatives()
		for row in self.get("items"):
			if not row.is_alternative and row.name in items_with_alternatives:
				row.has_alternative_item = 1

	def get_ordered_status(self):
		status = "Open"
		ordered_items = frappe._dict(
			frappe.db.get_all(
				"Sales Order Item",
				{"prevdoc_docname": self.name, "docstatus": 1},
				["item_code", "sum(qty)"],
				group_by="item_code",
				as_list=1,
			)
		)

		if not ordered_items:
			return status

		has_alternatives = any(row.is_alternative for row in self.get("items"))
		self._items = self.get_valid_items() if has_alternatives else self.get("items")

		if any(row.qty > ordered_items.get(row.item_code, 0.0) for row in self._items):
			status = "Partially Ordered"
		else:
			status = "Ordered"

		return status

	def get_valid_items(self):
		"""
		Filters out items in an alternatives set that were not ordered.
		"""

		def is_in_sales_order(row):
			in_sales_order = bool(
				frappe.db.exists(
					"Sales Order Item",
					{"quotation_item": row.name, "item_code": row.item_code, "docstatus": 1},
				)
			)
			return in_sales_order

		def can_map(row) -> bool:
			if row.is_alternative or row.has_alternative_item:
				return is_in_sales_order(row)

			return True

		return list(filter(can_map, self.get("items")))

	def is_fully_ordered(self):
		return self.get_ordered_status() == "Ordered"

	def is_partially_ordered(self):
		return self.get_ordered_status() == "Partially Ordered"

	def update_lead(self):
		if self.quotation_to == "Lead" and self.party_name:
			frappe.get_doc("Lead", self.party_name).set_status(update=True)

	def set_customer_name(self):
		if self.party_name and self.quotation_to == "Customer":
			self.customer_name = frappe.db.get_value("Customer", self.party_name, "customer_name")
		elif self.party_name and self.quotation_to == "Lead":
			lead_name, company_name = frappe.db.get_value(
				"Lead", self.party_name, ["lead_name", "company_name"]
			)
			self.customer_name = company_name or lead_name
		elif self.party_name and self.quotation_to == "Prospect":
			self.customer_name = self.party_name
		elif self.party_name and self.quotation_to == "CRM Deal":
			self.customer_name = frappe.db.get_value("CRM Deal", self.party_name, "organization")

	def update_opportunity(self, status):
		for opportunity in set(d.prevdoc_docname for d in self.get("items")):
			if opportunity:
				self.update_opportunity_status(status, opportunity)

		if self.opportunity:
			self.update_opportunity_status(status)

	def update_opportunity_status(self, status, opportunity=None):
		if not opportunity:
			opportunity = self.opportunity

		opp = frappe.get_doc("Opportunity", opportunity)
		opp.set_status(status=status, update=True)

	@frappe.whitelist()
	def declare_enquiry_lost(self, lost_reasons_list, competitors, detailed_reason=None):
		if not (self.is_fully_ordered() or self.is_partially_ordered()):
			get_lost_reasons = frappe.get_list("Quotation Lost Reason", fields=["name"])
			lost_reasons_lst = [reason.get("name") for reason in get_lost_reasons]
			self.db_set("status", "Lost")

			if detailed_reason:
				self.db_set("order_lost_reason", detailed_reason)

			for reason in lost_reasons_list:
				if reason.get("lost_reason") in lost_reasons_lst:
					self.append("lost_reasons", reason)
				else:
					frappe.throw(
						_("Invalid lost reason {0}, please create a new lost reason").format(
							frappe.bold(reason.get("lost_reason"))
						)
					)

			for competitor in competitors:
				self.append("competitors", competitor)

			self.update_opportunity("Lost")
			self.update_lead()
			self.save()

		else:
			frappe.throw(_("Cannot set as Lost as Sales Order is made."))

	def on_submit(self):
		# Check for Approving Authority
		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total, self
		)

		# update enquiry status
		self.update_opportunity("Quotation")
		self.update_lead()

	def on_cancel(self):
		if self.lost_reasons:
			self.lost_reasons = []
		super().on_cancel()

		# update enquiry status
		self.set_status(update=True)
		self.update_opportunity("Open")
		self.update_lead()

	def print_other_charges(self, docname):
		print_lst = []
		for d in self.get("taxes"):
			lst1 = []
			lst1.append(d.description)
			lst1.append(d.total)
			print_lst.append(lst1)
		return print_lst

	def on_recurring(self, reference_doc, auto_repeat_doc):
		self.valid_till = None

	def get_rows_with_alternatives(self):
		rows_with_alternatives = []
		table_length = len(self.get("items"))

		for idx, row in enumerate(self.get("items")):
			if row.is_alternative:
				continue

			if idx == (table_length - 1):
				break

			if self.get("items")[idx + 1].is_alternative:
				rows_with_alternatives.append(row.name)

		return rows_with_alternatives


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Quotations"),
		}
	)

	return list_context


@frappe.whitelist()
def make_sales_order(source_name: str, target_doc=None):
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

	return _make_sales_order(source_name, target_doc)


def _make_sales_order(source_name, target_doc=None, ignore_permissions=False):
	customer = _make_customer(source_name, ignore_permissions)
	ordered_items = frappe._dict(
		frappe.db.get_all(
			"Sales Order Item",
			{"prevdoc_docname": source_name, "docstatus": 1},
			["item_code", "sum(qty)"],
			group_by="item_code",
			as_list=1,
		)
	)

	selected_rows = [x.get("name") for x in frappe.flags.get("args", {}).get("selected_items", [])]

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
		balance_qty = obj.qty - ordered_items.get(obj.item_code, 0.0)
		target.qty = balance_qty if balance_qty > 0 else 0
		target.stock_qty = flt(target.qty) * flt(obj.conversion_factor)

		if obj.against_blanket_order:
			target.against_blanket_order = obj.against_blanket_order
			target.blanket_order = obj.blanket_order
			target.blanket_order_rate = obj.blanket_order_rate

	def can_map_row(item) -> bool:
		"""
		Row mapping from Quotation to Sales order:
		1. If no selections, map all non-alternative rows (that sum up to the grand total)
		2. If selections: Is Alternative Item/Has Alternative Item: Map if selected and adequate qty
		3. If selections: Simple row: Map if adequate qty
		"""
		balance_qty = item.qty - ordered_items.get(item.item_code, 0.0)
		if balance_qty <= 0:
			return False

		has_qty = balance_qty

		if not selected_rows:
			return not item.is_alternative

		if selected_rows and (item.is_alternative or item.has_alternative_item):
			return (item.name in selected_rows) and has_qty

		# Simple row
		return has_qty

	doclist = get_mapped_doc(
		"Quotation",
		source_name,
		{
			"Quotation": {"doctype": "Sales Order", "validation": {"docstatus": ["=", 1]}},
			"Quotation Item": {
				"doctype": "Sales Order Item",
				"field_map": {"parent": "prevdoc_docname", "name": "quotation_item"},
				"postprocess": update_item,
				"condition": can_map_row,
			},
			"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
			"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
			"Payment Schedule": {"doctype": "Payment Schedule", "add_if_empty": True},
		},
		target_doc,
		set_missing_values,
		ignore_permissions=ignore_permissions,
	)

	return doclist


def set_expired_status():
	# filter out submitted non expired quotations whose validity has been ended
	cond = "`tabQuotation`.docstatus = 1 and `tabQuotation`.status NOT IN ('Expired', 'Lost') and `tabQuotation`.valid_till < %s"
	# check if those QUO have SO against it
	so_against_quo = """
		SELECT
			so.name FROM `tabSales Order` so, `tabSales Order Item` so_item
		WHERE
			so_item.docstatus = 1 and so.docstatus = 1
			and so_item.parent = so.name
			and so_item.prevdoc_docname = `tabQuotation`.name"""

	# if not exists any SO, set status as Expired
	frappe.db.multisql(
		{
			"mariadb": f"""UPDATE `tabQuotation`  SET `tabQuotation`.status = 'Expired' WHERE {cond} and not exists({so_against_quo})""",
			"postgres": f"""UPDATE `tabQuotation` SET status = 'Expired' FROM `tabSales Order`, `tabSales Order Item` WHERE {cond} and not exists({so_against_quo})""",
		},
		(nowdate()),
	)


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	return _make_sales_invoice(source_name, target_doc)


def _make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
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

	doclist = get_mapped_doc(
		"Quotation",
		source_name,
		{
			"Quotation": {"doctype": "Sales Invoice", "validation": {"docstatus": ["=", 1]}},
			"Quotation Item": {
				"doctype": "Sales Invoice Item",
				"postprocess": update_item,
				"condition": lambda row: not row.is_alternative,
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
