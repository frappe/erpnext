# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _, msgprint
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, cstr, flt

from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import (
	get_party_tax_withholding_details,
)
from erpnext.accounts.party import get_party_account, get_party_account_currency
from erpnext.buying.utils import check_on_hold_or_closed_status, validate_for_items
from erpnext.controllers.buying_controller import BuyingController
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults, get_last_purchase_details
from erpnext.stock.stock_balance import get_ordered_qty, update_bin_qty
from erpnext.stock.utils import get_bin

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class PurchaseOrder(BuyingController):
	def __init__(self, *args, **kwargs):
		super(PurchaseOrder, self).__init__(*args, **kwargs)
		self.status_updater = [
			{
				"source_dt": "Purchase Order Item",
				"target_dt": "Material Request Item",
				"join_field": "material_request_item",
				"target_field": "ordered_qty",
				"target_parent_dt": "Material Request",
				"target_parent_field": "per_ordered",
				"target_ref_field": "stock_qty",
				"source_field": "stock_qty",
				"percent_join_field": "material_request",
			}
		]

	def onload(self):
		supplier_tds = frappe.db.get_value("Supplier", self.supplier, "tax_withholding_category")
		self.set_onload("supplier_tds", supplier_tds)

	def validate(self):
		super(PurchaseOrder, self).validate()

		self.set_status()

		# apply tax withholding only if checked and applicable
		self.set_tax_withholding()

		self.validate_supplier()
		self.validate_schedule_date()
		validate_for_items(self)
		self.check_on_hold_or_closed_status()

		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "stock_qty")

		self.validate_with_previous_doc()
		self.validate_for_subcontracting()
		self.validate_minimum_order_qty()

		if self.is_old_subcontracting_flow:
			self.validate_bom_for_subcontracting_items()
			self.create_raw_materials_supplied()

		self.validate_fg_item_for_subcontracting()
		self.set_received_qty_for_drop_ship_items()
		validate_inter_company_party(
			self.doctype, self.supplier, self.company, self.inter_company_order_reference
		)
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def validate_with_previous_doc(self):
		super(PurchaseOrder, self).validate_with_previous_doc(
			{
				"Supplier Quotation": {
					"ref_dn_field": "supplier_quotation",
					"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
				},
				"Supplier Quotation Item": {
					"ref_dn_field": "supplier_quotation_item",
					"compare_fields": [
						["project", "="],
						["item_code", "="],
						["uom", "="],
						["conversion_factor", "="],
					],
					"is_child_table": True,
				},
				"Material Request": {
					"ref_dn_field": "material_request",
					"compare_fields": [["company", "="]],
				},
				"Material Request Item": {
					"ref_dn_field": "material_request_item",
					"compare_fields": [["project", "="], ["item_code", "="]],
					"is_child_table": True,
				},
			}
		)

		if cint(frappe.db.get_single_value("Buying Settings", "maintain_same_rate")):
			self.validate_rate_with_reference_doc(
				[["Supplier Quotation", "supplier_quotation", "supplier_quotation_item"]]
			)

	def set_tax_withholding(self):
		if not self.apply_tds:
			return

		tax_withholding_details = get_party_tax_withholding_details(self, self.tax_withholding_category)

		if not tax_withholding_details:
			return

		accounts = []
		for d in self.taxes:
			if d.account_head == tax_withholding_details.get("account_head"):
				d.update(tax_withholding_details)
			accounts.append(d.account_head)

		if not accounts or tax_withholding_details.get("account_head") not in accounts:
			self.append("taxes", tax_withholding_details)

		to_remove = [
			d
			for d in self.taxes
			if not d.tax_amount and d.account_head == tax_withholding_details.get("account_head")
		]

		for d in to_remove:
			self.remove(d)

		# calculate totals again after applying TDS
		self.calculate_taxes_and_totals()

	def validate_supplier(self):
		prevent_po = frappe.db.get_value("Supplier", self.supplier, "prevent_pos")
		if prevent_po:
			standing = frappe.db.get_value("Supplier Scorecard", self.supplier, "status")
			if standing:
				frappe.throw(
					_("Purchase Orders are not allowed for {0} due to a scorecard standing of {1}.").format(
						self.supplier, standing
					)
				)

		warn_po = frappe.db.get_value("Supplier", self.supplier, "warn_pos")
		if warn_po:
			standing = frappe.db.get_value("Supplier Scorecard", self.supplier, "status")
			frappe.msgprint(
				_(
					"{0} currently has a {1} Supplier Scorecard standing, and Purchase Orders to this supplier should be issued with caution."
				).format(self.supplier, standing),
				title=_("Caution"),
				indicator="orange",
			)

		self.party_account_currency = get_party_account_currency("Supplier", self.supplier, self.company)

	def validate_minimum_order_qty(self):
		if not self.get("items"):
			return
		items = list(set(d.item_code for d in self.get("items")))

		itemwise_min_order_qty = frappe._dict(
			frappe.db.sql(
				"""select name, min_order_qty
			from tabItem where name in ({0})""".format(
					", ".join(["%s"] * len(items))
				),
				items,
			)
		)

		itemwise_qty = frappe._dict()
		for d in self.get("items"):
			itemwise_qty.setdefault(d.item_code, 0)
			itemwise_qty[d.item_code] += flt(d.stock_qty)

		for item_code, qty in itemwise_qty.items():
			if flt(qty) < flt(itemwise_min_order_qty.get(item_code)):
				frappe.throw(
					_(
						"Item {0}: Ordered qty {1} cannot be less than minimum order qty {2} (defined in Item)."
					).format(item_code, qty, itemwise_min_order_qty.get(item_code))
				)

	def validate_bom_for_subcontracting_items(self):
		for item in self.items:
			if not item.bom:
				frappe.throw(
					_("Row #{0}: BOM is not specified for subcontracting item {0}").format(
						item.idx, item.item_code
					)
				)

	def validate_fg_item_for_subcontracting(self):
		if self.is_subcontracted:
			if not self.is_old_subcontracting_flow:
				for item in self.items:
					if not item.fg_item:
						frappe.throw(
							_("Row #{0}: Finished Good Item is not specified for service item {1}").format(
								item.idx, item.item_code
							)
						)
					else:
						if not frappe.get_value("Item", item.fg_item, "is_sub_contracted_item"):
							frappe.throw(
								_("Row #{0}: Finished Good Item {1} must be a sub-contracted item").format(
									item.idx, item.fg_item
								)
							)
						elif not frappe.get_value("Item", item.fg_item, "default_bom"):
							frappe.throw(
								_("Row #{0}: Default BOM not found for FG Item {1}").format(item.idx, item.fg_item)
							)
					if not item.fg_item_qty:
						frappe.throw(_("Row #{0}: Finished Good Item Qty can not be zero").format(item.idx))
		else:
			for item in self.items:
				item.set("fg_item", None)
				item.set("fg_item_qty", 0)

	def get_schedule_dates(self):
		for d in self.get("items"):
			if d.material_request_item and not d.schedule_date:
				d.schedule_date = frappe.db.get_value(
					"Material Request Item", d.material_request_item, "schedule_date"
				)

	@frappe.whitelist()
	def get_last_purchase_rate(self):
		"""get last purchase rates for all items"""

		conversion_rate = flt(self.get("conversion_rate")) or 1.0
		for d in self.get("items"):
			if d.item_code:
				last_purchase_details = get_last_purchase_details(d.item_code, self.name)
				if last_purchase_details:
					d.base_price_list_rate = last_purchase_details["base_price_list_rate"] * (
						flt(d.conversion_factor) or 1.0
					)
					d.discount_percentage = last_purchase_details["discount_percentage"]
					d.base_rate = last_purchase_details["base_rate"] * (flt(d.conversion_factor) or 1.0)
					d.price_list_rate = d.base_price_list_rate / conversion_rate
					d.rate = d.base_rate / conversion_rate
					d.last_purchase_rate = d.rate
				else:

					item_last_purchase_rate = frappe.get_cached_value("Item", d.item_code, "last_purchase_rate")
					if item_last_purchase_rate:
						d.base_price_list_rate = (
							d.base_rate
						) = d.price_list_rate = d.rate = d.last_purchase_rate = item_last_purchase_rate

	# Check for Closed status
	def check_on_hold_or_closed_status(self):
		check_list = []
		for d in self.get("items"):
			if (
				d.meta.get_field("material_request")
				and d.material_request
				and d.material_request not in check_list
			):
				check_list.append(d.material_request)
				check_on_hold_or_closed_status("Material Request", d.material_request)

	def update_requested_qty(self):
		material_request_map = {}
		for d in self.get("items"):
			if d.material_request_item:
				material_request_map.setdefault(d.material_request, []).append(d.material_request_item)

		for mr, mr_item_rows in material_request_map.items():
			if mr and mr_item_rows:
				mr_obj = frappe.get_doc("Material Request", mr)

				if mr_obj.status in ["Stopped", "Cancelled"]:
					frappe.throw(
						_("Material Request {0} is cancelled or stopped").format(mr), frappe.InvalidStatusError
					)

				mr_obj.update_requested_qty(mr_item_rows)

	def update_ordered_qty(self, po_item_rows=None):
		"""update requested qty (before ordered_qty is updated)"""
		item_wh_list = []
		for d in self.get("items"):
			if (
				(not po_item_rows or d.name in po_item_rows)
				and [d.item_code, d.warehouse] not in item_wh_list
				and frappe.get_cached_value("Item", d.item_code, "is_stock_item")
				and d.warehouse
				and not d.delivered_by_supplier
			):
				item_wh_list.append([d.item_code, d.warehouse])
		for item_code, warehouse in item_wh_list:
			update_bin_qty(item_code, warehouse, {"ordered_qty": get_ordered_qty(item_code, warehouse)})

	def check_modified_date(self):
		mod_db = frappe.db.sql("select modified from `tabPurchase Order` where name = %s", self.name)
		date_diff = frappe.db.sql("select '%s' - '%s' " % (mod_db[0][0], cstr(self.modified)))

		if date_diff and date_diff[0][0]:
			msgprint(
				_("{0} {1} has been modified. Please refresh.").format(self.doctype, self.name),
				raise_exception=True,
			)

	def update_status(self, status):
		self.check_modified_date()
		self.set_status(update=True, status=status)
		self.update_requested_qty()
		self.update_ordered_qty()
		self.update_reserved_qty_for_subcontract()
		self.notify_update()
		clear_doctype_notifications(self)

	def on_submit(self):
		super(PurchaseOrder, self).on_submit()

		if self.is_against_so():
			self.update_status_updater()

		self.update_prevdoc_status()
		self.update_requested_qty()
		self.update_ordered_qty()
		self.validate_budget()
		self.update_reserved_qty_for_subcontract()

		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total
		)

		self.update_blanket_order()

		update_linked_doc(self.doctype, self.name, self.inter_company_order_reference)

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
		super(PurchaseOrder, self).on_cancel()

		if self.is_against_so():
			self.update_status_updater()

		if self.has_drop_ship_item():
			self.update_delivered_qty_in_sales_order()

		self.update_reserved_qty_for_subcontract()
		self.check_on_hold_or_closed_status()

		self.db_set("status", "Cancelled")

		self.update_prevdoc_status()

		# Must be called after updating ordered qty in Material Request
		# bin uses Material Request Items to recalculate & update
		self.update_requested_qty()
		self.update_ordered_qty()

		self.update_blanket_order()

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_order_reference)

	def on_update(self):
		pass

	def update_status_updater(self):
		self.status_updater.append(
			{
				"source_dt": "Purchase Order Item",
				"target_dt": "Sales Order Item",
				"target_field": "ordered_qty",
				"target_parent_dt": "Sales Order",
				"target_parent_field": "",
				"join_field": "sales_order_item",
				"target_ref_field": "stock_qty",
				"source_field": "stock_qty",
			}
		)
		self.status_updater.append(
			{
				"source_dt": "Purchase Order Item",
				"target_dt": "Packed Item",
				"target_field": "ordered_qty",
				"target_parent_dt": "Sales Order",
				"target_parent_field": "",
				"join_field": "sales_order_packed_item",
				"target_ref_field": "qty",
				"source_field": "stock_qty",
			}
		)

	def update_delivered_qty_in_sales_order(self):
		"""Update delivered qty in Sales Order for drop ship"""
		sales_orders_to_update = []
		for item in self.items:
			if item.sales_order and item.delivered_by_supplier == 1:
				if item.sales_order not in sales_orders_to_update:
					sales_orders_to_update.append(item.sales_order)

		for so_name in sales_orders_to_update:
			so = frappe.get_doc("Sales Order", so_name)
			so.update_delivery_status()
			so.set_status(update=True)
			so.notify_update()

	def has_drop_ship_item(self):
		return any(d.delivered_by_supplier for d in self.items)

	def is_against_so(self):
		return any(d.sales_order for d in self.items if d.sales_order)

	def set_received_qty_for_drop_ship_items(self):
		for item in self.items:
			if item.delivered_by_supplier == 1:
				item.received_qty = item.qty

	def update_reserved_qty_for_subcontract(self):
		if self.is_old_subcontracting_flow:
			for d in self.supplied_items:
				if d.rm_item_code:
					stock_bin = get_bin(d.rm_item_code, d.reserve_warehouse)
					stock_bin.update_reserved_qty_for_sub_contracting(subcontract_doctype="Purchase Order")

	def update_receiving_percentage(self):
		total_qty, received_qty = 0.0, 0.0
		for item in self.items:
			received_qty += item.received_qty
			total_qty += item.qty
		if total_qty:
			self.db_set("per_received", flt(received_qty / total_qty) * 100, update_modified=False)
		else:
			self.db_set("per_received", 0, update_modified=False)


def item_last_purchase_rate(name, conversion_rate, item_code, conversion_factor=1.0):
	"""get last purchase rate for an item"""

	conversion_rate = flt(conversion_rate) or 1.0

	last_purchase_details = get_last_purchase_details(item_code, name)
	if last_purchase_details:
		last_purchase_rate = (
			last_purchase_details["base_net_rate"] * (flt(conversion_factor) or 1.0)
		) / conversion_rate
		return last_purchase_rate
	else:
		item_last_purchase_rate = frappe.get_cached_value("Item", item_code, "last_purchase_rate")
		if item_last_purchase_rate:
			return item_last_purchase_rate


@frappe.whitelist()
def close_or_unclose_purchase_orders(names, status):
	if not frappe.has_permission("Purchase Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	names = json.loads(names)
	for name in names:
		po = frappe.get_doc("Purchase Order", name)
		if po.docstatus == 1:
			if status == "Closed":
				if po.status not in ("Cancelled", "Closed") and (po.per_received < 100 or po.per_billed < 100):
					po.update_status(status)
			else:
				if po.status == "Closed":
					po.update_status("Draft")
			po.update_blanket_order()

	frappe.local.message_log = []


def set_missing_values(source, target):
	target.run_method("set_missing_values")
	target.run_method("calculate_taxes_and_totals")


@frappe.whitelist()
def make_purchase_receipt(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.received_qty)
		target.stock_qty = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.conversion_factor)
		target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate)
		target.base_amount = (
			(flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate) * flt(source_parent.conversion_rate)
		)

	doc = get_mapped_doc(
		"Purchase Order",
		source_name,
		{
			"Purchase Order": {
				"doctype": "Purchase Receipt",
				"field_map": {"supplier_warehouse": "supplier_warehouse"},
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Order Item": {
				"doctype": "Purchase Receipt Item",
				"field_map": {
					"name": "purchase_order_item",
					"parent": "purchase_order",
					"bom": "bom",
					"material_request": "material_request",
					"material_request_item": "material_request_item",
				},
				"postprocess": update_item,
				"condition": lambda doc: abs(doc.received_qty) < abs(doc.qty)
				and doc.delivered_by_supplier != 1,
			},
			"Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges", "add_if_empty": True},
		},
		target_doc,
		set_missing_values,
	)

	doc.set_onload("ignore_price_list", True)

	return doc


@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
	return get_mapped_purchase_invoice(source_name, target_doc)


@frappe.whitelist()
def make_purchase_invoice_from_portal(purchase_order_name):
	doc = get_mapped_purchase_invoice(purchase_order_name, ignore_permissions=True)
	if doc.contact_email != frappe.session.user:
		frappe.throw(_("Not Permitted"), frappe.PermissionError)
	doc.save()
	frappe.db.commit()
	frappe.response["type"] = "redirect"
	frappe.response.location = "/purchase-invoices/" + doc.name


def get_mapped_purchase_invoice(source_name, target_doc=None, ignore_permissions=False):
	def postprocess(source, target):
		target.flags.ignore_permissions = ignore_permissions
		set_missing_values(source, target)
		# Get the advance paid Journal Entries in Purchase Invoice Advance
		if target.get("allocate_advances_automatically"):
			target.set_advances()

		target.set_payment_schedule()
		target.credit_to = get_party_account("Supplier", source.supplier, source.company)

	def update_item(obj, target, source_parent):
		target.amount = flt(obj.amount) - flt(obj.billed_amt)
		target.base_amount = target.amount * flt(source_parent.conversion_rate)
		target.qty = (
			target.amount / flt(obj.rate) if (flt(obj.rate) and flt(obj.billed_amt)) else flt(obj.qty)
		)

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)
		target.cost_center = (
			obj.cost_center
			or frappe.db.get_value("Project", obj.project, "cost_center")
			or item.get("buying_cost_center")
			or item_group.get("buying_cost_center")
		)

	fields = {
		"Purchase Order": {
			"doctype": "Purchase Invoice",
			"field_map": {
				"party_account_currency": "party_account_currency",
				"supplier_warehouse": "supplier_warehouse",
			},
			"field_no_map": ["payment_terms_template"],
			"validation": {
				"docstatus": ["=", 1],
			},
		},
		"Purchase Order Item": {
			"doctype": "Purchase Invoice Item",
			"field_map": {
				"name": "po_detail",
				"parent": "purchase_order",
			},
			"postprocess": update_item,
			"condition": lambda doc: (doc.base_amount == 0 or abs(doc.billed_amt) < abs(doc.amount)),
		},
		"Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges", "add_if_empty": True},
	}

	doc = get_mapped_doc(
		"Purchase Order",
		source_name,
		fields,
		target_doc,
		postprocess,
		ignore_permissions=ignore_permissions,
	)
	doc.set_onload("ignore_price_list", True)

	return doc


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Purchase Orders"),
		}
	)
	return list_context


@frappe.whitelist()
def update_status(status, name):
	po = frappe.get_doc("Purchase Order", name)
	po.update_status(status)
	po.update_delivered_qty_in_sales_order()


@frappe.whitelist()
def make_inter_company_sales_order(source_name, target_doc=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_transaction

	return make_inter_company_transaction("Purchase Order", source_name, target_doc)


@frappe.whitelist()
def make_subcontracting_order(source_name, target_doc=None):
	return get_mapped_subcontracting_order(source_name, target_doc)


def get_mapped_subcontracting_order(source_name, target_doc=None):

	if target_doc and isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
		for key in ["service_items", "items", "supplied_items"]:
			if key in target_doc:
				del target_doc[key]
		target_doc = json.dumps(target_doc)

	target_doc = get_mapped_doc(
		"Purchase Order",
		source_name,
		{
			"Purchase Order": {
				"doctype": "Subcontracting Order",
				"field_map": {},
				"field_no_map": ["total_qty", "total", "net_total"],
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Order Item": {
				"doctype": "Subcontracting Order Service Item",
				"field_map": {},
				"field_no_map": [],
			},
		},
		target_doc,
	)

	target_doc.populate_items_table()

	if target_doc.set_warehouse:
		for item in target_doc.items:
			item.warehouse = target_doc.set_warehouse
	else:
		source_doc = frappe.get_doc("Purchase Order", source_name)
		if source_doc.set_warehouse:
			for item in target_doc.items:
				item.warehouse = source_doc.set_warehouse
		else:
			for idx, item in enumerate(target_doc.items):
				item.warehouse = source_doc.items[idx].warehouse

	return target_doc


@frappe.whitelist()
def is_subcontracting_order_created(po_name) -> bool:
	count = frappe.db.count(
		"Subcontracting Order", {"purchase_order": po_name, "status": ["not in", ["Draft", "Cancelled"]]}
	)

	return True if count else False
