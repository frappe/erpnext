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
from frappe.desk.doctype.auto_repeat.auto_repeat import get_next_schedule_date
from erpnext.selling.doctype.customer.customer import check_credit_limit
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.manufacturing.doctype.production_plan.production_plan import get_items_for_material_requests

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class WarehouseRequired(frappe.ValidationError): pass

class SalesOrder(SellingController):
	def __init__(self, *args, **kwargs):
		super(SalesOrder, self).__init__(*args, **kwargs)

	def validate(self):
		super(SalesOrder, self).validate()
		self.validate_order_type()
		self.validate_delivery_date()
		self.validate_proj_cust()
		self.validate_po()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_for_items()
		self.validate_warehouse()
		self.validate_drop_ship()
		self.validate_serial_no_based_delivery()

		from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
		make_packing_list(self)

		self.validate_with_previous_doc()
		self.set_status()

		if not self.billing_status: self.billing_status = 'Not Billed'
		if not self.delivery_status: self.delivery_status = 'Not Delivered'

	def validate_po(self):
		# validate p.o date v/s delivery date
		if self.po_date:
			for d in self.get("items"):
				if d.delivery_date and getdate(self.po_date) > getdate(d.delivery_date):
					frappe.throw(_("Row #{0}: Expected Delivery Date cannot be before Purchase Order Date")
						.format(d.idx))

		if self.po_no and self.customer:
			so = frappe.db.sql("select name from `tabSales Order` \
				where ifnull(po_no, '') = %s and name != %s and docstatus < 2\
				and customer = %s", (self.po_no, self.name, self.customer))
			if so and so[0][0] and not cint(frappe.db.get_single_value("Selling Settings",
				"allow_against_multiple_purchase_orders")):
				frappe.msgprint(_("Warning: Sales Order {0} already exists against Customer's Purchase Order {1}").format(so[0][0], self.po_no))

	def validate_for_items(self):
		check_list = []
		for d in self.get('items'):
			check_list.append(cstr(d.item_code))

			# used for production plan
			d.transaction_date = self.transaction_date

			tot_avail_qty = frappe.db.sql("select projected_qty from `tabBin` \
				where item_code = %s and warehouse = %s", (d.item_code, d.warehouse))
			d.projected_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0

		# check for same entry multiple times
		unique_chk_list = set(check_list)
		if len(unique_chk_list) != len(check_list) and \
			not cint(frappe.db.get_single_value("Selling Settings", "allow_multiple_items")):
			frappe.msgprint(_("Same item has been entered multiple times"),
				title=_("Warning"), indicator='orange')

	def product_bundle_has_stock_item(self, product_bundle):
		"""Returns true if product bundle has stock item"""
		ret = len(frappe.db.sql("""select i.name from tabItem i, `tabProduct Bundle Item` pbi
			where pbi.parent = %s and pbi.item_code = i.name and i.is_stock_item = 1""", product_bundle))
		return ret

	def validate_sales_mntc_quotation(self):
		for d in self.get('items'):
			if d.prevdoc_docname:
				res = frappe.db.sql("select name from `tabQuotation` where name=%s and order_type = %s",
					(d.prevdoc_docname, self.order_type))
				if not res:
					frappe.msgprint(_("Quotation {0} not of type {1}")
						.format(d.prevdoc_docname, self.order_type))

	def validate_order_type(self):
		super(SalesOrder, self).validate_order_type()

	def validate_delivery_date(self):
		if self.order_type == 'Sales':
			delivery_date_list = [d.delivery_date for d in self.get("items") if d.delivery_date]
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
			else:
				frappe.throw(_("Please enter Delivery Date"))

		self.validate_sales_mntc_quotation()

	def validate_proj_cust(self):
		if self.project and self.customer_name:
			res = frappe.db.sql("""select name from `tabProject` where name = %s
				and (customer = %s or ifnull(customer,'')='')""",
					(self.project, self.customer))
			if not res:
				frappe.throw(_("Customer {0} does not belong to project {1}").format(self.customer, self.project))

	def validate_warehouse(self):
		super(SalesOrder, self).validate_warehouse()

		for d in self.get("items"):
			if (frappe.get_cached_value("Item", d.item_code, "is_stock_item") == 1 or
				(self.has_product_bundle(d.item_code) and self.product_bundle_has_stock_item(d.item_code))) \
				and not d.warehouse and not cint(d.delivered_by_supplier):
				frappe.throw(_("Delivery warehouse required for stock item {0}").format(d.item_code),
					WarehouseRequired)

	def validate_with_previous_doc(self):
		super(SalesOrder, self).validate_with_previous_doc({
			"Quotation": {
				"ref_dn_field": "prevdoc_docname",
				"compare_fields": [["company", "="]]
			}
		})


	def update_enquiry_status(self, prevdoc, flag):
		enq = frappe.db.sql("select t2.prevdoc_docname from `tabQuotation` t1, `tabQuotation Item` t2 where t2.parent = t1.name and t1.name=%s", prevdoc)
		if enq:
			frappe.db.sql("update `tabOpportunity` set status = %s where name=%s",(flag,enq[0][0]))

	def update_prevdoc_status(self, flag):
		for quotation in list(set([d.prevdoc_docname for d in self.get("items")])):
			if quotation:
				doc = frappe.get_doc("Quotation", quotation)
				if doc.docstatus==2:
					frappe.throw(_("Quotation {0} is cancelled").format(quotation))

				doc.set_status(update=True)
				doc.update_opportunity()

	def validate_drop_ship(self):
		for d in self.get('items'):
			if d.delivered_by_supplier and not d.supplier:
				frappe.throw(_("Row #{0}: Set Supplier for item {1}").format(d.idx, d.item_code))

	def on_submit(self):
		self.check_credit_limit()
		self.update_reserved_qty()

		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype, self.company, self.base_grand_total, self)
		self.update_project()
		self.update_prevdoc_status('submit')

		self.update_blanket_order()

	def on_cancel(self):
		# Cannot cancel closed SO
		if self.status == 'Closed':
			frappe.throw(_("Closed order cannot be cancelled. Unclose to cancel."))

		self.check_nextdoc_docstatus()
		self.update_reserved_qty()
		self.update_project()
		self.update_prevdoc_status('cancel')

		frappe.db.set(self, 'status', 'Cancelled')

		self.update_blanket_order()

	def update_project(self):
		if frappe.db.get_single_value('Selling Settings', 'sales_update_frequency') != "Each Transaction":
			return

		if self.project:
			project = frappe.get_doc("Project", self.project)
			project.flags.dont_sync_tasks = True
			project.update_sales_amount()
			project.save()

	def check_credit_limit(self):
		# if bypass credit limit check is set to true (1) at sales order level,
		# then we need not to check credit limit and vise versa
		if not cint(frappe.get_cached_value("Customer", self.customer, "bypass_credit_limit_check_at_sales_order")):
			check_credit_limit(self.customer, self.company)

	def check_nextdoc_docstatus(self):
		# Checks Delivery Note
		submit_dn = frappe.db.sql_list("""
			select t1.name
			from `tabDelivery Note` t1,`tabDelivery Note Item` t2
			where t1.name = t2.parent and t2.against_sales_order = %s and t1.docstatus = 1""", self.name)

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

	def update_status(self, status):
		self.check_modified_date()
		self.set_status(update=True, status=status)
		self.update_reserved_qty()
		self.notify_update()
		clear_doctype_notifications(self)

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

	def on_update(self):
		pass

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
				supplier = frappe.db.get_value("Sales Order Item", {"parent": self.name, "item_code": item.item_code},
					"supplier")
				if item.ordered_qty > 0.0 and item.supplier != supplier:
					exc_list.append(_("Row #{0}: Not allowed to change Supplier as Purchase Order already exists").format(item.idx))

		if exc_list:
			frappe.throw('\n'.join(exc_list))

	def update_delivery_status(self):
		"""Update delivery status from Purchase Order for drop shipping"""
		tot_qty, delivered_qty = 0.0, 0.0

		for item in self.items:
			if item.delivered_by_supplier:
				item_delivered_qty  = frappe.db.sql("""select sum(qty)
					from `tabPurchase Order Item` poi, `tabPurchase Order` po
					where poi.sales_order_item = %s
						and poi.item_code = %s
						and poi.parent = po.name
						and po.docstatus = 1
						and po.status = 'Delivered'""", (item.name, item.item_code))

				item_delivered_qty = item_delivered_qty[0][0] if item_delivered_qty else 0
				item.db_set("delivered_qty", flt(item_delivered_qty), update_modified=False)

			delivered_qty += item.delivered_qty
			tot_qty += item.qty

		if tot_qty != 0:
			self.db_set("per_delivered", flt(delivered_qty/tot_qty) * 100,
				update_modified=False)


	def set_indicator(self):
		"""Set indicator for portal"""
		if self.per_billed < 100 and self.per_delivered < 100:
			self.indicator_color = "orange"
			self.indicator_title = _("Not Paid and Not Delivered")

		elif self.per_billed == 100 and self.per_delivered < 100:
			self.indicator_color = "orange"
			self.indicator_title = _("Paid and Not Delivered")

		else:
			self.indicator_color = "green"
			self.indicator_title = _("Paid")

	def get_work_order_items(self, for_raw_material_request=0):
		'''Returns items with BOM that already do not have a linked work order'''
		items = []
		for table in [self.items, self.packed_items]:
			for i in table:
				bom = get_default_bom_item(i.item_code)
				stock_qty = i.qty if i.doctype == 'Packed Item' else i.stock_qty
				if not for_raw_material_request:
					total_work_order_qty = flt(frappe.db.sql('''select sum(qty) from `tabWork Order`
						where production_item=%s and sales_order=%s and sales_order_item = %s and docstatus<2''', (i.item_code, self.name, i.name))[0][0])
					pending_qty = stock_qty - total_work_order_qty
				else:
					pending_qty = stock_qty

				if pending_qty:
					if bom:
						items.append(dict(
							name= i.name,
							item_code= i.item_code,
							bom = bom,
							warehouse = i.warehouse,
							pending_qty = pending_qty,
							required_qty = pending_qty if for_raw_material_request else 0,
							sales_order_item = i.name
						))
					else:
						items.append(dict(
							name= i.name,
							item_code= i.item_code,
							bom = '',
							warehouse = i.warehouse,
							pending_qty = pending_qty,
							required_qty = pending_qty if for_raw_material_request else 0,
							sales_order_item = i.name
						))
		return items

	def on_recurring(self, reference_doc, auto_repeat_doc):

		def _get_delivery_date(ref_doc_delivery_date, red_doc_transaction_date, transaction_date):
			delivery_date = get_next_schedule_date(ref_doc_delivery_date,
				auto_repeat_doc.frequency, cint(auto_repeat_doc.repeat_on_day))

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
def close_or_unclose_sales_orders(names, status):
	if not frappe.has_permission("Sales Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	names = json.loads(names)
	for name in names:
		so = frappe.get_doc("Sales Order", name)
		if so.docstatus == 1:
			if status == "Closed":
				if so.status not in ("Cancelled", "Closed") and (so.per_delivered < 100 or so.per_billed < 100):
					so.update_status(status)
			else:
				if so.status == "Closed":
					so.update_status('Draft')
			so.update_blanket_order()

	frappe.local.message_log = []

@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
	def postprocess(source, doc):
		doc.material_request_type = "Purchase"

	def update_item(source, target, source_parent):
		target.project = source_parent.project

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
				"stock_uom": "uom"
			},
			"postprocess": update_item
		},
		"Sales Order Item": {
			"doctype": "Material Request Item",
			"field_map": {
				"name": "sales_order_item",
				"parent": "sales_order",
				"stock_uom": "uom",
				"stock_qty": "qty"
			},
			"condition": lambda doc: not frappe.db.exists('Product Bundle', doc.item_code),
			"postprocess": update_item
		}
	}, target_doc, postprocess)

	return doc

@frappe.whitelist()
def make_project(source_name, target_doc=None):
	def postprocess(source, doc):
		doc.project_type = "External"
		doc.project_name = source.name

	doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Project",
			"validation": {
				"docstatus": ["=", 1]
			},
			"field_map":{
				"name" : "sales_order",
				"base_grand_total" : "estimated_costing",
			}
		},
		"Sales Order Item": {
			"doctype": "Project Task",
			"field_map": {
				"description": "title",
			},
		}
	}, target_doc, postprocess)

	return doc

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

		# set company address
		target.update(get_company_address(target.company))
		if target.company_address:
			target.update(get_fetch_values("Delivery Note", 'company_address', target.company_address))

	def update_item(source, target, source_parent):
		target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = flt(source.qty) - flt(source.delivered_qty)

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)

		if item:
			target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center") \
				or item.get("selling_cost_center") \
				or item_group.get("selling_cost_center")

	target_doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Delivery Note",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
			},
			"postprocess": update_item,
			"condition": lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return target_doc

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
	def postprocess(source, target):
		set_missing_values(source, target)
		#Get the advance paid Journal Entries in Sales Invoice Advance
		target.set_advances()

	def set_missing_values(source, target):
		target.is_pos = 0
		target.ignore_pricing_rule = 1
		target.flags.ignore_permissions = True
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

		# set company address
		target.update(get_company_address(target.company))
		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))

		# set the redeem loyalty points if provided via shopping cart
		if source.loyalty_points and source.order_type == "Shopping Cart":
			target.redeem_loyalty_points = 1

	def update_item(source, target, source_parent):
		target.amount = flt(source.amount) - flt(source.billed_amt)
		target.base_amount = target.amount * flt(source_parent.conversion_rate)
		target.qty = target.amount / flt(source.rate) if (source.rate and source.billed_amt) else source.qty - source.returned_qty

		if source_parent.project:
			target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center")
		if not target.cost_center and target.item_code:
			item = get_item_defaults(target.item_code, source_parent.company)
			item_group = get_item_group_defaults(target.item_code, source_parent.company)
			target.cost_center = item.get("selling_cost_center") \
				or item_group.get("selling_cost_center")

	doclist = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Sales Invoice",
			"field_map": {
				"party_account_currency": "party_account_currency",
				"payment_terms_template": "payment_terms_template"
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"name": "so_detail",
				"parent": "sales_order",
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.qty and (doc.base_amount==0 or abs(doc.billed_amt) < abs(doc.amount))
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		}
	}, target_doc, postprocess, ignore_permissions=ignore_permissions)

	return doclist

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
def make_purchase_order_for_drop_shipment(source_name, for_supplier=None, target_doc=None):
	def set_missing_values(source, target):
		target.supplier = supplier
		target.apply_discount_on = ""
		target.additional_discount_percentage = 0.0
		target.discount_amount = 0.0

		default_price_list = frappe.get_value("Supplier", supplier, "default_price_list")
		if default_price_list:
			target.buying_price_list = default_price_list

		if any( item.delivered_by_supplier==1 for item in source.items):
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

	def update_item(source, target, source_parent):
		target.schedule_date = source.delivery_date
		target.qty = flt(source.qty) - flt(source.ordered_qty)
		target.stock_qty = (flt(source.qty) - flt(source.ordered_qty)) * flt(source.conversion_factor)
		target.project = source_parent.project

	suppliers =[]
	if for_supplier:
		suppliers.append(for_supplier)
	else:
		sales_order = frappe.get_doc("Sales Order", source_name)
		for item in sales_order.items:
			if item.supplier and item.supplier not in suppliers:
				suppliers.append(item.supplier)
	for supplier in suppliers:
		po =frappe.get_list("Purchase Order", filters={"sales_order":source_name, "supplier":supplier, "docstatus": ("<", "2")})
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
						"taxes_and_charges"
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
						"price_list_rate"
					],
					"postprocess": update_item,
					"condition": lambda doc: doc.ordered_qty < doc.qty and doc.supplier == supplier
				}
			}, target_doc, set_missing_values)
			if not for_supplier:
				doc.insert()
		else:
			suppliers =[]
	if suppliers:
		if not for_supplier:
			frappe.db.commit()
		return doc
	else:
		frappe.msgprint(_("PO already created for all sales order items"))


@frappe.whitelist()
def get_supplier(doctype, txt, searchfield, start, page_len, filters):
	supp_master_name = frappe.defaults.get_user_default("supp_master_name")
	if supp_master_name == "Supplier Name":
		fields = ["name", "supplier_group"]
	else:
		fields = ["name", "supplier_name", "supplier_group"]
	fields = ", ".join(fields)

	return frappe.db.sql("""select {field} from `tabSupplier`
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
		limit %(start)s, %(page_len)s """.format(**{
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
			fg_warehouse=i['warehouse']
		)).insert()
		work_order.set_work_order_operations()
		work_order.save()
		out.append(work_order)

	return [p.name for p in out]

@frappe.whitelist()
def update_status(status, name):
	so = frappe.get_doc("Sales Order", name)
	so.update_status(status)

def get_default_bom_item(item_code):
	bom = frappe.get_all('BOM', dict(item=item_code, is_active=True),
			order_by='is_default desc')
	bom = bom[0].name if bom else None

	return bom

@frappe.whitelist()
def make_raw_material_request(items, company, sales_order, project=None):
	if not frappe.has_permission("Sales Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if isinstance(items, string_types):
		items = frappe._dict(json.loads(items))

	for item in items.get('items'):
		item["include_exploded_items"] = items.get('include_exploded_items')
		item["ignore_existing_ordered_qty"] = items.get('ignore_existing_ordered_qty')
		item["include_raw_materials_from_sales_order"] = items.get('include_raw_materials_from_sales_order')

	raw_materials = get_items_for_material_requests(items, sales_order, company)
	if not raw_materials:
		frappe.msgprint(_("Material Request not created, as quantity for Raw Materials already available."))
		return

	material_request = frappe.new_doc('Material Request')
	material_request.update(dict(
		doctype = 'Material Request',
		transaction_date = nowdate(),
		company = company,
		requested_by = frappe.session.user,
		material_request_type = 'Purchase'
	))
	for item in raw_materials:
		item_doc = frappe.get_cached_doc('Item', item.get('item_code'))
		schedule_date = add_days(nowdate(), cint(item_doc.lead_time_days))
		material_request.append('items', {
		'item_code': item.get('item_code'),
		'qty': item.get('quantity'),
		'schedule_date': schedule_date,
		'warehouse': item.get('warehouse'),
		'sales_order': sales_order,
		'project': project
		})
	material_request.insert()
	material_request.flags.ignore_permissions = 1
	material_request.run_method("set_missing_values")
	material_request.submit()
	return material_request