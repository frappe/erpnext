# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate, nowdate

from erpnext.buying.utils import validate_for_items
from erpnext.controllers.buying_controller import BuyingController

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class SupplierQuotation(BuyingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.purchase_taxes_and_charges.purchase_taxes_and_charges import (
			PurchaseTaxesandCharges,
		)
		from erpnext.buying.doctype.supplier_quotation_item.supplier_quotation_item import (
			SupplierQuotationItem,
		)

		additional_discount_percentage: DF.Float
		address_display: DF.TextEditor | None
		amended_from: DF.Link | None
		apply_discount_on: DF.Literal["", "Grand Total", "Net Total"]
		auto_repeat: DF.Link | None
		base_discount_amount: DF.Currency
		base_grand_total: DF.Currency
		base_in_words: DF.Data | None
		base_net_total: DF.Currency
		base_rounded_total: DF.Currency
		base_rounding_adjustment: DF.Currency
		base_taxes_and_charges_added: DF.Currency
		base_taxes_and_charges_deducted: DF.Currency
		base_total: DF.Currency
		base_total_taxes_and_charges: DF.Currency
		billing_address: DF.Link | None
		billing_address_display: DF.TextEditor | None
		buying_price_list: DF.Link | None
		company: DF.Link
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		currency: DF.Link
		disable_rounded_total: DF.Check
		discount_amount: DF.Currency
		grand_total: DF.Currency
		group_same_items: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		is_subcontracted: DF.Check
		items: DF.Table[SupplierQuotationItem]
		language: DF.Data | None
		letter_head: DF.Link | None
		named_place: DF.Data | None
		naming_series: DF.Literal["PUR-SQTN-.YYYY.-"]
		net_total: DF.Currency
		opportunity: DF.Link | None
		other_charges_calculation: DF.TextEditor | None
		plc_conversion_rate: DF.Float
		price_list_currency: DF.Link | None
		pricing_rules: DF.Table[PricingRuleDetail]
		project: DF.Link | None
		quotation_number: DF.Data | None
		rounded_total: DF.Currency
		rounding_adjustment: DF.Currency
		select_print_heading: DF.Link | None
		shipping_address: DF.Link | None
		shipping_address_display: DF.TextEditor | None
		shipping_rule: DF.Link | None
		status: DF.Literal["", "Draft", "Submitted", "Stopped", "Cancelled", "Expired"]
		supplier: DF.Link
		supplier_address: DF.Link | None
		supplier_name: DF.Data | None
		tax_category: DF.Link | None
		taxes: DF.Table[PurchaseTaxesandCharges]
		taxes_and_charges: DF.Link | None
		taxes_and_charges_added: DF.Currency
		taxes_and_charges_deducted: DF.Currency
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		title: DF.Data | None
		total: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		transaction_date: DF.Date
		valid_till: DF.Date | None
	# end: auto-generated types

	def validate(self):
		super().validate()

		if not self.status:
			self.status = "Draft"

		from erpnext.controllers.status_updater import validate_status

		validate_status(self.status, ["Draft", "Submitted", "Stopped", "Cancelled"])

		validate_for_items(self)
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_valid_till()

	def on_submit(self):
		self.db_set("status", "Submitted")
		self.update_rfq_supplier_status(1)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self.update_rfq_supplier_status(0)

	def on_trash(self):
		pass

	def validate_with_previous_doc(self):
		super().validate_with_previous_doc(
			{
				"Material Request": {
					"ref_dn_field": "prevdoc_docname",
					"compare_fields": [["company", "="]],
				},
				"Material Request Item": {
					"ref_dn_field": "prevdoc_detail_docname",
					"compare_fields": [["item_code", "="], ["uom", "="]],
					"is_child_table": True,
				},
			}
		)

	def validate_valid_till(self):
		if self.valid_till and getdate(self.valid_till) < getdate(self.transaction_date):
			frappe.throw(_("Valid till Date cannot be before Transaction Date"))

	def update_rfq_supplier_status(self, include_me):
		rfq_list = set([])
		for item in self.items:
			if item.request_for_quotation:
				rfq_list.add(item.request_for_quotation)
		for rfq in rfq_list:
			doc = frappe.get_doc("Request for Quotation", rfq)
			doc_sup = frappe.get_all(
				"Request for Quotation Supplier",
				filters={"parent": doc.name, "supplier": self.supplier},
				fields=["name", "quote_status"],
			)

			doc_sup = doc_sup[0] if doc_sup else None
			if not doc_sup:
				frappe.throw(
					_("Supplier {0} not found in {1}").format(
						self.supplier,
						"<a href='desk/app/Form/Request for Quotation/{0}'> Request for Quotation {0} </a>".format(
							doc.name
						),
					)
				)

			quote_status = _("Received")
			for item in doc.items:
				sqi_count = frappe.db.sql(
					"""
					SELECT
						COUNT(sqi.name) as count
					FROM
						`tabSupplier Quotation Item` as sqi,
						`tabSupplier Quotation` as sq
					WHERE sq.supplier = %(supplier)s
						AND sqi.docstatus = 1
						AND sq.name != %(me)s
						AND sqi.request_for_quotation_item = %(rqi)s
						AND sqi.parent = sq.name""",
					{"supplier": self.supplier, "rqi": item.name, "me": self.name},
					as_dict=1,
				)[0]
				self_count = (
					sum(my_item.request_for_quotation_item == item.name for my_item in self.items)
					if include_me
					else 0
				)
				if (sqi_count.count + self_count) == 0:
					quote_status = _("Pending")

				frappe.db.set_value(
					"Request for Quotation Supplier", doc_sup.name, "quote_status", quote_status
				)


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Supplier Quotation"),
		}
	)

	return list_context


@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		target.run_method("get_schedule_dates")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		target.stock_qty = flt(obj.qty) * flt(obj.conversion_factor)

	doclist = get_mapped_doc(
		"Supplier Quotation",
		source_name,
		{
			"Supplier Quotation": {
				"doctype": "Purchase Order",
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Supplier Quotation Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "supplier_quotation_item"],
					["parent", "supplier_quotation"],
					["material_request", "material_request"],
					["material_request_item", "material_request_item"],
					["sales_order", "sales_order"],
				],
				"postprocess": update_item,
			},
			"Purchase Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
	doc = get_mapped_doc(
		"Supplier Quotation",
		source_name,
		{
			"Supplier Quotation": {
				"doctype": "Purchase Invoice",
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Supplier Quotation Item": {"doctype": "Purchase Invoice Item"},
			"Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges"},
		},
		target_doc,
	)

	return doc


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc(
		"Supplier Quotation",
		source_name,
		{
			"Supplier Quotation": {
				"doctype": "Quotation",
				"field_map": {
					"name": "supplier_quotation",
				},
			},
			"Supplier Quotation Item": {
				"doctype": "Quotation Item",
				"condition": lambda doc: frappe.db.get_value("Item", doc.item_code, "is_sales_item") == 1,
				"add_if_empty": True,
			},
		},
		target_doc,
	)

	return doclist


def set_expired_status():
	frappe.db.sql(
		"""
		UPDATE
			`tabSupplier Quotation` SET `status` = 'Expired'
		WHERE
			`status` not in ('Cancelled', 'Stopped') AND `valid_till` < %s
		""",
		(nowdate()),
	)
