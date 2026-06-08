# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from typing import Literal

import frappe
import frappe.utils
from frappe import _, qb
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt, get_link_to_form, getdate

from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)
from erpnext.controllers.selling_controller import SellingController
from erpnext.manufacturing.doctype.blanket_order.blanket_order import (
	validate_against_blanket_order,
)
from erpnext.selling.doctype.customer.customer import check_credit_limit
from erpnext.selling.doctype.sales_order.services.delivery_schedule import DeliveryScheduleService
from erpnext.selling.doctype.sales_order.services.status import StatusService
from erpnext.selling.doctype.sales_order.services.stock_reservation import StockReservationService
from erpnext.selling.doctype.sales_order.services.subcontracting import SubcontractingService
from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import has_reserved_stock
from erpnext.stock.get_item_details import get_default_bom

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class WarehouseRequired(frappe.ValidationError):
	pass


class SalesOrder(SellingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.item_wise_tax_detail.item_wise_tax_detail import ItemWiseTaxDetail
		from erpnext.accounts.doctype.payment_schedule.payment_schedule import PaymentSchedule
		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.sales_taxes_and_charges.sales_taxes_and_charges import (
			SalesTaxesandCharges,
		)
		from erpnext.selling.doctype.sales_order_item.sales_order_item import SalesOrderItem
		from erpnext.selling.doctype.sales_team.sales_team import SalesTeam
		from erpnext.stock.doctype.packed_item.packed_item import PackedItem

		additional_discount_percentage: DF.Float
		address_display: DF.TextEditor | None
		advance_paid: DF.Currency
		advance_payment_status: DF.Literal["Not Requested", "Requested", "Partially Paid", "Fully Paid"]
		amended_from: DF.Link | None
		amount_eligible_for_commission: DF.Currency
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
		billing_status: DF.Literal["Not Billed", "Fully Billed", "Partly Billed", "Closed"]
		commission_rate: DF.Float
		company: DF.Link
		company_address: DF.Link | None
		company_address_display: DF.TextEditor | None
		company_contact_person: DF.Link | None
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		contact_phone: DF.Data | None
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		coupon_code: DF.Link | None
		currency: DF.Link
		customer: DF.Link
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		delivery_date: DF.Date | None
		delivery_status: DF.Literal[
			"Not Delivered", "Fully Delivered", "Partly Delivered", "Closed", "Not Applicable"
		]
		disable_rounded_total: DF.Check
		discount_amount: DF.Currency
		dispatch_address: DF.TextEditor | None
		dispatch_address_name: DF.Link | None
		from_date: DF.Date | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		has_unit_price_items: DF.Check
		ignore_default_payment_terms_template: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		inter_company_order_reference: DF.Link | None
		is_internal_customer: DF.Check
		is_subcontracted: DF.Check
		item_wise_tax_details: DF.Table[ItemWiseTaxDetail]
		items: DF.Table[SalesOrderItem]
		language: DF.Link | None
		letter_head: DF.Link | None
		loyalty_amount: DF.Currency
		loyalty_points: DF.Int
		named_place: DF.Data | None
		naming_series: DF.Literal["SAL-ORD-.YYYY.-"]
		net_total: DF.Currency
		order_type: DF.Literal["", "Sales", "Maintenance", "Shopping Cart"]
		other_charges_calculation: DF.TextEditor | None
		packed_items: DF.Table[PackedItem]
		party_account_currency: DF.Link | None
		payment_schedule: DF.Table[PaymentSchedule]
		payment_terms_template: DF.Link | None
		per_billed: DF.Percent
		per_delivered: DF.Percent
		per_picked: DF.Percent
		plc_conversion_rate: DF.Float
		po_date: DF.Date | None
		po_no: DF.Data | None
		price_list_currency: DF.Link
		pricing_rules: DF.Table[PricingRuleDetail]
		project: DF.Link | None
		represents_company: DF.Link | None
		reserve_stock: DF.Check
		rounded_total: DF.Currency
		rounding_adjustment: DF.Currency
		sales_partner: DF.Link | None
		sales_team: DF.Table[SalesTeam]
		scan_barcode: DF.Data | None
		select_print_heading: DF.Link | None
		selling_price_list: DF.Link
		set_warehouse: DF.Link | None
		shipping_address: DF.TextEditor | None
		shipping_address_name: DF.Link | None
		shipping_rule: DF.Link | None
		skip_delivery_note: DF.Check
		status: DF.Literal[
			"",
			"Draft",
			"On Hold",
			"To Pay",
			"To Deliver and Bill",
			"To Bill",
			"To Deliver",
			"Completed",
			"Cancelled",
			"Closed",
		]
		tax_category: DF.Link | None
		tax_id: DF.Data | None
		taxes: DF.Table[SalesTaxesandCharges]
		taxes_and_charges: DF.Link | None
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		territory: DF.Link | None
		title: DF.Data | None
		to_date: DF.Date | None
		total: DF.Currency
		total_commission: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		transaction_date: DF.Date
		transaction_time: DF.Time | None
		utm_campaign: DF.Link | None
		utm_content: DF.Data | None
		utm_medium: DF.Link | None
		utm_source: DF.Link | None
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.status_updater = [
			{
				"source_dt": "Sales Order Item",
				"target_dt": "Quotation Item",
				"join_field": "quotation_item",
				"target_field": "ordered_qty",
				"target_ref_field": "stock_qty",
				"source_field": "stock_qty",
			}
		]

	def onload(self) -> None:
		super().onload()

		if self.get("is_subcontracted"):
			self.set_onload("can_update_items", self.can_update_items())
			return

		if frappe.get_single_value("Stock Settings", "enable_stock_reservation"):
			if self.has_unreserved_stock() or self.has_unreserved_stock("packed_items"):
				self.set_onload("has_unreserved_stock", True)

		if has_reserved_stock(self.doctype, self.name):
			self.set_onload("has_reserved_stock", True)

	def can_update_items(self) -> bool:
		return SubcontractingService(self).can_update_items()

	def before_validate(self):
		self.set_has_unit_price_items()
		self.flags.allow_zero_qty = self.has_unit_price_items

	def validate(self):
		super().validate()
		self.validate_delivery_date()
		self.validate_proj_cust()
		self.validate_po()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_for_items()
		self.validate_warehouse()
		self.validate_drop_ship()
		StockReservationService(self).validate_reserved_stock()
		self.validate_serial_no_based_delivery()
		validate_against_blanket_order(self)
		validate_inter_company_party(
			self.doctype, self.customer, self.company, self.inter_company_order_reference
		)

		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code

			validate_coupon_code(self.coupon_code)

		make_packing_list(self)

		self.validate_with_previous_doc()
		SubcontractingService(self).validate_fg_item_for_subcontracting()
		self.set_status()

		StatusService(self).set_default_statuses()

		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		if not self.get("is_subcontracted"):
			StockReservationService(self).enable_auto_reserve_stock()

	def set_has_unit_price_items(self):
		"""
		If permitted in settings and any item has 0 qty, the SO has unit price items.
		"""
		if not frappe.get_single_value("Selling Settings", "allow_zero_qty_in_sales_order"):
			return

		self.has_unit_price_items = any(
			not row.qty for row in self.get("items") if (row.item_code and not row.qty)
		)

	def validate_po(self):
		# validate p.o date v/s delivery date
		if self.po_date and not self.skip_delivery_note:
			for d in self.get("items"):
				if d.delivery_date and getdate(self.po_date) > getdate(d.delivery_date):
					frappe.throw(
						_("Row #{0}: Expected Delivery Date cannot be before Purchase Order Date").format(
							d.idx
						)
					)

		if self.po_no and self.customer and not self.skip_delivery_note:
			so = frappe.db.get_value(
				"Sales Order",
				filters={
					"po_no": self.po_no,
					"name": ["!=", self.name],
					"docstatus": ["<", 2],
					"customer": self.customer,
				},
				fieldname="name",
			)
			if so:
				if cint(
					frappe.get_single_value("Selling Settings", "allow_against_multiple_purchase_orders")
				):
					frappe.msgprint(
						_(
							"Warning: Sales Order {0} already exists against Customer's Purchase Order {1}"
						).format(frappe.bold(so), frappe.bold(self.po_no)),
						alert=True,
					)
				else:
					frappe.throw(
						_(
							"Sales Order {0} already exists against Customer's Purchase Order {1}. To allow multiple Sales Orders, Enable {2} in {3}"
						).format(
							frappe.bold(so),
							frappe.bold(self.po_no),
							frappe.bold(
								_("'Allow Multiple Sales Orders Against a Customer's Purchase Order'")
							),
							get_link_to_form("Selling Settings", "Selling Settings"),
						)
					)

	def validate_for_items(self):
		item_warehouse_pairs = [
			(d.item_code, d.warehouse) for d in self.get("items") if d.item_code and d.warehouse
		]

		bin_data = {}
		if item_warehouse_pairs:
			bins = frappe.get_all(
				"Bin",
				fields=["item_code", "warehouse", "projected_qty"],
				filters={"item_code": ["in", [p[0] for p in item_warehouse_pairs]]},
			)
			bin_data = {(b.item_code, b.warehouse): flt(b.projected_qty) for b in bins}

		for d in self.get("items"):
			d.transaction_date = self.transaction_date
			d.projected_qty = bin_data.get((d.item_code, d.warehouse), 0.0)

	def product_bundle_has_stock_item(self, product_bundle):
		"""Returns true if the active bundle for `product_bundle` (a parent item code) has a stock item"""
		from erpnext.selling.doctype.product_bundle.product_bundle import get_active_product_bundle

		bundle_name = get_active_product_bundle(product_bundle)
		if not bundle_name:
			return False

		bundle_items = frappe.get_all(
			"Product Bundle Item", filters={"parent": bundle_name}, pluck="item_code"
		)

		if not bundle_items:
			return False

		return frappe.db.exists("Item", {"name": ["in", bundle_items], "is_stock_item": 1}) is not None

	def validate_sales_mntc_quotation(self):
		quotation_names = [d.prevdoc_docname for d in self.get("items") if d.prevdoc_docname]

		if not quotation_names:
			return

		valid_quotations = frappe.get_all(
			"Quotation",
			filters={"name": ["in", quotation_names], "order_type": self.order_type},
			pluck="name",
		)

		for d in self.get("items"):
			if d.prevdoc_docname and d.prevdoc_docname not in valid_quotations:
				frappe.msgprint(_("Quotation {0} not of type {1}").format(d.prevdoc_docname, self.order_type))

	def validate_delivery_date(self):
		if self.order_type == "Sales" and not self.skip_delivery_note:
			delivery_date_list = [d.delivery_date for d in self.get("items") if d.delivery_date]
			max_delivery_date = max(delivery_date_list) if delivery_date_list else None
			if (max_delivery_date and not self.delivery_date) or (
				max_delivery_date and getdate(self.delivery_date) != getdate(max_delivery_date)
			):
				self.delivery_date = max_delivery_date
			if self.delivery_date:
				for d in self.get("items"):
					if not d.delivery_date:
						d.delivery_date = self.delivery_date
					if getdate(self.transaction_date) > getdate(d.delivery_date):
						frappe.msgprint(
							_("Expected Delivery Date should be after Sales Order Date"),
							indicator="orange",
							title=_("Invalid Delivery Date"),
							raise_exception=True,
						)
			else:
				frappe.throw(_("Please enter Delivery Date"))

		self.validate_sales_mntc_quotation()

	def validate_proj_cust(self):
		if self.project and self.customer_name:
			project_has_valid_customer = frappe.db.exists(
				"Project", {"name": self.project, "customer": ["in", [self.customer, "", None]]}
			)
			if not project_has_valid_customer:
				frappe.throw(
					_("Customer {0} does not belong to project {1}").format(self.customer, self.project)
				)

	def validate_warehouse(self):
		super().validate_warehouse()

		for d in self.get("items"):
			if (
				(
					frappe.get_cached_value("Item", d.item_code, "is_stock_item") == 1
					or (
						self.has_product_bundle(d.item_code)
						and self.product_bundle_has_stock_item(d.item_code)
					)
				)
				and not d.warehouse
				and not cint(d.delivered_by_supplier)
			):
				frappe.throw(
					_("Source warehouse required for stock item {0}").format(d.item_code), WarehouseRequired
				)

	def validate_with_previous_doc(self):
		super().validate_with_previous_doc(
			{
				"Quotation": {"ref_dn_field": "prevdoc_docname", "compare_fields": [["company", "="]]},
				"Quotation Item": {
					"ref_dn_field": "quotation_item",
					"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True,
				},
			}
		)

		if cint(frappe.get_single_value("Selling Settings", "maintain_same_sales_rate")):
			self.validate_rate_with_reference_doc([["Quotation", "prevdoc_docname", "quotation_item"]])

	def update_enquiry_status(self, prevdoc, flag):
		opportunity_name = frappe.db.get_value("Quotation Item", {"parent": prevdoc}, "prevdoc_docname")
		if opportunity_name:
			frappe.db.set_value("Opportunity", opportunity_name, "status", flag)

	def update_prevdoc_status(self, flag=None):
		for quotation in set(d.prevdoc_docname for d in self.get("items")):
			if quotation:
				doc = frappe.get_doc("Quotation", quotation)
				if doc.docstatus.is_cancelled():
					frappe.throw(_("Quotation {0} is cancelled").format(quotation))

				doc.set_status(update=True)
				doc.update_opportunity("Converted" if flag == "submit" else "Quotation")

	def validate_drop_ship(self):
		for d in self.get("items"):
			if d.delivered_by_supplier and not d.supplier:
				frappe.throw(_("Row #{0}: Set Supplier for item {1}").format(d.idx, d.item_code))

	def on_submit(self):
		super().update_prevdoc_status()
		self.check_credit_limit()
		self.update_reserved_qty()
		DeliveryScheduleService(self).delete_removed_delivery_schedule_items()

		frappe.get_cached_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total, self
		)
		self.update_project()
		self.update_prevdoc_status("submit")

		self.update_blanket_order()

		update_linked_doc(self.doctype, self.name, self.inter_company_order_reference)
		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

			update_coupon_code_count(self.coupon_code, "used")

		if self.get("reserve_stock") and not self.get("is_subcontracted"):
			self.create_stock_reservation_entries()

	def on_cancel(self):
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Payment Ledger Entry",
			"Advance Payment Ledger Entry",
			"Unreconcile Payment",
			"Unreconcile Payment Entries",
		)
		super().on_cancel()
		super().update_prevdoc_status()
		# Cannot cancel closed SO
		if self.status == "Closed":
			frappe.throw(_("Closed order cannot be cancelled. Unclose to cancel."))

		DeliveryScheduleService(self).delete_delivery_schedule_items()
		self.check_nextdoc_docstatus()
		self.update_reserved_qty()
		self.update_project()
		self.update_prevdoc_status("cancel")

		self.db_set("status", "Cancelled")

		self.update_blanket_order()
		self.cancel_stock_reservation_entries()

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_order_reference)
		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

			update_coupon_code_count(self.coupon_code, "cancelled")

	def update_project(self):
		if frappe.get_single_value("Selling Settings", "sales_update_frequency") != "Each Transaction":
			return

		if self.project:
			project = frappe.get_lazy_doc("Project", self.project)
			project.update_sales_amount()
			project.db_update()

	def check_credit_limit(self):
		# if bypass credit limit check is set to true (1) at sales order level,
		# then we need not to check credit limit and vise versa
		if not cint(
			frappe.db.get_value(
				"Customer Credit Limit",
				{"parent": self.customer, "parenttype": "Customer", "company": self.company},
				"bypass_credit_limit_check",
			)
		):
			check_credit_limit(self.customer, self.company)

	def check_nextdoc_docstatus(self):
		linked_invoices = frappe.get_all(
			"Sales Invoice Item",
			filters={"sales_order": self.name, "docstatus": 0},
			pluck="parent",
			distinct=True,
		)
		if linked_invoices:
			linked_invoices = [get_link_to_form("Sales Invoice", si) for si in linked_invoices]
			frappe.throw(
				_("Sales Invoice {0} must be deleted before cancelling this Sales Order").format(
					", ".join(linked_invoices)
				)
			)

	def update_status(self, status):
		StatusService(self).update_status(status)

	def update_reserved_qty(self, so_item_rows=None):
		StockReservationService(self).update_reserved_qty(so_item_rows)

	def on_update_after_submit(self):
		self.calculate_commission()
		self.calculate_contribution()
		self.check_credit_limit()

	def before_update_after_submit(self):
		self.validate_po()
		self.validate_drop_ship()
		self.validate_supplier_after_submit()
		self.validate_delivery_date()

	def validate_supplier_after_submit(self):
		"""Check that supplier is the same after submit if PO is already made"""
		exc_list = []

		for item in self.items:
			if item.supplier:
				supplier = frappe.db.get_value("Sales Order Item", item.name, "supplier")
				if item.ordered_qty > 0.0 and item.supplier != supplier:
					exc_list.append(
						_("Row #{0}: Not allowed to change Supplier as Purchase Order already exists").format(
							item.idx
						)
					)

		if exc_list:
			frappe.throw("\n".join(exc_list))

	def update_delivery_status(self):
		"""Update delivery status from Purchase Order for drop shipping"""
		StatusService(self).update_delivery_status()

	def update_picking_status(self):
		StatusService(self).update_picking_status()

	def set_indicator(self):
		"""Set indicator for portal"""
		StatusService(self).set_indicator()

	def on_recurring(self, reference_doc, auto_repeat_doc):
		def _get_delivery_date(ref_doc_delivery_date, red_doc_transaction_date, transaction_date):
			delivery_date = auto_repeat_doc.get_next_schedule_date(schedule_date=ref_doc_delivery_date)

			if delivery_date <= transaction_date:
				delivery_date_diff = frappe.utils.date_diff(ref_doc_delivery_date, red_doc_transaction_date)
				delivery_date = frappe.utils.add_days(transaction_date, delivery_date_diff)

			return delivery_date

		self.set(
			"delivery_date",
			_get_delivery_date(
				reference_doc.delivery_date, reference_doc.transaction_date, self.transaction_date
			),
		)

		for d in self.get("items"):
			reference_delivery_date = frappe.db.get_value(
				"Sales Order Item",
				{"parent": reference_doc.name, "item_code": d.item_code, "idx": d.idx},
				"delivery_date",
			)

			d.set(
				"delivery_date",
				_get_delivery_date(
					reference_delivery_date, reference_doc.transaction_date, self.transaction_date
				),
			)

	def validate_serial_no_based_delivery(self):
		reserved_items = []
		normal_items = []
		for item in self.items:
			if item.ensure_delivery_based_on_produced_serial_no:
				if item.item_code in normal_items:
					frappe.throw(
						_(
							"Cannot ensure delivery by Serial No as Item {0} is added with and without Ensure Delivery by Serial No."
						).format(item.item_code)
					)
				if item.item_code not in reserved_items:
					if not frappe.get_cached_value("Item", item.item_code, "has_serial_no"):
						frappe.throw(
							_(
								"Item {0} has no Serial No. Only serialized items can have delivery based on Serial No"
							).format(item.item_code)
						)
					if not frappe.db.exists("BOM", {"item": item.item_code, "is_active": 1}):
						frappe.throw(
							_(
								"No active BOM found for item {0}. Delivery by Serial No cannot be ensured"
							).format(item.item_code)
						)
				reserved_items.append(item.item_code)
			else:
				normal_items.append(item.item_code)

			if not item.ensure_delivery_based_on_produced_serial_no and item.item_code in reserved_items:
				frappe.throw(
					_(
						"Cannot ensure delivery by Serial No as Item {0} is added with and without Ensure Delivery by Serial No."
					).format(item.item_code)
				)

	@frappe.whitelist()
	def has_unreserved_stock(self, table_name: str = "items") -> dict:
		"""Returns unreserved qty per item if there is any unreserved item in the Sales Order."""
		return StockReservationService(self).has_unreserved_stock(table_name)

	@frappe.whitelist()
	def create_stock_reservation_entries(
		self,
		items_details: list[dict] | None = None,
		from_voucher_type: Literal["Pick List", "Purchase Receipt"] | None = None,
		notify: bool = True,
	) -> None:
		"""Creates Stock Reservation Entries for Sales Order Items."""
		StockReservationService(self).create_stock_reservation_entries(
			items_details, from_voucher_type, notify
		)

	@frappe.whitelist()
	def cancel_stock_reservation_entries(self, sre_list: list | None = None, notify: bool = True) -> None:
		"""Cancel Stock Reservation Entries for Sales Order Items."""
		StockReservationService(self).cancel_stock_reservation_entries(sre_list, notify)

	def set_missing_values(self, for_validate=False):
		super().set_missing_values(for_validate)

		if self.delivery_date:
			for item in self.items:
				if not item.delivery_date:
					item.delivery_date = self.delivery_date

	@frappe.whitelist()
	def get_delivery_schedule(self, sales_order_item: str):
		return DeliveryScheduleService(self).get_delivery_schedule(sales_order_item)

	@frappe.whitelist()
	def create_delivery_schedule(self, child_row: dict | frappe._dict, schedules: str | list[dict]):
		DeliveryScheduleService(self).create_delivery_schedule(child_row, schedules)


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Orders"),
			"list_template": "templates/includes/list/list.html",
		}
	)

	return list_context


@frappe.whitelist()
def is_enable_cutoff_date_on_bulk_delivery_note_creation():
	return frappe.get_single_value("Selling Settings", "enable_cutoff_date_on_bulk_delivery_note_creation")


@frappe.whitelist()
def close_or_unclose_sales_orders(names: str, status: str):
	if not frappe.has_permission("Sales Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	names = json.loads(names)
	for name in names:
		so = frappe.get_lazy_doc("Sales Order", name)
		if so.docstatus == 1:
			if status == "Closed":
				if so.status not in ("Cancelled", "Closed") and (
					so.per_delivered < 100 or so.per_billed < 100
				):
					so.update_status(status)
			else:
				if so.status == "Closed":
					so.update_status("Draft")
			so.update_blanket_order()

	frappe.local.message_log = []


@frappe.whitelist()
def get_events(start: str, end: str, filters: str | dict | None = None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""

	SalesOrder = frappe.qb.DocType("Sales Order")
	SalesOrderItem = frappe.qb.DocType("Sales Order Item")

	query = (
		frappe.get_query("Sales Order", filters=filters, ignore_permissions=False)
		.join(SalesOrderItem)
		.on(SalesOrder.name == SalesOrderItem.parent)
		.select(
			SalesOrder.name,
			SalesOrder.customer_name,
			SalesOrder.status,
			SalesOrder.delivery_status,
			SalesOrder.billing_status,
			SalesOrderItem.delivery_date,
		)
		.distinct()
		.where(SalesOrder.skip_delivery_note == 0)
		.where(SalesOrder.docstatus < 2)
		.where(SalesOrderItem.delivery_date.between(start, end))
		.where(SalesOrderItem.delivery_date.isnotnull())
	)

	data = query.run(as_dict=True)

	for row in data:
		row.update(
			{
				"allDay": 0,
				"convertToUserTz": 0,
			}
		)

	return data


@frappe.whitelist()
def update_status(status: str, name: str):
	so = frappe.get_doc("Sales Order", name, check_permission="submit")
	so.update_status(status)


def update_produced_qty_in_so_item(sales_order, sales_order_item):
	# for multiple work orders against same sales order item
	linked_wo_with_so_item = frappe.db.get_all(
		"Work Order",
		["produced_qty"],
		{"sales_order_item": sales_order_item, "sales_order": sales_order, "docstatus": 1},
	)

	total_produced_qty = 0
	for wo in linked_wo_with_so_item:
		total_produced_qty += flt(wo.get("produced_qty"))

	if not total_produced_qty and frappe.flags.in_patch:
		return

	frappe.db.set_value("Sales Order Item", sales_order_item, "produced_qty", total_produced_qty)


@frappe.whitelist()
def get_work_order_items(sales_order: str, for_raw_material_request: int = 0):
	"""Returns items with BOM that already do not have a linked work order"""
	if sales_order:
		so = frappe.get_doc("Sales Order", sales_order)

		wo = qb.DocType("Work Order")

		items = []
		item_codes = [i.item_code for i in so.items]
		product_bundle_parents = [
			pb.new_item_code
			for pb in frappe.get_all(
				"Product Bundle",
				{"new_item_code": ["in", item_codes], "is_active": 1, "docstatus": 1},
				["new_item_code"],
			)
		]

		overproduction_percentage_for_sales_order = (
			frappe.get_single_value("Manufacturing Settings", "overproduction_percentage_for_sales_order")
			/ 100
		)
		for table in [so.items, so.packed_items]:
			for i in table:
				bom = get_default_bom(i.item_code)
				stock_qty = i.qty if i.doctype == "Packed Item" else i.stock_qty

				if not for_raw_material_request:
					total_work_order_qty = flt(
						qb.from_(wo)
						.select(Sum(wo.qty - wo.process_loss_qty))
						.where(
							(wo.production_item == i.item_code)
							& (wo.sales_order == so.name)
							& (wo.sales_order_item == i.name)
							& (wo.docstatus == 1)
							& (wo.status != "Closed")
						)
						.run()[0][0]
					)
					pending_qty = stock_qty - total_work_order_qty
				else:
					pending_qty = stock_qty

				if not pending_qty:
					pending_qty = stock_qty * overproduction_percentage_for_sales_order

				if pending_qty > 0 and i.item_code not in product_bundle_parents and bom:
					items.append(
						dict(
							name=i.name,
							item_code=i.item_code,
							item_name=i.item_name,
							description=i.description,
							bom=bom,
							warehouse=i.warehouse,
							pending_qty=pending_qty,
							required_qty=pending_qty if for_raw_material_request else 0,
							sales_order_item=i.name,
						)
					)

		return items


@frappe.whitelist()
def get_stock_reservation_status():
	return frappe.get_single_value("Stock Settings", "enable_stock_reservation")
