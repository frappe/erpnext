# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from erpnext.buying.utils import validate_for_items
from erpnext.controllers.buying_controller import BuyingController

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class SupplierQuotation(BuyingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.item_wise_tax_detail.item_wise_tax_detail import ItemWiseTaxDetail
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
		has_unit_price_items: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		is_subcontracted: DF.Check
		item_wise_tax_details: DF.Table[ItemWiseTaxDetail]
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

	def before_validate(self):
		self.set_has_unit_price_items()
		self.flags.allow_zero_qty = self.has_unit_price_items

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

	def set_has_unit_price_items(self):
		"""
		If permitted in settings and any item has 0 qty, the SQ has unit price items.
		"""
		if not frappe.db.get_single_value("Buying Settings", "allow_zero_qty_in_supplier_quotation"):
			return

		self.has_unit_price_items = any(
			not row.qty for row in self.get("items") if (row.item_code and not row.qty)
		)

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
		from frappe.query_builder.functions import Count

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

			SQ = frappe.qb.DocType("Supplier Quotation")
			SQ_Item = frappe.qb.DocType("Supplier Quotation Item")

			for item in doc.items:
				query = (
					frappe.qb.from_(SQ_Item)
					.join(SQ)
					.on(SQ_Item.parent == SQ.name)
					.select(Count(SQ_Item.name).as_("count"))
					.where(SQ.supplier == self.supplier)
					.where(SQ_Item.docstatus == 1)
					.where(SQ.name != self.name)
					.where(SQ_Item.request_for_quotation_item == item.name)
				)

				result = query.run(as_dict=True)
				sqi_count = result[0] if result else frappe._dict(count=0)

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
			"list_template": "templates/includes/list/list.html",
		}
	)

	return list_context


def set_expired_status():
	frappe.db.set_value(
		"Supplier Quotation",
		filters={"status": ["not in", ["Cancelled", "Stopped"]], "valid_till": ["<", nowdate()]},
		fieldname="status",
		value="Expired",
		update_modified=True,
	)


def get_purchased_items(supplier_quotation: str):
	return frappe._dict(
		frappe.get_all(
			"Purchase Order Item",
			filters={"supplier_quotation": supplier_quotation, "docstatus": 1},
			fields=["supplier_quotation_item", {"SUM": "qty"}],
			group_by="supplier_quotation_item",
			as_list=1,
		)
	)
