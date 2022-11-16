# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import json
from frappe.utils import cstr, flt, cint
from frappe import msgprint, _
from frappe.model.mapper import get_mapped_doc
from erpnext.controllers.buying_controller import BuyingController
from erpnext.stock.doctype.item.item import get_last_purchase_details
from erpnext.stock.stock_balance import update_bin_qty, get_ordered_qty
from frappe.desk.notifications import clear_doctype_notifications
from erpnext.buying.utils import validate_for_items, check_on_hold_or_closed_status
from erpnext.stock.utils import get_bin
from erpnext.accounts.party import get_party_account_currency
from six import string_types
from erpnext.accounts.doctype.sales_invoice.sales_invoice import validate_inter_company_party, update_linked_doc,\
	unlink_inter_company_doc


form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}


class PurchaseOrder(BuyingController):
	def __init__(self, *args, **kwargs):
		super(PurchaseOrder, self).__init__(*args, **kwargs)
		self.status_map = [
			["Draft", None],
			["To Receive and Bill", "eval:self.per_received < 100 and self.per_completed < 100 and self.docstatus == 1"],
			["To Bill", "eval:self.per_received >= 100 and self.per_completed < 100 and self.docstatus == 1"],
			["To Receive", "eval:self.per_received < 100 and self.per_completed == 100 and self.docstatus == 1"],
			["Completed", "eval:self.per_received >= 100 and self.per_completed == 100 and self.docstatus == 1"],
			["Delivered", "eval:self.status=='Delivered'"],
			["Cancelled", "eval:self.docstatus==2"],
			["On Hold", "eval:self.status=='On Hold'"],
			["Closed", "eval:self.status=='Closed'"],
		]

	def validate(self):
		super(PurchaseOrder, self).validate()

		self.validate_supplier()
		self.validate_schedule_date()
		validate_for_items(self)
		self.check_on_hold_or_closed_status()

		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "stock_qty")

		self.validate_minimum_order_qty()

		self.validate_for_subcontracting()
		self.validate_bom_for_subcontracting_items()
		self.create_raw_materials_supplied("supplied_items")

		validate_inter_company_party(self.doctype, self.supplier, self.company, self.inter_company_reference)

		self.validate_with_previous_doc()
		self.set_receipt_status()
		self.set_billing_status()
		self.set_status()
		self.set_title()

	def on_submit(self):
		super(PurchaseOrder, self).on_submit()

		self.update_previous_doc_status()
		self.update_requested_qty()
		self.update_ordered_qty()
		self.validate_budget()

		if self.is_subcontracted == "Yes":
			self.update_reserved_qty_for_subcontract()

		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
			self.company, self.base_grand_total)

		self.update_blanket_order()

		update_linked_doc(self.doctype, self.name, self.inter_company_reference)

	def on_cancel(self):
		super(PurchaseOrder, self).on_cancel()

		if self.has_drop_ship_item():
			self.update_delivered_qty_in_sales_order()

		if self.is_subcontracted == "Yes":
			self.update_reserved_qty_for_subcontract()

		self.check_on_hold_or_closed_status()

		self.db_set('status', 'Cancelled')

		self.update_previous_doc_status()

		# Must be called after updating ordered qty in Material Request
		self.update_requested_qty()
		self.update_ordered_qty()

		self.update_blanket_order()

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_reference)

	def on_update(self):
		pass

	def set_title(self):
		self.title = self.supplier_name or self.supplier

	def update_previous_doc_status(self):
		material_requests = set()
		material_request_row_names = set()
		sales_orders = set()

		for d in self.items:
			if d.material_request:
				material_requests.add(d.material_request)
			if d.material_request_item:
				material_request_row_names.add(d.material_request_item)
			if d.sales_order:
				sales_orders.add(d.sales_order)

		# Update Material Requests
		for name in material_requests:
			doc = frappe.get_doc("Material Request", name)
			doc.set_completion_status(update=True)
			doc.validate_ordered_qty(from_doctype=self.doctype, row_names=material_request_row_names)
			doc.set_status(update=True)
			doc.notify_update()

		# Update Sales Orders
		for name in sales_orders:
			doc = frappe.get_doc("Sales Order", name)
			doc.set_purchase_status(update=True)
			doc.set_status(update=True)
			doc.notify_update()

	def update_status(self, status):
		self.check_modified_date()
		self.set_status(update=True, status=status)
		self.update_requested_qty()
		self.update_ordered_qty()
		if self.is_subcontracted == "Yes":
			self.update_reserved_qty_for_subcontract()

		self.notify_update()
		clear_doctype_notifications(self)

	def validate_with_previous_doc(self):
		super(PurchaseOrder, self).validate_with_previous_doc({
			"Supplier Quotation": {
				"ref_dn_field": "supplier_quotation",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Supplier Quotation Item": {
				"ref_dn_field": "supplier_quotation_item",
				"compare_fields": [["project", "="], ["item_code", "="],
					["uom", "="], ["conversion_factor", "="]],
				"is_child_table": True
			},
			"Material Request": {
				"ref_dn_field": "material_request",
				"compare_fields": [["company", "="]],
			},
			"Material Request Item": {
				"ref_dn_field": "material_request_item",
				"compare_fields": [["item_code", "="]],
				"is_child_table": True
			}
		})

		if cint(frappe.get_cached_value('Buying Settings', None, 'maintain_same_rate')):
			self.validate_rate_with_reference_doc([["Supplier Quotation", "supplier_quotation", "supplier_quotation_item"]])

	def set_receipt_status(self, update=False, update_modified=True):
		data = self.get_receipt_status_data()

		# update values in rows
		for d in self.items:
			d.received_qty = flt(data.received_qty_map.get(d.name))
			if not d.received_qty:
				d.received_qty = flt(data.service_billed_qty_map.get(d.name))

			d.total_returned_qty = flt(data.total_returned_qty_map.get(d.name))

			if update:
				d.db_set({
					'received_qty': d.received_qty,
					'total_returned_qty': d.total_returned_qty,
				}, update_modified=update_modified)

		# update percentage in parent
		self.per_received = self.calculate_status_percentage('received_qty', 'qty', data.receivable_rows)
		if self.per_received is None:
			self.per_received = flt(self.calculate_status_percentage('received_qty', 'qty', self.items))

		if update:
			self.db_set({
				'per_received': self.per_received,
			}, update_modified=update_modified)

	def set_billing_status(self, update=False, update_modified=True):
		data = self.get_billing_status_data()

		# update values in rows
		for d in self.items:
			d.billed_qty = flt(data.billed_qty_map.get(d.name))
			d.billed_amt = flt(data.billed_amount_map.get(d.name))
			d.returned_qty = flt(data.receipt_return_qty_map.get(d.name))
			if update:
				d.db_set({
					'billed_qty': d.billed_qty,
					'billed_amt': d.billed_amt,
					'returned_qty': d.returned_qty,
				}, update_modified=update_modified)

		# update percentage in parent
		self.per_returned = flt(self.calculate_status_percentage('returned_qty', 'qty', self.items))
		self.per_billed = self.calculate_status_percentage('billed_qty', 'qty', self.items)
		self.per_completed = self.calculate_status_percentage(['billed_qty', 'returned_qty'], 'qty', self.items)
		if self.per_completed is None:
			total_billed_qty = flt(sum([flt(d.billed_qty) for d in self.items]), self.precision('total_qty'))
			self.per_billed = 100 if total_billed_qty else 0
			self.per_completed = 100 if total_billed_qty else 0

		if update:
			self.db_set({
				'per_billed': self.per_billed,
				'per_returned': self.per_returned,
				'per_completed': self.per_completed,
			}, update_modified=update_modified)

	def get_receipt_status_data(self):
		out = frappe._dict()

		out.receivable_rows = []
		out.received_qty_map = {}
		out.total_returned_qty_map = {}
		out.service_billed_qty_map = {}

		reveived_by_prec_row_names = []
		received_by_billing_row_names = []

		for d in self.items:
			if d.is_stock_item or d.is_fixed_asset:
				out.receivable_rows.append(d)

				if d.delivered_by_supplier:
					out.received_qty_map[d.name] = d.qty
				else:
					reveived_by_prec_row_names.append(d.name)
			else:
				received_by_billing_row_names.append(d.name)

		# Get Received Qty
		if self.docstatus == 1:
			if reveived_by_prec_row_names:
				# Received By Purchase Receipt
				recieved_by_prec = frappe.db.sql("""
					select i.purchase_order_item, i.received_qty, p.is_return, p.reopen_order
					from `tabPurchase Receipt Item` i
					inner join `tabPurchase Receipt` p on p.name = i.parent
					where p.docstatus = 1 and i.purchase_order_item in %s
				""", [reveived_by_prec_row_names], as_dict=1)

				for d in recieved_by_prec:
					if not d.is_return or d.reopen_order:
						out.received_qty_map.setdefault(d.purchase_order_item, 0)
						out.received_qty_map[d.purchase_order_item] += d.received_qty

					if d.is_return:
						out.total_returned_qty_map.setdefault(d.purchase_order_item, 0)
						out.total_returned_qty_map[d.purchase_order_item] -= d.received_qty

				# Received By Purchase Invoice
				received_by_pinv = frappe.db.sql("""
					select i.purchase_order_item, i.received_qty, p.is_return, p.reopen_order
					from `tabPurchase Invoice Item` i
					inner join `tabPurchase Invoice` p on p.name = i.parent
					where p.docstatus = 1 and p.update_stock = 1 and i.purchase_order_item in %s
				""", [reveived_by_prec_row_names], as_dict=1)

				for d in received_by_pinv:
					if not d.is_return or d.reopen_order:
						out.received_qty_map.setdefault(d.purchase_order_item, 0)
						out.received_qty_map[d.purchase_order_item] += d.received_qty

					if d.is_return:
						out.total_returned_qty_map.setdefault(d.purchase_order_item, 0)
						out.total_returned_qty_map[d.purchase_order_item] -= d.received_qty

			# Get Service Items Billed Qty as Delivered Qty
			if received_by_billing_row_names:
				out.service_billed_qty_map = dict(frappe.db.sql("""
					select i.purchase_order_item, sum(i.qty)
					from `tabPurchase Invoice Item` i
					inner join `tabPurchase Invoice` p on p.name = i.parent
					where p.docstatus = 1 and (p.is_return = 0 or p.reopen_order = 1)
						and i.purchase_order_item in %s
					group by i.purchase_order_item
				""", [received_by_billing_row_names]))

		return out

	def get_billing_status_data(self):
		out = frappe._dict()
		out.billed_qty_map = {}
		out.billed_amount_map = {}
		out.receipt_return_qty_map = {}

		if self.docstatus == 1:
			row_names = [d.name for d in self.items]
			if row_names:
				# Billed By Purchase Invoice
				billed_by_pinv = frappe.db.sql("""
					select i.purchase_order_item, i.qty, i.amount, p.is_return, p.reopen_order
					from `tabPurchase Invoice Item` i
					inner join `tabPurchase Invoice` p on p.name = i.parent
					where p.docstatus = 1 and (p.is_return = 0 or p.reopen_order = 1)
						and i.purchase_order_item in %s
				""", [row_names], as_dict=1)

				for d in billed_by_pinv:
					out.billed_amount_map.setdefault(d.purchase_order_item, 0)
					out.billed_amount_map[d.purchase_order_item] += d.amount

					out.billed_qty_map.setdefault(d.purchase_order_item, 0)
					out.billed_qty_map[d.purchase_order_item] += d.qty

				# Returned By Purchase Receipt
				out.receipt_return_qty_map = dict(frappe.db.sql("""
					select i.purchase_order_item, -1 * sum(i.qty)
					from `tabPurchase Receipt Item` i
					inner join `tabPurchase Receipt` p on p.name = i.parent
					where p.docstatus = 1 and p.is_return = 1 and p.reopen_order = 0 and i.purchase_order_item in %s
					group by i.purchase_order_item
				""", [row_names]))

		return out

	def validate_received_qty(self, from_doctype=None, row_names=None):
		self.validate_completed_qty('received_qty', 'qty', self.items,
			allowance_type='qty', from_doctype=from_doctype, row_names=row_names)

	def validate_billed_qty(self, from_doctype=None, row_names=None):
		self.validate_completed_qty(['billed_qty', 'returned_qty'], 'qty', self.items,
			allowance_type='billing', from_doctype=from_doctype, row_names=row_names)

		if frappe.get_cached_value("Accounts Settings", None, "validate_over_billing_in_sales_invoice"):
			self.validate_completed_qty('billed_amt', 'amount', self.items,
				allowance_type='billing', from_doctype=from_doctype, row_names=row_names)

	def update_delivered_qty_in_sales_order(self):
		"""Update delivered qty in Sales Order for drop ship"""
		sales_orders_to_update = []
		for item in self.items:
			if item.sales_order and item.delivered_by_supplier == 1:
				if item.sales_order not in sales_orders_to_update:
					sales_orders_to_update.append(item.sales_order)

		for so_name in sales_orders_to_update:
			so = frappe.get_doc("Sales Order", so_name)
			so.set_delivery_status(update=True)
			so.set_status(update=True)
			so.notify_update()

	def validate_supplier(self):
		prevent_po = frappe.get_cached_value("Supplier", self.supplier, 'prevent_pos')
		if prevent_po:
			standing = frappe.get_cached_value("Supplier Scorecard", self.supplier, 'status')
			if standing:
				frappe.throw(_("Purchase Orders are not allowed for {0} due to a scorecard standing of {1}.")
					.format(self.supplier, standing))

		warn_po = frappe.get_cached_value("Supplier", self.supplier, 'warn_pos')
		if warn_po:
			standing = frappe.get_cached_value("Supplier Scorecard", self.supplier, 'status')
			frappe.msgprint(_("{0} currently has a {1} Supplier Scorecard standing, and Purchase Orders to this supplier should be issued with caution.")
				.format(self.supplier, standing), title=_("Caution"), indicator='orange')

		self.party_account_currency = get_party_account_currency("Supplier", self.supplier, self.company)

	def validate_minimum_order_qty(self):
		if not self.get("items"):
			return

		items = list(set([d.item_code for d in self.get("items")]))

		itemwise_min_order_qty = frappe._dict(frappe.db.sql("""select name, min_order_qty
			from tabItem where name in ({0})""".format(", ".join(["%s"] * len(items))), items))

		itemwise_qty = frappe._dict()
		for d in self.get("items"):
			itemwise_qty.setdefault(d.item_code, 0)
			itemwise_qty[d.item_code] += flt(d.stock_qty)

		for item_code, qty in itemwise_qty.items():
			if flt(qty) < flt(itemwise_min_order_qty.get(item_code)):
				frappe.throw(_("Item {0}: Ordered qty {1} cannot be less than minimum order qty {2} (defined in Item).")
					.format(item_code, qty, itemwise_min_order_qty.get(item_code)))

	def validate_bom_for_subcontracting_items(self):
		if self.is_subcontracted == "Yes":
			for item in self.items:
				if not item.bom:
					frappe.throw(_("BOM is not specified for subcontracting item {0} at row {1}"\
						.format(item.item_code, item.idx)))

	def get_schedule_dates(self):
		for d in self.get('items'):
			if d.material_request_item and not d.schedule_date:
				d.schedule_date = frappe.db.get_value("Material Request Item",
						d.material_request_item, "schedule_date")

	@frappe.whitelist()
	def get_last_purchase_rate(self):
		"""get last purchase rates for all items"""

		conversion_rate = flt(self.get('conversion_rate')) or 1.0
		for d in self.get("items"):
			if d.item_code:
				last_purchase_details = get_last_purchase_details(d.item_code, self.name)
				if last_purchase_details:
					d.base_price_list_rate = (last_purchase_details['base_price_list_rate'] *
						(flt(d.conversion_factor) or 1.0))
					d.discount_percentage = last_purchase_details['discount_percentage']
					d.base_rate = last_purchase_details['base_rate'] * (flt(d.conversion_factor) or 1.0)
					d.price_list_rate = d.base_price_list_rate / conversion_rate
					d.rate = d.base_rate / conversion_rate
					d.last_purchase_rate = d.rate
				else:
					item_last_purchase_rate = frappe.get_cached_value("Item", d.item_code, "last_purchase_rate")
					if item_last_purchase_rate:
						d.base_price_list_rate = d.base_rate = d.price_list_rate \
							= d.rate = d.last_purchase_rate = item_last_purchase_rate

	# Check for Closed status
	def check_on_hold_or_closed_status(self):
		check_list = []
		for d in self.get('items'):
			if d.meta.get_field('material_request') and d.material_request and d.material_request not in check_list:
				check_list.append(d.material_request)
				check_on_hold_or_closed_status('Material Request', d.material_request)

	def update_requested_qty(self):
		material_request_map = {}
		for d in self.get("items"):
			if d.material_request_item:
				material_request_map.setdefault(d.material_request, []).append(d.material_request_item)

		for mr, mr_item_rows in material_request_map.items():
			if mr and mr_item_rows:
				mr_obj = frappe.get_doc("Material Request", mr)

				if mr_obj.status in ["Stopped", "Cancelled"]:
					frappe.throw(_("Material Request {0} is cancelled or stopped").format(mr), frappe.InvalidStatusError)

				mr_obj.update_requested_qty(mr_item_rows)

	def update_ordered_qty(self, po_item_rows=None):
		"""update requested qty (before ordered_qty is updated)"""
		item_wh_list = []
		for d in self.get("items"):
			if (not po_item_rows or d.name in po_item_rows) \
				and [d.item_code, d.warehouse] not in item_wh_list \
				and frappe.get_cached_value("Item", d.item_code, "is_stock_item") \
				and d.warehouse and not d.delivered_by_supplier:
					item_wh_list.append([d.item_code, d.warehouse])
		for item_code, warehouse in item_wh_list:
			update_bin_qty(item_code, warehouse, {
				"ordered_qty": get_ordered_qty(item_code, warehouse)
			})

	def check_modified_date(self):
		mod_db = frappe.db.sql("select modified from `tabPurchase Order` where name = %s",
			self.name)
		date_diff = frappe.db.sql("select '%s' - '%s' " % (mod_db[0][0], cstr(self.modified)))

		if date_diff and date_diff[0][0]:
			msgprint(_("{0} {1} has been modified. Please refresh.").format(self.doctype, self.name),
				raise_exception=True)

	def has_drop_ship_item(self):
		return any([d.delivered_by_supplier for d in self.items])

	def is_against_so(self):
		return any([d.sales_order for d in self.items if d.sales_order])

	def update_reserved_qty_for_subcontract(self):
		for d in self.supplied_items:
			if d.rm_item_code:
				stock_bin = get_bin(d.rm_item_code, d.reserve_warehouse)
				stock_bin.update_reserved_qty_for_sub_contracting()

	def update_receiving_percentage(self):
		total_qty, received_qty = 0.0, 0.0
		for item in self.items:
			received_qty += item.received_qty
			total_qty += item.qty
		if total_qty:
			self.db_set("per_received", flt(received_qty/total_qty) * 100, update_modified=False)
		else:
			self.db_set("per_received", 0, update_modified=False)


def item_last_purchase_rate(name, conversion_rate, item_code, conversion_factor= 1.0):
	"""get last purchase rate for an item"""

	conversion_rate = flt(conversion_rate) or 1.0

	last_purchase_details =  get_last_purchase_details(item_code, name)
	if last_purchase_details:
		last_purchase_rate = (last_purchase_details['base_net_rate'] * (flt(conversion_factor) or 1.0)) / conversion_rate
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
	from erpnext.vehicles.doctype.vehicle.vehicle import split_vehicle_items_by_qty, set_reserved_vehicles_from_po
	split_vehicle_items_by_qty(target)
	set_reserved_vehicles_from_po(source, target)

	target.ignore_pricing_rule = 1
	target.run_method("set_missing_values")
	target.run_method("calculate_taxes_and_totals")


@frappe.whitelist()
def make_purchase_receipt(source_name, target_doc=None):
	def get_pending_qty(source):
		return flt(source.qty) - flt(source.received_qty)

	def item_condition(source, source_parent, target_parent):
		if source.name in [d.purchase_order_item for d in target_parent.get('items') if d.purchase_order_item]:
			return False

		if source.delivered_by_supplier:
			return False

		if not source.is_stock_item and not source.is_fixed_asset:
			return False

		return abs(source.received_qty) < abs(source.qty)

	def update_item(source, target, source_parent, target_parent):
		target.qty = get_pending_qty(source)

	doc = get_mapped_doc("Purchase Order", source_name,	{
		"Purchase Order": {
			"doctype": "Purchase Receipt",
			"field_map": {
				"per_billed": "per_billed",
				"supplier_warehouse": "supplier_warehouse",
				"remarks": "remarks"
			},
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"Purchase Order Item": {
			"doctype": "Purchase Receipt Item",
			"field_map": {
				"name": "purchase_order_item",
				"parent": "purchase_order",
				"bom": "bom",
				"material_request": "material_request",
				"material_request_item": "material_request_item"
			},
			"postprocess": update_item,
			"condition": item_condition,
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return doc


@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
	return get_mapped_purchase_invoice(source_name, target_doc)


@frappe.whitelist()
def make_purchase_invoice_from_portal(purchase_order_name):
	doc = get_mapped_purchase_invoice(purchase_order_name, ignore_permissions=True)
	if doc.contact_email != frappe.session.user:
		frappe.throw(_('Not Permitted'), frappe.PermissionError)
	doc.save()
	frappe.db.commit()
	frappe.response['type'] = 'redirect'
	frappe.response.location = '/purchase-invoices/' + doc.name


def get_mapped_purchase_invoice(source_name, target_doc=None, ignore_permissions=False):
	unbilled_pr_qty_map = get_unbilled_pr_qty_map(source_name)

	def get_pending_qty(source):
		billable_qty = flt(source.qty) - flt(source.billed_qty) - flt(source.returned_qty)
		unbilled_pr_qty = flt(unbilled_pr_qty_map.get(source.name))
		return max(billable_qty - unbilled_pr_qty, 0)

	def item_condition(source, source_parent, target_parent):
		if source.name in [d.purchase_order_item for d in target_parent.get('items') if d.purchase_order_item and not d.purchase_receipt_item]:
			return False

		return get_pending_qty(source)

	def update_item(source, target, source_parent, target_parent):
		target.qty = get_pending_qty(source)

	def postprocess(source, target):
		target.flags.ignore_permissions = ignore_permissions
		set_missing_values(source, target)

		if target.get("allocate_advances_automatically"):
			target.set_advances()

	fields = {
		"Purchase Order": {
			"doctype": "Purchase Invoice",
			"field_map": {
				"party_account_currency": "party_account_currency",
				"supplier_warehouse":"supplier_warehouse",
				"remarks": "remarks",
			},
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"Purchase Order Item": {
			"doctype": "Purchase Invoice Item",
			"field_map": {
				"name": "purchase_order_item",
				"parent": "purchase_order",
			},
			"postprocess": update_item,
			"condition": item_condition,
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
			"add_if_empty": True
		},
	}

	if frappe.get_single("Accounts Settings").automatically_fetch_payment_terms == 1:
		fields["Payment Schedule"] = {
			"doctype": "Payment Schedule",
			"add_if_empty": True
		}

	doc = get_mapped_doc("Purchase Order", source_name,	fields,
		target_doc, postprocess, ignore_permissions=ignore_permissions)

	return doc


def get_unbilled_pr_qty_map(purchase_order):
	unbilled_pr_qty_map = {}

	item_data = frappe.db.sql("""
		select purchase_order_item, qty - billed_qty
		from `tabPurchase Receipt Item`
		where purchase_order=%s and docstatus=1
	""", purchase_order)

	for purchase_receipt_item, qty in item_data:
		if not unbilled_pr_qty_map.get(purchase_receipt_item):
			unbilled_pr_qty_map[purchase_receipt_item] = 0
		unbilled_pr_qty_map[purchase_receipt_item] += qty

	return unbilled_pr_qty_map


@frappe.whitelist()
def make_rm_stock_entry(purchase_order, rm_items):
	if isinstance(rm_items, string_types):
		rm_items_list = json.loads(rm_items)
	else:
		frappe.throw(_("No Items available for transfer"))

	if rm_items_list:
		fg_items = list(set(d["item_code"] for d in rm_items_list))
	else:
		frappe.throw(_("No Items selected for transfer"))

	if purchase_order:
		purchase_order = frappe.get_doc("Purchase Order", purchase_order)

	if fg_items:
		items = tuple(set(d["rm_item_code"] for d in rm_items_list))
		item_wh = get_item_details(items)

		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Send to Subcontractor"
		stock_entry.purchase_order = purchase_order.name
		stock_entry.supplier = purchase_order.supplier
		stock_entry.supplier_name = purchase_order.supplier_name
		stock_entry.supplier_address = purchase_order.supplier_address
		stock_entry.address_display = purchase_order.address_display
		stock_entry.company = purchase_order.company
		stock_entry.to_warehouse = purchase_order.supplier_warehouse
		stock_entry.set_stock_entry_type()

		for item_code in fg_items:
			for rm_item_data in rm_items_list:
				if rm_item_data["item_code"] == item_code:
					rm_item_code = rm_item_data["rm_item_code"]
					items_dict = {
						rm_item_code: {
							"purchase_order_item": rm_item_data.get("name"),
							"item_name": rm_item_data["item_name"],
							"description": item_wh.get(rm_item_code, {}).get('description', ""),
							'qty': rm_item_data["qty"],
							'from_warehouse': rm_item_data["warehouse"],
							'stock_uom': rm_item_data["stock_uom"],
							'main_item_code': rm_item_data["item_code"],
							'allow_alternative_item': item_wh.get(rm_item_code, {}).get('allow_alternative_item')
						}
					}
					stock_entry.add_to_stock_entry_detail(items_dict)
		return stock_entry.as_dict()
	else:
		frappe.throw(_("No Items selected for transfer"))
	return purchase_order.name


def get_item_details(items):
	item_details = {}
	for d in frappe.db.sql("""select item_code, description, allow_alternative_item from `tabItem`
		where name in ({0})""".format(", ".join(["%s"] * len(items))), items, as_dict=1):
		item_details[d.item_code] = d

	return item_details


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Purchase Orders'),
	})
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
