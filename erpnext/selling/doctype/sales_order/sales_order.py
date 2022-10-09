# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
import frappe.utils
from frappe.utils import cstr, flt, getdate, cint, nowdate, add_days, get_link_to_form
from frappe import _
from six import string_types
from frappe.model.utils import get_fetch_values
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.stock_balance import update_bin_qty, get_reserved_qty
from frappe.desk.notifications import clear_doctype_notifications
from frappe.contacts.doctype.address.address import get_company_address
from erpnext.controllers.selling_controller import SellingController
from erpnext.controllers.accounts_controller import get_default_taxes_and_charges
from erpnext.vehicles.doctype.vehicle.vehicle import split_vehicle_items_by_qty, set_reserved_vehicles_from_so
from frappe.automation.doctype.auto_repeat.auto_repeat import get_next_schedule_date
from erpnext.selling.doctype.customer.customer import check_credit_limit
from erpnext.manufacturing.doctype.production_plan.production_plan import get_items_for_material_requests
from erpnext.accounts.doctype.sales_invoice.sales_invoice import validate_inter_company_party, update_linked_doc,\
	unlink_inter_company_doc


form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}


class WarehouseRequired(frappe.ValidationError):
	pass


class SalesOrder(SellingController):
	def __init__(self, *args, **kwargs):
		super(SalesOrder, self).__init__(*args, **kwargs)
		self.status_map = [
			["Draft", None],
			["To Deliver and Bill", "eval:self.per_delivered < 100 and self.per_completed < 100 and self.docstatus == 1"],
			["To Bill", "eval:(self.per_delivered == 100 or self.skip_delivery_note) and self.per_completed < 100 and self.docstatus == 1"],
			["To Deliver", "eval:self.per_delivered < 100 and self.per_completed == 100 and self.docstatus == 1 and not self.skip_delivery_note"],
			["Completed", "eval:(self.per_delivered == 100 or self.skip_delivery_note) and self.per_completed == 100 and self.docstatus == 1"],
			["Cancelled", "eval:self.docstatus==2"],
			["Closed", "eval:self.status=='Closed'"],
			["On Hold", "eval:self.status=='On Hold'"],
		]

	def validate(self):
		super(SalesOrder, self).validate()
		self.set_skip_delivery_note()
		self.validate_delivery_date()
		self.validate_po()
		self.validate_project_customer()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_for_items()
		self.validate_warehouse()
		self.validate_drop_ship()
		self.validate_serial_no_based_delivery()
		validate_inter_company_party(self.doctype, self.customer, self.company, self.inter_company_reference)

		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code
			validate_coupon_code(self.coupon_code)

		from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
		make_packing_list(self)

		self.validate_with_previous_doc()
		self.set_delivery_status()
		self.set_billing_status()
		self.set_purchase_status()
		self.set_status()
		self.set_title()

	def before_submit(self):
		self.validate_delivery_date_required()
		self.validate_item_code_mandatory()

	def on_submit(self):
		self.check_credit_limit()
		self.update_reserved_qty()

		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype, self.company, self.base_grand_total, self)
		self.update_previous_doc_status()

		self.update_blanket_order()

		update_linked_doc(self.doctype, self.name, self.inter_company_reference)
		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count
			update_coupon_code_count(self.coupon_code, 'used')

	def on_cancel(self):
		super(SalesOrder, self).on_cancel()

		# Cannot cancel closed SO
		if self.status == 'Closed':
			frappe.throw(_("Closed order cannot be cancelled. Unclose to cancel."))

		self.check_nextdoc_docstatus()
		self.update_reserved_qty()
		self.update_previous_doc_status()

		frappe.db.set(self, 'status', 'Cancelled')

		self.update_blanket_order()

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_reference)
		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count
			update_coupon_code_count(self.coupon_code, 'cancelled')

	def before_update_after_submit(self):
		super(SalesOrder, self).before_update_after_submit()
		self.validate_po()
		self.validate_drop_ship()
		self.validate_supplier_after_submit()
		self.validate_delivery_date()

	def set_title(self):
		self.title = self.customer_name or self.customer

	def set_indicator(self):
		"""Set indicator for portal"""
		if self.per_completed < 100 and self.per_delivered < 100:
			self.indicator_color = "orange"
			self.indicator_title = _("Not Paid and Not Delivered")

		elif self.per_completed == 100 and self.per_delivered < 100:
			self.indicator_color = "orange"
			self.indicator_title = _("Paid and Not Delivered")

		else:
			self.indicator_color = "green"
			self.indicator_title = _("Paid")

	def update_status(self, status):
		self.check_modified_date()
		self.set_status(update=True, status=status)
		self.update_project_billing_and_sales()
		self.update_reserved_qty()
		self.notify_update()
		clear_doctype_notifications(self)

	def validate_with_previous_doc(self):
		super(SalesOrder, self).validate_with_previous_doc({
			"Quotation": {
				"ref_dn_field": "quotation",
				"compare_fields": [["company", "="], ["order_type", "="]]
			}
		})

	def update_previous_doc_status(self):
		for quotation in list(set([d.quotation for d in self.get("items")])):
			if quotation:
				doc = frappe.get_doc("Quotation", quotation)
				if doc.docstatus == 2:
					frappe.throw(_("Quotation {0} is cancelled").format(quotation))

				doc.set_status(update=True)
				doc.set_ordered_status(update=True)
				doc.update_opportunity()
				doc.notify_update()

		self.update_project_billing_and_sales()

	def set_delivery_status(self, update=False, update_modified=True):
		data = self.get_delivery_status_data()

		# update values in rows
		for d in self.items:
			d.delivered_qty = flt(data.delivered_qty_map.get(d.name))
			if not d.delivered_qty:
				d.delivered_qty = flt(data.service_billed_qty_map.get(d.name))

			d.total_returned_qty = flt(data.total_returned_qty_map.get(d.name))

			if update:
				d.db_set({
					'delivered_qty': d.delivered_qty,
					'total_returned_qty': d.total_returned_qty,
				}, update_modified=update_modified)

		# update percentage in parent
		self.per_delivered = self.calculate_status_percentage('delivered_qty', 'qty', data.deliverable_rows)
		if self.per_delivered is None:
			self.per_delivered = flt(self.calculate_status_percentage('delivered_qty', 'qty', self.items))

		# update delivery_status
		self.delivery_status = self.get_completion_status('per_delivered', 'Delivered')

		if update:
			self.db_set({
				'per_delivered': self.per_delivered,
				'delivery_status': self.delivery_status,
			}, update_modified=update_modified)

	def set_billing_status(self, update=False, update_modified=True):
		data = self.get_billing_status_data()

		# update values in rows
		for d in self.items:
			d.billed_qty = flt(data.billed_qty_map.get(d.name))
			d.billed_amt = flt(data.billed_amount_map.get(d.name))
			d.returned_qty = flt(data.delivery_return_qty_map.get(d.name))
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

		# update billing_status
		self.billing_status = self.get_completion_status('per_billed', 'Billed')

		if update:
			self.db_set({
				'per_billed': self.per_billed,
				'per_returned': self.per_returned,
				'per_completed': self.per_completed,
				'billing_status': self.billing_status,
			}, update_modified=update_modified)

	def set_purchase_status(self, update=False, update_modified=True):
		purchase_order_qty_map = self.get_purchase_order_qty_map()

		# update values in rows
		for d in self.items:
			d.ordered_qty = flt(purchase_order_qty_map.get(d.name))

			if update:
				d.db_set({
					'ordered_qty': d.ordered_qty,
				}, update_modified=update_modified)

	def get_delivery_status_data(self):
		out = frappe._dict()

		out.deliverable_rows = []
		out.delivered_qty_map = {}
		out.total_returned_qty_map = {}
		out.service_billed_qty_map = {}

		delivery_by_supplier_row_names = []
		delivery_by_stock_row_names = []
		delivery_by_billing_row_names = []

		for d in self.items:
			if d.is_stock_item or d.is_fixed_asset:
				out.deliverable_rows.append(d)

				if d.delivered_by_supplier:
					delivery_by_supplier_row_names.append(d.name)
				else:
					delivery_by_stock_row_names.append(d.name)
			else:
				delivery_by_billing_row_names.append(d.name)

		# Get Delivered Qty
		if self.docstatus == 1:
			if delivery_by_stock_row_names:
				# Delivered By Delivery Note
				delivered_by_dn = frappe.db.sql("""
					select i.sales_order_item, i.qty, p.is_return, p.reopen_order
					from `tabDelivery Note Item` i
					inner join `tabDelivery Note` p on p.name = i.parent
					where p.docstatus = 1 and i.sales_order_item in %s
				""", [delivery_by_stock_row_names], as_dict=1)

				for d in delivered_by_dn:
					if not d.is_return or d.reopen_order:
						out.delivered_qty_map.setdefault(d.sales_order_item, 0)
						out.delivered_qty_map[d.sales_order_item] += d.qty

					if d.is_return:
						out.total_returned_qty_map.setdefault(d.sales_order_item, 0)
						out.total_returned_qty_map[d.sales_order_item] -= d.qty

				# Delivered By Sales Invoice
				delivered_by_sinv = frappe.db.sql("""
					select i.sales_order_item, i.qty, p.is_return, p.reopen_order
					from `tabSales Invoice Item` i
					inner join `tabSales Invoice` p on p.name = i.parent
					where p.docstatus = 1 and p.update_stock = 1 and i.sales_order_item in %s
				""", [delivery_by_stock_row_names], as_dict=1)

				for d in delivered_by_sinv:
					if not d.is_return or d.reopen_order:
						out.delivered_qty_map.setdefault(d.sales_order_item, 0)
						out.delivered_qty_map[d.sales_order_item] += d.qty

					if d.is_return:
						out.total_returned_qty_map.setdefault(d.sales_order_item, 0)
						out.total_returned_qty_map[d.sales_order_item] -= d.qty

			if delivery_by_supplier_row_names:
				# Delivered By Purchase Order
				delivered_by_po = frappe.db.sql("""
					select i.sales_order_item, i.qty
					from `tabPurchase Order Item` i
					inner join `tabPurchase Order` p on p.name = i.parent
					where p.docstatus = 1 and p.status = 'Delivered'
						and i.sales_order_item in %s
				""", [delivery_by_supplier_row_names], as_dict=1)

				for d in delivered_by_po:
					out.delivered_qty_map.setdefault(d.sales_order_item, 0)
					out.delivered_qty_map[d.sales_order_item] += d.qty

			# Get Service Items Billed Qty as Delivered Qty
			if delivery_by_billing_row_names:
				out.service_billed_qty_map = dict(frappe.db.sql("""
					select i.sales_order_item, sum(i.qty)
					from `tabSales Invoice Item` i
					inner join `tabSales Invoice` p on p.name = i.parent
					where p.docstatus = 1 and (p.is_return = 0 or p.reopen_order = 1)
						and i.sales_order_item in %s
					group by i.sales_order_item
				""", [delivery_by_billing_row_names]))

		return out

	def get_billing_status_data(self):
		out = frappe._dict()
		out.billed_qty_map = {}
		out.billed_amount_map = {}
		out.delivery_return_qty_map = {}

		if self.docstatus == 1:
			row_names = [d.name for d in self.items]
			if row_names:
				# Billed By Sales Invoice
				billed_by_sinv = frappe.db.sql("""
					select i.sales_order_item, i.qty, i.amount, p.depreciation_type, p.is_return, p.reopen_order,
						p.customer, p.bill_to
					from `tabSales Invoice Item` i
					inner join `tabSales Invoice` p on p.name = i.parent
					where p.docstatus = 1 and (p.is_return = 0 or p.reopen_order = 1)
						and i.sales_order_item in %s
				""", [row_names], as_dict=1)

				for d in billed_by_sinv:
					bill_to = d.bill_to or d.customer
					so_row = self.getone('items', {'name': d.sales_order_item})
					claim_customer = so_row.claim_customer if so_row else None
					if not d.amount and claim_customer and bill_to != claim_customer:
						continue

					out.billed_amount_map.setdefault(d.sales_order_item, 0)
					out.billed_amount_map[d.sales_order_item] += d.amount

					if d.depreciation_type != 'Depreciation Amount Only':
						out.billed_qty_map.setdefault(d.sales_order_item, 0)
						out.billed_qty_map[d.sales_order_item] += d.qty

				# Returned By Delivery Note
				out.delivery_return_qty_map = dict(frappe.db.sql("""
					select i.sales_order_item, -1 * sum(i.qty)
					from `tabDelivery Note Item` i
					inner join `tabDelivery Note` p on p.name = i.parent
					where p.docstatus = 1 and p.is_return = 1 and p.reopen_order = 0 and i.sales_order_item in %s
					group by i.sales_order_item
				""", [row_names]))

		return out

	def get_purchase_order_qty_map(self):
		purchase_order_qty_map = {}

		if self.docstatus == 1:
			row_names = [d.name for d in self.items]
			if row_names:
				purchase_order_qty_map = dict(frappe.db.sql("""
					select i.sales_order_item, sum(i.qty)
					from `tabPurchase Order Item` i
					inner join `tabPurchase Order` p on p.name = i.parent
					where p.docstatus = 1 and i.sales_order_item in %s
					group by i.sales_order_item
				""", [row_names]))

		return purchase_order_qty_map

	def validate_delivered_qty(self, from_doctype=None, row_names=None):
		self.validate_completed_qty('delivered_qty', 'qty', self.items,
			allowance_type='qty', from_doctype=from_doctype, row_names=row_names)

	def validate_billed_qty(self, from_doctype=None, row_names=None):
		self.validate_completed_qty(['billed_qty', 'returned_qty'], 'qty', self.items,
			allowance_type='billing', from_doctype=from_doctype, row_names=row_names)

		if frappe.get_cached_value("Accounts Settings", None, "validate_over_billing_in_sales_invoice"):
			self.validate_completed_qty('billed_amt', 'amount', self.items,
				allowance_type='billing', from_doctype=from_doctype, row_names=row_names)

	def set_skip_delivery_note(self):
		has_deliverable = False
		for d in self.items:
			if d.item_code and (d.is_stock_item or d.is_fixed_asset):
				has_deliverable = True
				break

		self.skip_delivery_note = cint(not has_deliverable)

	def validate_po(self):
		# validate p.o date v/s delivery date
		if self.po_date and not self.skip_delivery_note:
			for d in self.get("items"):
				if d.delivery_date and getdate(self.po_date) > getdate(d.delivery_date):
					frappe.throw(_("Row #{0}: Expected Delivery Date cannot be before Purchase Order Date")
						.format(d.idx))

		if self.po_no and self.customer and not self.skip_delivery_note:
			so = frappe.db.sql("select name from `tabSales Order` \
				where ifnull(po_no, '') = %s and name != %s and docstatus < 2\
				and customer = %s", (self.po_no, self.name, self.customer))
			if so and so[0][0] and not cint(frappe.get_cached_value("Selling Settings", None, "allow_against_multiple_purchase_orders")):
				frappe.msgprint(_("Warning: Sales Order {0} already exists against Customer's Purchase Order {1}").format(so[0][0], self.po_no))

	def validate_for_items(self):
		for d in self.get('items'):
			# used for production plan
			d.transaction_date = self.transaction_date

			tot_avail_qty = frappe.db.sql("select projected_qty from `tabBin` \
				where item_code = %s and warehouse = %s", (d.item_code, d.warehouse))
			d.projected_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0

	def product_bundle_has_stock_item(self, product_bundle):
		"""Returns true if product bundle has stock item"""
		ret = len(frappe.db.sql("""select i.name from tabItem i, `tabProduct Bundle Item` pbi
			where pbi.parent = %s and pbi.item_code = i.name and i.is_stock_item = 1""", product_bundle))
		return ret

	def validate_delivery_date(self):
		if self.order_type == 'Sales' and not self.skip_delivery_note:
			delivery_date_list = [getdate(d.delivery_date) for d in self.get("items") if d.delivery_date]
			max_delivery_date = max(delivery_date_list) if delivery_date_list else None
			if not self.delivery_date:
				self.delivery_date = max_delivery_date
			if self.delivery_date:
				for d in self.get("items"):
					if not d.delivery_date:
						d.delivery_date = self.delivery_date
					if getdate(self.transaction_date) > getdate(d.delivery_date):
						frappe.msgprint(_("Expected Delivery Date should be after Sales Order Date"),
							indicator='orange', title=_('Warning'))
				if getdate(self.delivery_date) != getdate(max_delivery_date):
					self.delivery_date = max_delivery_date

	def validate_delivery_date_required(self):
		if self.order_type == 'Sales' and not self.skip_delivery_note:
			if not self.delivery_date:
				frappe.throw(_("Please enter Expected Delivery Date"))

	def validate_warehouse(self):
		super(SalesOrder, self).validate_warehouse()

		for d in self.get("items"):
			if (d.item_code and frappe.get_cached_value("Item", d.item_code, "is_stock_item") == 1 or
				(self.has_product_bundle(d.item_code) and self.product_bundle_has_stock_item(d.item_code))) \
				and not d.warehouse and not cint(d.delivered_by_supplier):
				frappe.throw(_("Delivery Warehouse required for Stock Item {0}").format(d.item_code),
					WarehouseRequired)

	def validate_drop_ship(self):
		for d in self.get('items'):
			if d.delivered_by_supplier and not d.supplier:
				frappe.throw(_("Row #{0}: Set Supplier for item {1}").format(d.idx, d.item_code))

	def check_credit_limit(self):
		# if bypass credit limit check is set to true (1) at sales order level,
		# then we need not to check credit limit and vise versa
		if not cint(frappe.db.get_value("Customer Credit Limit",
			{'parent': self.customer, 'parenttype': 'Customer', 'company': self.company},
			"bypass_credit_limit_check")):
			check_credit_limit(self.customer, self.company)

	def check_nextdoc_docstatus(self):
		# Checks Delivery Note
		submit_dn = frappe.db.sql_list("""
			select t1.name
			from `tabDelivery Note` t1,`tabDelivery Note Item` t2
			where t1.name = t2.parent and t2.sales_order = %s and t1.docstatus = 1""", self.name)

		if submit_dn:
			submit_dn = [get_link_to_form("Delivery Note", dn) for dn in submit_dn]
			frappe.throw(_("Delivery Notes {0} must be cancelled before cancelling this Sales Order")
				.format(", ".join(submit_dn)))

		# Checks Sales Invoice
		submit_rv = frappe.db.sql_list("""select t1.name
			from `tabSales Invoice` t1,`tabSales Invoice Item` t2
			where t1.name = t2.parent and t2.sales_order = %s and t1.docstatus = 1""",
			self.name)

		if submit_rv:
			submit_rv = [get_link_to_form("Sales Invoice", si) for si in submit_rv]
			frappe.throw(_("Sales Invoice {0} must be cancelled before cancelling this Sales Order")
				.format(", ".join(submit_rv)))

		#check maintenance schedule
		submit_ms = frappe.db.sql_list("""
			select t1.name
			from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2
			where t2.parent=t1.name and t2.sales_order = %s and t1.docstatus = 1""", self.name)

		if submit_ms:
			submit_ms = [get_link_to_form("Maintenance Schedule", ms) for ms in submit_ms]
			frappe.throw(_("Maintenance Schedule {0} must be cancelled before cancelling this Sales Order")
				.format(", ".join(submit_ms)))

		# check maintenance visit
		submit_mv = frappe.db.sql_list("""
			select t1.name
			from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2
			where t2.parent=t1.name and t2.prevdoc_docname = %s and t1.docstatus = 1""",self.name)

		if submit_mv:
			submit_mv = [get_link_to_form("Maintenance Visit", mv) for mv in submit_mv]
			frappe.throw(_("Maintenance Visit {0} must be cancelled before cancelling this Sales Order")
				.format(", ".join(submit_mv)))

		# check work order
		pro_order = frappe.db.sql_list("""
			select name
			from `tabWork Order`
			where sales_order = %s and docstatus = 1""", self.name)

		if pro_order:
			pro_order = [get_link_to_form("Work Order", po) for po in pro_order]
			frappe.throw(_("Work Order {0} must be cancelled before cancelling this Sales Order")
				.format(", ".join(pro_order)))

	def check_modified_date(self):
		mod_db = frappe.db.get_value("Sales Order", self.name, "modified")
		date_diff = frappe.db.sql("select TIMEDIFF('%s', '%s')" %
			( mod_db, cstr(self.modified)))
		if date_diff and date_diff[0][0]:
			frappe.throw(_("{0} {1} has been modified. Please refresh.").format(self.doctype, self.name))

	def update_reserved_qty(self, so_item_rows=None):
		"""update requested qty (before ordered_qty is updated)"""
		item_wh_list = []
		def _valid_for_reserve(item_code, warehouse):
			if item_code and warehouse and [item_code, warehouse] not in item_wh_list \
				and frappe.get_cached_value("Item", item_code, "is_stock_item"):
					item_wh_list.append([item_code, warehouse])

		for d in self.get("items"):
			if (not so_item_rows or d.name in so_item_rows) and not d.delivered_by_supplier:
				if self.has_product_bundle(d.item_code):
					for p in self.get("packed_items"):
						if p.parent_detail_docname == d.name and p.parent_item == d.item_code:
							_valid_for_reserve(p.item_code, p.warehouse)
				else:
					_valid_for_reserve(d.item_code, d.warehouse)

		for item_code, warehouse in item_wh_list:
			update_bin_qty(item_code, warehouse, {
				"reserved_qty": get_reserved_qty(item_code, warehouse)
			})

	def validate_supplier_after_submit(self):
		"""Check that supplier is the same after submit if PO is already made"""
		exc_list = []

		for item in self.items:
			if item.supplier:
				supplier = frappe.db.get_value("Sales Order Item", {"parent": self.name, "item_code": item.item_code},
					"supplier")
				if item.ordered_qty > 0.0 and item.supplier != supplier:
					exc_list.append(_("Row #{0}: Not allowed to change Supplier as Purchase Order already exists").format(item.idx))

		if exc_list:
			frappe.throw('\n'.join(exc_list))

	def get_work_order_items(self, for_raw_material_request=0):
		'''Returns items with BOM that already do not have a linked work order'''
		items = []
		item_codes = [i.item_code for i in self.items]
		product_bundle_parents = [pb.new_item_code for pb in frappe.get_all("Product Bundle", {"new_item_code": ["in", item_codes]}, ["new_item_code"])]
		default_rm_warehouse = frappe.get_cached_value("Manufacturing Settings", None, "default_rm_warehouse")

		for table in [self.items, self.packed_items]:
			for i in table:
				bom = get_default_bom_item(i.item_code)
				if bom:
					stock_qty = i.qty if i.doctype == 'Packed Item' else i.stock_qty
					if not for_raw_material_request:
						total_work_order_qty = flt(frappe.db.sql('''select sum(qty) from `tabWork Order`
							where production_item=%s and sales_order=%s and sales_order_item = %s and docstatus<2''', (i.item_code, self.name, i.name))[0][0])
						pending_qty = stock_qty - total_work_order_qty
					else:
						pending_qty = stock_qty

					if pending_qty and i.item_code not in product_bundle_parents:
						items.append(dict(
							name= i.name,
							item_code= i.item_code,
							item_name= i.item_name,
							description= i.description,
							bom = bom,
							warehouse = default_rm_warehouse if for_raw_material_request else i.warehouse,
							pending_qty = pending_qty,
							required_qty = pending_qty if for_raw_material_request else 0,
							sales_order_item = i.name
						))
		return items

	def on_recurring(self, reference_doc, auto_repeat_doc):
		def _get_delivery_date(ref_doc_delivery_date, red_doc_transaction_date, transaction_date):
			delivery_date = get_next_schedule_date(ref_doc_delivery_date,
				auto_repeat_doc.frequency, auto_repeat_doc.start_date, cint(auto_repeat_doc.repeat_on_day))

			if delivery_date <= transaction_date:
				delivery_date_diff = frappe.utils.date_diff(ref_doc_delivery_date, red_doc_transaction_date)
				delivery_date = frappe.utils.add_days(transaction_date, delivery_date_diff)

			return delivery_date

		self.set("delivery_date", _get_delivery_date(reference_doc.delivery_date,
			reference_doc.transaction_date, self.transaction_date ))

		for d in self.get("items"):
			reference_delivery_date = frappe.db.get_value("Sales Order Item",
				{"parent": reference_doc.name, "item_code": d.item_code, "idx": d.idx}, "delivery_date")

			d.set("delivery_date", _get_delivery_date(reference_delivery_date,
				reference_doc.transaction_date, self.transaction_date))

	def validate_serial_no_based_delivery(self):
		reserved_items = []
		normal_items = []
		for item in self.items:
			if item.ensure_delivery_based_on_produced_serial_no:
				if item.item_code in normal_items:
					frappe.throw(_("Cannot ensure delivery by Serial No as \
					Item {0} is added with and without Ensure Delivery by \
					Serial No.").format(item.item_code))
				if item.item_code not in reserved_items:
					if not frappe.get_cached_value("Item", item.item_code, "has_serial_no"):
						frappe.throw(_("Item {0} has no Serial No. Only serilialized items \
						can have delivery based on Serial No").format(item.item_code))
					if not frappe.db.exists("BOM", {"item": item.item_code, "is_active": 1}):
						frappe.throw(_("No active BOM found for item {0}. Delivery by \
						Serial No cannot be ensured").format(item.item_code))
				reserved_items.append(item.item_code)
			else:
				normal_items.append(item.item_code)

			if not item.ensure_delivery_based_on_produced_serial_no and \
				item.item_code in reserved_items:
				frappe.throw(_("Cannot ensure delivery by Serial No as \
				Item {0} is added with and without Ensure Delivery by \
				Serial No.").format(item.item_code))


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Orders'),
	})

	return list_context


@frappe.whitelist()
def update_status(status, name):
	so = frappe.get_doc("Sales Order", name)
	so.update_status(status)


@frappe.whitelist()
def close_or_unclose_sales_orders(names, status):
	if not frappe.has_permission("Sales Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	names = json.loads(names)
	for name in names:
		so = frappe.get_doc("Sales Order", name)
		if so.docstatus == 1:
			if status == "Closed":
				if so.status not in ("Cancelled", "Closed") and (so.per_delivered < 100 or so.per_completed < 100):
					so.update_status(status)
			else:
				if so.status == "Closed":
					so.update_status('Draft')
			so.update_blanket_order()

	frappe.local.message_log = []

def get_requested_item_qty(sales_order):
	return frappe._dict(frappe.db.sql("""
		select sales_order_item, sum(stock_qty)
		from `tabMaterial Request Item`
		where docstatus = 1
			and sales_order = %s
		group by sales_order_item
	""", sales_order))


@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
	requested_item_qty_map = get_requested_item_qty(source_name)

	def get_pending_qty(source):
		qty = flt(source.get("qty"))
		return qty - flt(requested_item_qty_map.get(source.name))

	def item_condition(source, source_parent, target_parent):
		if source.name in [d.sales_order_item for d in target_parent.get('items') if d.sales_order_item]:
			return False

		if frappe.db.exists('Product Bundle', source.item_code):
			return False

		return flt(source.stock_qty) > flt(requested_item_qty_map.get(source.name))

	def update_item(source, target, source_parent, target_parent):
		# qty is for packed items, because packed items don't have stock_qty field
		target.qty = get_pending_qty(source)
		target.project = source_parent.project

	def postprocess(source, target):
		target.run_method("set_missing_values")

	doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Material Request",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Packed Item": {
			"doctype": "Material Request Item",
			"field_map": {
				"parent": "sales_order",
				"uom": "uom"
			},
			"postprocess": update_item
		},
		"Sales Order Item": {
			"doctype": "Material Request Item",
			"field_map": {
				"name": "sales_order_item",
				"parent": "sales_order"
			},
			"condition": item_condition,
			"postprocess": update_item
		}
	}, target_doc, postprocess)

	return doc


@frappe.whitelist()
def make_purchase_invoice(supplier, source_name, target_doc=None):
	def set_missing_values(source, target):
		target.supplier = supplier
		target.apply_discount_on = ""
		target.additional_discount_percentage = 0.0
		target.discount_amount = 0.0
		target.update_stock = 1

		target.tax_id, target.tax_cnic, target.tax_strn = frappe.get_value("Supplier", supplier, ['tax_id', 'tax_cnic', 'tax_strn'])

		if target.get('taxes_and_charges'): target.taxes_and_charges = ""
		if target.get('taxes'): target.taxes = []
		default_tax = get_default_taxes_and_charges("Purchase Taxes and Charges Template", company=target.company)
		target.update(default_tax)

		default_price_list = frappe.get_value("Supplier", supplier, "default_price_list")
		if default_price_list:
			target.buying_price_list = default_price_list

		if target.get('payment_terms_template'): target.payment_terms_template = ""
		if target.get('address_display'): target.address_display = ""
		if target.get('shipping_address'): target.shipping_address = ""

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent, target_parent):
		target.discount_percentage = 0
		target.price_list_rate = 0
		target.rate = 0
		target.qty = flt(source.qty) - flt(source.ordered_qty)
		target.stock_qty = (flt(source.qty) - flt(source.ordered_qty)) * flt(source.conversion_factor)
		target.project = source_parent.project

	doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Purchase Invoice",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Purchase Invoice Item",
			"postprocess": update_item
		}
	}, target_doc, set_missing_values)

	return doc


@frappe.whitelist()
def make_project(source_name, target_doc=None):
	def postprocess(source, target):
		project_templates = []
		for d in source.items:
			if d.project_template and d.project_template not in project_templates:
				project_templates.append(d.project_template)

		for project_template in project_templates:
			pt_row = target.append("project_templates")
			pt_row.project_template = project_template
			pt_row.sales_order = source.name

		target.run_method("set_missing_values")

	doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Project",
			"validation": {
				"docstatus": ["=", 1]
			},
			"field_map": {
				"name": "sales_order",
				"delivery_date": "expected_delivery_date",
			},
		},
	}, target_doc, postprocess)

	return doc


@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, warehouse=None, skip_item_mapping=False):
	if not warehouse and frappe.flags.args:
		warehouse = frappe.flags.args.warehouse

	def item_condition(source, source_parent, target_parent):
		if source.name in [d.sales_order_item for d in target_parent.get('items') if d.sales_order_item]:
			return False

		if source.delivered_by_supplier:
			return False

		if not source.is_stock_item and not source.is_fixed_asset:
			return False

		return abs(source.delivered_qty) < abs(source.qty)

	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1

		if not skip_item_mapping:
			update_purchase_receipt_item_details(source, target)
			split_vehicle_items_by_qty(target)
			set_reserved_vehicles_from_so(source, target)

		if warehouse:
			target.set_warehouse = warehouse

		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

		if source.company_address:
			target.update({'company_address': source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Delivery Note", 'company_address', target.company_address))

	def update_item(source, target, source_parent, target_parent):
		target.qty = flt(source.qty) - flt(source.delivered_qty)

	def update_purchase_receipt_item_details(source, target):
		updated_rows = []

		for target_dn_item in target.items:
			updated_rows.append(target_dn_item)

			has_batch_no, has_serial_no = frappe.get_cached_value("Item", target_dn_item.item_code,
				['has_batch_no', 'has_serial_no'], as_dict=1)

			if target_dn_item.sales_order and (has_batch_no or has_serial_no):
				purchase_receipt_items = frappe.db.sql("""
					select pr_item.batch_no, pr_item.serial_no, pr_item.qty
					from `tabPurchase Receipt Item` pr_item
					inner join `tabPurchase Order Item` po_item on po_item.name = pr_item.purchase_order_item
					where pr_item.docstatus = 1 and po_item.sales_order_item = %s
				""", target_dn_item.sales_order_item, as_dict=1)

				delivery_note_items = frappe.db.sql("""
					select dn_item.batch_no, dn_item.serial_no, dn_item.qty
					from `tabDelivery Note Item` dn_item
					inner join `tabSales Order Item` so_item on so_item.name = dn_item.sales_order_item
					where dn_item.docstatus = 1 and dn_item.sales_order_item = %s
				""", target_dn_item.sales_order_item, as_dict=1)

				batch_wise_details = {}

				# Get received batch/serial details
				for pr_item in purchase_receipt_items:
					current_batch = batch_wise_details.setdefault(cstr(pr_item.batch_no), frappe._dict({
						"batch_no": pr_item.batch_no, "serial_nos": [], "remaining_qty": 0
					}))
					current_batch.remaining_qty += flt(pr_item.qty)
					current_batch.serial_nos += cstr(pr_item.serial_no).split("\n")

				# Remove batch/serial nos delivered
				for dn_item in delivery_note_items:
					current_batch = batch_wise_details.get(cstr(dn_item.batch_no))
					if current_batch:
						current_batch.remaining_qty -= flt(dn_item.qty)
						if current_batch.remaining_qty <= 0:
							del batch_wise_details[dn_item.batch_no]
							continue

						serial_nos_to_remove = cstr(dn_item.serial_no).split("\n")
						current_batch.serial_nos = list(filter(lambda d: d and d not in serial_nos_to_remove, current_batch.serial_nos))

				if batch_wise_details:
					batches = list(batch_wise_details.values())
					rows = [target_dn_item]
					for i in range(1, len(batches)):
						new_row = frappe.copy_doc(target_dn_item)
						rows.append(new_row)
						updated_rows.append(new_row)

					for row, batch in zip(rows, batches):
						row.qty = batch.remaining_qty
						row.batch_no = batch.batch_no
						row.serial_no = "\n".join(batch.serial_nos)

		# Replace with updated list
		for i, row in enumerate(updated_rows):
			row.idx = i + 1
		target.items = updated_rows

	mapper = {
		"Sales Order": {
			"doctype": "Delivery Note",
			"validation": {
				"docstatus": ["=", 1]
			},
			"field_map": {
				"remarks": "remarks"
			}
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		}
	}

	if not skip_item_mapping:
		mapper["Sales Order Item"] = {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "sales_order_item",
				"parent": "sales_order",
				"quotation": "quotation",
				"quotation_item": "quotation_item",
			},
			"postprocess": update_item,
			"condition": item_condition,
		}

	target_doc = get_mapped_doc("Sales Order", source_name, mapper, target_doc, set_missing_values)

	return target_doc


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False, only_items=None):
	unbilled_dn_qty_map = get_unbilled_dn_qty_map(source_name)

	if frappe.flags.args and only_items is None:
		only_items = cint(frappe.flags.args.only_items)

	def get_pending_qty(source):
		billable_qty = flt(source.qty) - flt(source.billed_qty) - flt(source.returned_qty)
		unbilled_dn_qty = flt(unbilled_dn_qty_map.get(source.name))
		return max(billable_qty - unbilled_dn_qty, 0)

	def item_condition(source, source_parent, target_parent):
		if source.name in [d.sales_order_item for d in target_parent.get('items') if d.sales_order_item and not d.delivery_note_item]:
			return False

		if cint(target_parent.get('claim_billing')):
			bill_to = target_parent.get('bill_to') or target_parent.get('customer')
			if bill_to:
				if source.claim_customer != bill_to:
					return False
			else:
				if not source.claim_customer:
					return False

		return get_pending_qty(source)

	def update_item(source, target, source_parent, target_parent):
		target.project = source_parent.get('project')
		target.qty = get_pending_qty(source)
		target.depreciation_percentage = None

		if target_parent:
			target_parent.set_rate_zero_for_claim_item(source, target)

	def postprocess(source, target):
		split_vehicle_items_by_qty(target)
		set_reserved_vehicles_from_so(source, target)

		target.ignore_pricing_rule = 1
		target.flags.ignore_permissions = True
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

		# set the redeem loyalty points if provided via shopping cart
		if source.loyalty_points and source.order_type == "Shopping Cart":
			target.redeem_loyalty_points = 1

		if target.get("allocate_advances_automatically"):
			target.set_advances()

	mapping = {
		"Sales Order": {
			"doctype": "Sales Invoice",
			"field_map": {
				"party_account_currency": "party_account_currency",
				"payment_terms_template": "payment_terms_template",
				"remarks": "remarks",
			},
			"field_no_map": [
				"has_stin",
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"name": "sales_order_item",
				"parent": "sales_order",
				"quotation": "quotation",
				"quotation_item": "quotation_item",
			},
			"postprocess": update_item,
			"condition": item_condition,
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		}
	}

	if only_items:
		mapping = {dt: dt_mapping for dt, dt_mapping in mapping.items() if dt == "Sales Order Item"}

	doclist = get_mapped_doc("Sales Order", source_name, mapping, target_doc, postprocess,
		ignore_permissions=ignore_permissions, explicit_child_tables=only_items)

	return doclist


def get_unbilled_dn_qty_map(sales_order):
	unbilled_dn_qty_map = {}

	item_data = frappe.db.sql("""
		select sales_order_item, qty - billed_qty
		from `tabDelivery Note Item`
		where sales_order=%s and docstatus=1
	""", sales_order)

	for sales_order_item, qty in item_data:
		if not unbilled_dn_qty_map.get(sales_order_item):
			unbilled_dn_qty_map[sales_order_item] = 0
		unbilled_dn_qty_map[sales_order_item] += qty

	return unbilled_dn_qty_map


@frappe.whitelist()
def make_maintenance_schedule(source_name, target_doc=None):
	maint_schedule = frappe.db.sql("""select t1.name
		from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2
		where t2.parent=t1.name and t2.sales_order=%s and t1.docstatus=1""", source_name)

	if not maint_schedule:
		doclist = get_mapped_doc("Sales Order", source_name, {
			"Sales Order": {
				"doctype": "Maintenance Schedule",
				"validation": {
					"docstatus": ["=", 1]
				}
			},
			"Sales Order Item": {
				"doctype": "Maintenance Schedule Item",
				"field_map": {
					"parent": "sales_order"
				},
				"add_if_empty": True
			}
		}, target_doc)

		return doclist


@frappe.whitelist()
def make_maintenance_visit(source_name, target_doc=None):
	visit = frappe.db.sql("""select t1.name
		from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2
		where t2.parent=t1.name and t2.prevdoc_docname=%s
		and t1.docstatus=1 and t1.completion_status='Fully Completed'""", source_name)

	if not visit:
		doclist = get_mapped_doc("Sales Order", source_name, {
			"Sales Order": {
				"doctype": "Maintenance Visit",
				"validation": {
					"docstatus": ["=", 1]
				}
			},
			"Sales Order Item": {
				"doctype": "Maintenance Visit Purpose",
				"field_map": {
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype"
				},
				"add_if_empty": True
			}
		}, target_doc)

		return doclist


@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Sales Order", filters)

	data = frappe.db.sql("""
		select
			distinct `tabSales Order`.name, `tabSales Order`.customer_name, `tabSales Order`.status,
			`tabSales Order`.delivery_status, `tabSales Order`.billing_status,
			`tabSales Order Item`.delivery_date
		from
			`tabSales Order`, `tabSales Order Item`
		where `tabSales Order`.name = `tabSales Order Item`.parent
			and `tabSales Order`.skip_delivery_note = 0
			and (ifnull(`tabSales Order Item`.delivery_date, '0000-00-00')!= '0000-00-00') \
			and (`tabSales Order Item`.delivery_date between %(start)s and %(end)s)
			and `tabSales Order`.docstatus < 2
			{conditions}
		""".format(conditions=conditions), {
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})
	return data


@frappe.whitelist()
def make_purchase_order(source_name, for_supplier=None, selected_items=[], target_doc=None):
	if isinstance(selected_items, string_types):
		selected_items = json.loads(selected_items)

	def item_condition(source, source_parent, target_parent):
		return source.ordered_qty < source.qty and source.supplier == supplier and source.item_code in selected_items

	def set_missing_values(source, target):
		target.supplier = supplier
		target.apply_discount_on = ""
		target.additional_discount_percentage = 0.0
		target.discount_amount = 0.0
		target.inter_company_reference = ""

		default_price_list = frappe.get_value("Supplier", supplier, "default_price_list")
		if default_price_list:
			target.buying_price_list = default_price_list

		if any(d.delivered_by_supplier for d in source.items):
			if source.shipping_address_name:
				target.shipping_address = source.shipping_address_name
				target.shipping_address_display = source.shipping_address
			else:
				target.shipping_address = source.customer_address
				target.shipping_address_display = source.address_display

			target.customer_contact_person = source.contact_person
			target.customer_contact_display = source.contact_display
			target.customer_contact_mobile = source.contact_mobile
			target.customer_contact_email = source.contact_email

		else:
			target.customer = ""
			target.customer_name = ""

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent, target_parent):
		target.schedule_date = source.delivery_date
		target.qty = flt(source.qty) - flt(source.ordered_qty)
		target.stock_qty = (flt(source.qty) - flt(source.ordered_qty)) * flt(source.conversion_factor)
		target.project = source_parent.project

	suppliers = []
	if for_supplier:
		suppliers.append(for_supplier)
	else:
		sales_order = frappe.get_doc("Sales Order", source_name)
		for item in sales_order.items:
			if item.supplier and item.supplier not in suppliers:
				suppliers.append(item.supplier)

	if not suppliers:
		frappe.throw(_("Please set a Supplier against the Items to be considered in the Purchase Order."))

	for supplier in suppliers:
		po = frappe.get_all("Purchase Order", filters={"sales_order": source_name, "supplier": supplier, "docstatus": ("<", 2)})
		if len(po) == 0:
			doc = get_mapped_doc("Sales Order", source_name, {
				"Sales Order": {
					"doctype": "Purchase Order",
					"field_no_map": [
						"address_display",
						"contact_display",
						"contact_mobile",
						"contact_email",
						"contact_person",
						"taxes_and_charges",
						"currency",
						"transaction_type"
					],
					"field_map": [
						['remarks', 'remarks']
					],
					"validation": {
						"docstatus": ["=", 1]
					}
				},
				"Sales Order Item": {
					"doctype": "Purchase Order Item",
					"field_map":  [
						["name", "sales_order_item"],
						["parent", "sales_order"],
						["stock_uom", "stock_uom"],
						["uom", "uom"],
						["conversion_factor", "conversion_factor"],
						["delivery_date", "schedule_date"]
					],
					"field_no_map": [
						"rate",
						"price_list_rate",
						"item_tax_template"
					],
					"postprocess": update_item,
					"condition": item_condition,
				}
			}, target_doc, set_missing_values)

			if not for_supplier:
				doc.insert()
		else:
			suppliers = []

	if suppliers:
		if not for_supplier:
			frappe.db.commit()
		return doc
	else:
		frappe.msgprint(_("Purchase Order already created for all Sales Order Items"))


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_supplier(doctype, txt, searchfield, start, page_len, filters):
	supp_master_name = frappe.defaults.get_user_default("supp_master_name")
	if supp_master_name == "Supplier Name":
		fields = ["name", "supplier_group"]
	else:
		fields = ["name", "supplier_name", "supplier_group"]
	fields = ", ".join(fields)

	return frappe.db.sql("""
		select {field} from `tabSupplier`
		where docstatus < 2
			and ({key} like %(txt)s
				or supplier_name like %(txt)s)
			and name in (select supplier from `tabSales Order Item` where parent = %(parent)s)
			and name not in (select supplier from `tabPurchase Order` po inner join `tabPurchase Order Item` poi
				on po.name=poi.parent where po.docstatus<2 and poi.sales_order=%(parent)s)
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, supplier_name), locate(%(_txt)s, supplier_name), 99999),
			name, supplier_name
		limit %(start)s, %(page_len)s
	""".format(**{
			'field': fields,
			'key': frappe.db.escape(searchfield)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'parent': filters.get('parent')
		})


@frappe.whitelist()
def make_work_orders(items, sales_order, company, project=None):
	'''Make Work Orders against the given Sales Order for the given `items`'''
	items = json.loads(items).get('items')
	out = []

	for i in items:
		if not i.get("bom"):
			frappe.throw(_("Please select BOM against item {0}").format(i.get("item_code")))
		if not i.get("pending_qty"):
			frappe.throw(_("Please select Qty against item {0}").format(i.get("item_code")))

		work_order = frappe.get_doc(dict(
			doctype='Work Order',
			production_item=i['item_code'],
			bom_no=i.get('bom'),
			qty=i['pending_qty'],
			company=company,
			sales_order=sales_order,
			sales_order_item=i['sales_order_item'],
			project=project,
			fg_warehouse=i['warehouse'],
			description=i['description']
		)).insert()
		work_order.set_work_order_operations()
		work_order.save()
		out.append(work_order)

	return [p.name for p in out]


def get_default_bom_item(item_code):
	bom = frappe.get_all('BOM', dict(item=item_code, is_active=True),
			order_by='is_default desc')
	bom = bom[0].name if bom else None

	return bom


@frappe.whitelist()
def make_raw_material_request(items, company, sales_order, project=None):
	if not frappe.has_permission("Sales Order", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if isinstance(items, string_types):
		items = frappe._dict(json.loads(items))

	for item in items.get('items'):
		item["include_exploded_items"] = items.get('include_exploded_items')
		item["ignore_existing_ordered_qty"] = items.get('ignore_existing_ordered_qty')
		item["include_raw_materials_from_sales_order"] = items.get('include_raw_materials_from_sales_order')

	items.update({
		'company': company,
		'sales_order': sales_order
	})

	raw_materials = get_items_for_material_requests(items)
	if not raw_materials:
		frappe.msgprint(_("Material Request not created, as quantity for Raw Materials already available."))
		return

	material_request = frappe.new_doc('Material Request')
	material_request.update(dict(
		doctype = 'Material Request',
		transaction_date = nowdate(),
		company = company,
		requested_by = frappe.session.user
	))
	for item in raw_materials:
		item_doc = frappe.get_cached_doc('Item', item.get('item_code'))

		schedule_date = add_days(nowdate(), cint(item_doc.lead_time_days))
		row = material_request.append('items', {
			'item_code': item.get('item_code'),
			'qty': item.get('quantity'),
			'required_qty': flt(item.get('required_qty')),
			'schedule_date': schedule_date,
			'warehouse': item.get('warehouse'),
			'sales_order': sales_order,
			'project': project
		})

	material_request.flags.ignore_permissions = 1
	material_request.run_method("set_missing_values")
	material_request.run_method("calculate_totals")
	return material_request


@frappe.whitelist()
def make_inter_company_purchase_order(source_name, target_doc=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_transaction
	return make_inter_company_transaction("Sales Order", source_name, target_doc)


@frappe.whitelist()
def create_pick_list(source_name, target_doc=None):
	def update_item_quantity(source, target, source_parent, target_parent):
		target.qty = flt(source.qty) - flt(source.delivered_qty)
		target.stock_qty = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.conversion_factor)

	doc = get_mapped_doc('Sales Order', source_name, {
		'Sales Order': {
			'doctype': 'Pick List',
			'validation': {
				'docstatus': ['=', 1]
			}
		},
		'Sales Order Item': {
			'doctype': 'Pick List Item',
			'field_map': {
				'parent': 'sales_order',
				'name': 'sales_order_item'
			},
			'postprocess': update_item_quantity,
			'condition': lambda doc, source, target: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
		},
	}, target_doc)

	doc.purpose = 'Delivery'

	doc.set_item_locations()

	return doc


def update_produced_qty_in_so_item(sales_order, sales_order_item):
	# for multiple work orders against same sales order item
	linked_wo_with_so_item = frappe.db.get_all('Work Order', ['produced_qty'], {
		'sales_order_item': sales_order_item,
		'sales_order': sales_order,
		'docstatus': 1
	})

	total_produced_qty = 0
	for wo in linked_wo_with_so_item:
		total_produced_qty += flt(wo.get('produced_qty'))

	if not total_produced_qty and frappe.flags.in_patch: return

	frappe.db.set_value('Sales Order Item', sales_order_item, 'produced_qty', total_produced_qty)
