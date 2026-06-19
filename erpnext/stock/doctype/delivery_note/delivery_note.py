# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.controllers.selling_controller import SellingController
from erpnext.stock.doctype.delivery_note.services.billing_status import BillingStatusService
from erpnext.stock.doctype.delivery_note.services.packing import PackingService
from erpnext.stock.doctype.packed_item.packed_item import make_packing_list

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class DeliveryNote(SellingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.item_wise_tax_detail.item_wise_tax_detail import ItemWiseTaxDetail
		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.sales_taxes_and_charges.sales_taxes_and_charges import (
			SalesTaxesandCharges,
		)
		from erpnext.selling.doctype.sales_team.sales_team import SalesTeam
		from erpnext.stock.doctype.delivery_note_item.delivery_note_item import DeliveryNoteItem
		from erpnext.stock.doctype.packed_item.packed_item import PackedItem

		additional_discount_percentage: DF.Float
		address_display: DF.TextEditor | None
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
		commission_rate: DF.Float
		company: DF.Link
		company_address: DF.Link | None
		company_address_display: DF.TextEditor | None
		company_contact_person: DF.Link | None
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		currency: DF.Link
		customer: DF.Link
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		delivery_trip: DF.Link | None
		disable_rounded_total: DF.Check
		discount_amount: DF.Currency
		dispatch_address: DF.TextEditor | None
		dispatch_address_name: DF.Link | None
		driver: DF.Link | None
		driver_name: DF.Data | None
		excise_page: DF.Data | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		installation_status: DF.Literal[None]
		instructions: DF.Text | None
		inter_company_reference: DF.Link | None
		is_internal_customer: DF.Check
		is_return: DF.Check
		issue_credit_note: DF.Check
		item_wise_tax_details: DF.Table[ItemWiseTaxDetail]
		items: DF.Table[DeliveryNoteItem]
		language: DF.Link | None
		letter_head: DF.Link | None
		lr_date: DF.Date | None
		lr_no: DF.Data | None
		named_place: DF.Data | None
		naming_series: DF.Literal["MAT-DN-.YYYY.-", "MAT-DN-RET-.YYYY.-"]
		net_total: DF.Currency
		other_charges_calculation: DF.TextEditor | None
		packed_items: DF.Table[PackedItem]
		per_billed: DF.Percent
		per_installed: DF.Percent
		per_returned: DF.Percent
		plc_conversion_rate: DF.Float
		po_date: DF.Date | None
		po_no: DF.SmallText | None
		posting_date: DF.Date
		posting_time: DF.Time
		price_list_currency: DF.Link
		pricing_rules: DF.Table[PricingRuleDetail]
		print_without_amount: DF.Check
		project: DF.Link | None
		represents_company: DF.Link | None
		return_against: DF.Link | None
		rounded_total: DF.Currency
		rounding_adjustment: DF.Currency
		sales_partner: DF.Link | None
		sales_team: DF.Table[SalesTeam]
		scan_barcode: DF.Data | None
		select_print_heading: DF.Link | None
		selling_price_list: DF.Link
		set_posting_time: DF.Check
		set_target_warehouse: DF.Link | None
		set_warehouse: DF.Link | None
		shipping_address: DF.TextEditor | None
		shipping_address_name: DF.Link | None
		shipping_rule: DF.Link | None
		status: DF.Literal[
			"",
			"Draft",
			"To Bill",
			"Partially Billed",
			"Completed",
			"Return",
			"Return Issued",
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
		total: DF.Currency
		total_commission: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		transporter: DF.Link | None
		transporter_name: DF.Data | None
		utm_campaign: DF.Link | None
		utm_content: DF.Data | None
		utm_medium: DF.Link | None
		utm_source: DF.Link | None
		vehicle_no: DF.Data | None
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.status_updater = [
			{
				"source_dt": "Delivery Note Item",
				"target_dt": "Sales Order Item",
				"join_field": "so_detail",
				"target_field": "delivered_qty",
				"target_parent_dt": "Sales Order",
				"target_parent_field": "per_delivered",
				"target_ref_field": "qty",
				"source_field": "qty",
				"percent_join_field": "against_sales_order",
				"status_field": "delivery_status",
				"keyword": "Delivered",
				"second_source_dt": "Sales Invoice Item",
				"second_source_field": "qty",
				"second_join_field": "so_detail",
				"overflow_type": "delivery",
				"second_source_extra_cond": """ and exists(select name from `tabSales Invoice`
				where name=`tabSales Invoice Item`.parent and update_stock = 1)""",
			},
			{
				"source_dt": "Delivery Note Item",
				"target_dt": "Sales Invoice Item",
				"join_field": "si_detail",
				"target_field": "delivered_qty",
				"target_parent_dt": "Sales Invoice",
				"target_ref_field": "qty",
				"source_field": "qty",
				"percent_join_field": "against_sales_invoice",
				"overflow_type": "delivery",
				"no_allowance": 1,
			},
			{
				"source_dt": "Delivery Note Item",
				"target_dt": "Pick List Item",
				"join_field": "pick_list_item",
				"target_field": "delivered_qty",
				"target_parent_dt": "Pick List",
				"target_parent_field": "per_delivered",
				"target_ref_field": "picked_qty",
				"source_field": "stock_qty",
				"percent_join_field": "against_pick_list",
				"status_field": "delivery_status",
				"keyword": "Delivered",
			},
		]
		if cint(self.is_return):
			self.status_updater.extend(
				[
					{
						"source_dt": "Delivery Note Item",
						"target_dt": "Sales Order Item",
						"join_field": "so_detail",
						"target_field": "returned_qty",
						"target_parent_dt": "Sales Order",
						"source_field": "-1 * qty",
						"second_source_dt": "Sales Invoice Item",
						"second_source_field": "-1 * qty",
						"second_join_field": "so_detail",
						"extra_cond": """ and exists (select name from `tabDelivery Note`
					where name=`tabDelivery Note Item`.parent and is_return=1)""",
						"second_source_extra_cond": """ and exists (select name from `tabSales Invoice`
					where name=`tabSales Invoice Item`.parent and is_return=1 and update_stock=1)""",
					},
					{
						"source_dt": "Delivery Note Item",
						"target_dt": "Delivery Note Item",
						"join_field": "dn_detail",
						"target_field": "returned_qty",
						"target_parent_dt": "Delivery Note",
						"target_parent_field": "per_returned",
						"target_ref_field": "stock_qty",
						"source_field": "-1 * stock_qty",
						"percent_join_field_parent": "return_against",
					},
				]
			)

	def onload(self):
		super().onload()

		if self.docstatus == 0:
			self.set_onload("has_unpacked_items", self.has_unpacked_items())

	def before_print(self, settings=None):
		def toggle_print_hide(meta, fieldname):
			df = meta.get_field(fieldname)
			if self.get("print_without_amount"):
				df.set("__print_hide", 1)
			else:
				df.delete_key("__print_hide")

		item_meta = frappe.get_meta("Delivery Note Item")
		print_hide_fields = {
			"parent": ["grand_total", "rounded_total", "in_words", "currency", "total", "taxes"],
			"items": ["rate", "amount", "discount_amount", "price_list_rate", "discount_percentage"],
		}

		for key, fieldname in print_hide_fields.items():
			for f in fieldname:
				toggle_print_hide(self.meta if key == "parent" else item_meta, f)

		super().before_print(settings)

	def set_actual_qty(self):
		for d in self.get("items"):
			if d.item_code and d.warehouse:
				actual_qty = frappe.db.sql(
					"""select actual_qty from `tabBin`
					where item_code = %s and warehouse = %s""",
					(d.item_code, d.warehouse),
				)
				d.actual_qty = actual_qty and flt(actual_qty[0][0]) or 0

	def so_required(self):
		"""check in manage account if sales order required or not"""
		if frappe.get_single_value("Selling Settings", "so_required") == "Yes":
			for d in self.get("items"):
				if not d.against_sales_order:
					frappe.throw(_("Sales Order required for Item {0}").format(d.item_code))

	def validate(self):
		self.validate_posting_time()
		super().validate()
		self.validate_references()
		self.validate_expense_account()
		self.set_status()
		self.so_required()
		self.validate_proj_cust()
		self.check_sales_order_on_hold_or_close("against_sales_order")
		self.validate_warehouse()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_with_previous_doc()
		self.set_serial_and_batch_bundle_from_pick_list()
		make_packing_list(self)
		self.update_current_stock()

		if not self.installation_status:
			self.installation_status = "Not Installed"

		self.validate_against_stock_reservation_entries()
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def validate_with_previous_doc(self):
		super().validate_with_previous_doc(
			{
				"Sales Order": {
					"ref_dn_field": "against_sales_order",
					"compare_fields": [
						["customer", "="],
						["company", "="],
						["project", "="],
						["currency", "="],
					],
				},
				"Sales Order Item": {
					"ref_dn_field": "so_detail",
					"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True,
				},
				"Sales Invoice": {
					"ref_dn_field": "against_sales_invoice",
					"compare_fields": [
						["customer", "="],
						["company", "="],
						["project", "="],
						["currency", "="],
					],
				},
				"Sales Invoice Item": {
					"ref_dn_field": "si_detail",
					"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True,
				},
			}
		)

		if (
			cint(frappe.get_single_value("Selling Settings", "maintain_same_sales_rate"))
			and not self.is_return
			and not self.is_internal_customer
		):
			self.validate_rate_with_reference_doc(
				[
					["Sales Order", "against_sales_order", "so_detail"],
					["Sales Invoice", "against_sales_invoice", "si_detail"],
				]
			)

	def validate_references(self):
		self.validate_sales_order_references()
		self.validate_sales_invoice_references()

	def validate_sales_order_references(self):
		self._validate_dependent_item_fields(
			"against_sales_order", "so_detail", _("References to Sales Orders are Incomplete")
		)

	def validate_sales_invoice_references(self):
		if self.is_return:
			return

		self._validate_dependent_item_fields(
			"against_sales_invoice", "si_detail", _("References to Sales Invoices are Incomplete")
		)

	def _validate_dependent_item_fields(self, field_a: str, field_b: str, error_title: str):
		errors = []
		for item in self.items:
			missing_label = None
			if item.get(field_a) and not item.get(field_b):
				missing_label = item.meta.get_label(field_b)
			elif item.get(field_b) and not item.get(field_a):
				missing_label = item.meta.get_label(field_a)

			if missing_label and missing_label != "No Label":
				errors.append(
					_("The field {0} in row {1} is not set").format(
						frappe.bold(_(missing_label)), frappe.bold(item.idx)
					)
				)

		if errors:
			frappe.throw("<br>".join(errors), title=error_title)

	def validate_proj_cust(self):
		"""check for does customer belong to same project as entered.."""
		if self.project and self.customer:
			res = frappe.db.sql(
				"""select name from `tabProject`
				where name = %s and (customer = %s or
					ifnull(customer,'')='')""",
				(self.project, self.customer),
			)
			if not res:
				frappe.throw(
					_("Customer {0} does not belong to project {1}").format(self.customer, self.project)
				)

	def validate_warehouse(self):
		super().validate_warehouse()

		for d in self.get_item_list():
			if not d["warehouse"] and frappe.get_cached_value("Item", d["item_code"], "is_stock_item") == 1:
				frappe.throw(_("Warehouse required for stock Item {0}").format(d["item_code"]))

	def update_current_stock(self):
		if self.get("_action") and self._action != "update_after_submit":
			for d in self.get("items"):
				d.actual_qty = frappe.db.get_value(
					"Bin", {"item_code": d.item_code, "warehouse": d.warehouse}, "actual_qty"
				)

			for d in self.get("packed_items"):
				bin_qty = frappe.db.get_value(
					"Bin",
					{"item_code": d.item_code, "warehouse": d.warehouse},
					["actual_qty", "projected_qty"],
					as_dict=True,
				)
				if bin_qty:
					d.actual_qty = flt(bin_qty.actual_qty)
					d.projected_qty = flt(bin_qty.projected_qty)

	def validate_expense_account(self):
		company_values = frappe.get_cached_value(
			"Company",
			self.company,
			[
				"stock_delivered_but_not_billed",
				"disable_sdbnb_in_sr",
				"default_expense_account",
			],
			as_dict=True,
		)

		sdbnb_account = company_values.stock_delivered_but_not_billed
		disable_sdbnb_in_sr = company_values.disable_sdbnb_in_sr
		default_expense_account = company_values.default_expense_account

		for item in self.items:
			if item.get("against_sales_invoice"):
				if sdbnb_account and item.expense_account == sdbnb_account:
					frappe.throw(
						_(
							"Row #{0}: Stock Delivered But Not Billed account cannot be used for items linked to a Sales Invoice"
						).format(item.idx)
					)
			else:
				is_stock_item = frappe.get_cached_value("Item", item.item_code, "is_stock_item")
				# Only stock items
				if is_stock_item and not item.get("is_fixed_asset") and not item.get("is_subcontracted"):
					# Sales Return handling
					if self.is_return and disable_sdbnb_in_sr:
						if default_expense_account and (
							not item.expense_account or item.expense_account == sdbnb_account
						):
							item.expense_account = default_expense_account

					elif sdbnb_account:
						item.expense_account = sdbnb_account
			if not item.expense_account and default_expense_account:
				item.expense_account = default_expense_account

	def on_submit(self):
		self.validate_packed_qty()
		self.update_pick_list_status()

		# Check for Approving Authority
		frappe.get_cached_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total, self
		)

		# update delivered qty in sales order
		self.update_prevdoc_status()
		self.update_billing_status()

		if not self.is_return:
			self.check_credit_limit()
		elif self.issue_credit_note:
			BillingStatusService(self).make_return_invoice()

		for table_name in ["items", "packed_items"]:
			if not self.get(table_name):
				continue

			self.make_bundle_for_sales_purchase_return(table_name)
			self.make_bundle_using_old_serial_batch_fields(table_name)

		self.validate_standalone_serial_nos_customer()
		self.update_stock_reservation_entries()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		self.update_stock_ledger()
		self.make_gl_entries()
		self.repost_future_sle_and_gle()

	def on_cancel(self):
		super().on_cancel()

		self.check_sales_order_on_hold_or_close("against_sales_order")
		self.check_next_docstatus()

		self.update_prevdoc_status()
		self.update_billing_status()

		self.update_stock_reservation_entries()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		self.update_stock_ledger()

		PackingService(self).cancel_packing_slips()
		self.update_pick_list_status()

		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Repost Item Valuation",
			"Serial and Batch Bundle",
		)

		self.delete_auto_created_batches()

	def validate_against_stock_reservation_entries(self):
		"""Validates if Stock Reservation Entries are available for the Sales Order Item reference."""

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_sre_reserved_warehouses_for_voucher,
		)

		# Don't validate if Return
		if self.is_return:
			return

		for item in self.get("items"):
			# Skip if `Sales Order` or `Sales Order Item` reference is not set.
			if not item.against_sales_order or not item.so_detail:
				continue

			reserved_warehouses = get_sre_reserved_warehouses_for_voucher(
				"Sales Order", item.against_sales_order, item.so_detail
			)

			# Skip if stock is not reserved.
			if not reserved_warehouses:
				continue

			# Set `Warehouse` from SRE if not set.
			if not item.warehouse:
				item.warehouse = reserved_warehouses[0]
			else:
				# Throw if `Warehouse` not in Reserved Warehouses.
				if item.warehouse not in reserved_warehouses:
					msg = _("Row #{0}: Stock is reserved for item {1} in warehouse {2}.").format(
						item.idx,
						frappe.bold(item.item_code),
						frappe.bold(reserved_warehouses[0])
						if len(reserved_warehouses) == 1
						else _("{0} and {1}").format(
							frappe.bold(", ".join(reserved_warehouses[:-1])),
							frappe.bold(reserved_warehouses[-1]),
						),
					)
					frappe.throw(msg, title=_("Stock Reservation Warehouse Mismatch"))

	def check_credit_limit(self):
		from erpnext.selling.doctype.customer.customer import check_credit_limit

		if self.per_billed == 100:
			return

		extra_amount = 0
		validate_against_credit_limit = False
		bypass_credit_limit_check_at_sales_order = cint(
			frappe.db.get_value(
				"Customer Credit Limit",
				filters={"parent": self.customer, "parenttype": "Customer", "company": self.company},
				fieldname="bypass_credit_limit_check",
			)
		)

		if bypass_credit_limit_check_at_sales_order:
			for d in self.get("items"):
				if not d.against_sales_invoice:
					validate_against_credit_limit = True
					extra_amount = self.base_grand_total
					break
		else:
			for d in self.get("items"):
				if not (d.against_sales_order or d.against_sales_invoice):
					validate_against_credit_limit = True
					break

		if validate_against_credit_limit:
			check_credit_limit(
				self.customer, self.company, bypass_credit_limit_check_at_sales_order, extra_amount
			)

	def validate_packed_qty(self):
		"""Validate that if packed qty exists, it should be equal to qty"""
		PackingService(self).validate_packed_qty()

	def check_next_docstatus(self):
		submit_rv = frappe.db.sql(
			"""select t1.name
			from `tabSales Invoice` t1,`tabSales Invoice Item` t2
			where t1.name = t2.parent and t2.delivery_note = %s and t1.docstatus = 1""",
			(self.name),
		)
		if submit_rv:
			frappe.throw(_("Sales Invoice {0} has already been submitted").format(submit_rv[0][0]))

		submit_in = frappe.db.sql(
			"""select t1.name
			from `tabInstallation Note` t1, `tabInstallation Note Item` t2
			where t1.name = t2.parent and t2.prevdoc_docname = %s and t1.docstatus = 1""",
			(self.name),
		)
		if submit_in:
			frappe.throw(_("Installation Note {0} has already been submitted").format(submit_in[0][0]))

	def update_status(self, status):
		BillingStatusService(self).update_status(status)

	def update_billing_status(self, update_modified=True):
		BillingStatusService(self).update_billing_status(update_modified)

	def has_unpacked_items(self):
		return PackingService(self).has_unpacked_items()


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Shipments"),
			"list_template": "templates/includes/list/list.html",
		}
	)
	return list_context


@frappe.whitelist()
def update_delivery_note_status(docname: str, status: str):
	dn = frappe.get_lazy_doc("Delivery Note", docname)
	dn.update_status(status)
