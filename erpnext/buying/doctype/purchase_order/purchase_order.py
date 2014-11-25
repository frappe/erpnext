# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, flt
from frappe import msgprint, _, throw
from frappe.model.mapper import get_mapped_doc
from erpnext.controllers.buying_controller import BuyingController

form_grid_templates = {
	"po_details": "templates/form_grid/item_grid.html"
}

class PurchaseOrder(BuyingController):
	tname = 'Purchase Order Item'
	fname = 'po_details'

	def __init__(self, arg1, arg2=None):
		super(PurchaseOrder, self).__init__(arg1, arg2)
		self.status_updater = [{
			'source_dt': 'Purchase Order Item',
			'target_dt': 'Material Request Item',
			'join_field': 'prevdoc_detail_docname',
			'target_field': 'ordered_qty',
			'target_parent_dt': 'Material Request',
			'target_parent_field': 'per_ordered',
			'target_ref_field': 'qty',
			'source_field': 'qty',
			'percent_join_field': 'prevdoc_docname',
			'overflow_type': 'order'
		}]

	def validate(self):
		super(PurchaseOrder, self).validate()

		if not self.status:
			self.status = "Draft"

		from erpnext.utilities import validate_status
		validate_status(self.status, ["Draft", "Submitted", "Stopped",
			"Cancelled"])

		pc_obj = frappe.get_doc('Purchase Common')
		pc_obj.validate_for_items(self)
		self.check_for_stopped_status(pc_obj)

		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", ["qty", "required_qty"])

		self.validate_with_previous_doc()
		self.validate_for_subcontracting()
		self.validate_minimum_order_qty()
		self.create_raw_materials_supplied("po_raw_material_details")

	def validate_with_previous_doc(self):
		super(PurchaseOrder, self).validate_with_previous_doc(self.tname, {
			"Supplier Quotation": {
				"ref_dn_field": "supplier_quotation",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Supplier Quotation Item": {
				"ref_dn_field": "supplier_quotation_item",
				"compare_fields": [["rate", "="], ["project_name", "="], ["item_code", "="],
					["uom", "="]],
				"is_child_table": True
			}
		})

	def validate_minimum_order_qty(self):
		itemwise_min_order_qty = frappe._dict(frappe.db.sql("select name, min_order_qty from tabItem"))

		itemwise_qty = frappe._dict()
		for d in self.get("po_details"):
			itemwise_qty.setdefault(d.item_code, 0)
			itemwise_qty[d.item_code] += flt(d.stock_qty)

		for item_code, qty in itemwise_qty.items():
			if flt(qty) < flt(itemwise_min_order_qty.get(item_code)):
				frappe.throw(_("Item #{0}: Ordered qty can not less than item's minimum order qty (defined in item master).").format(item_code))

	def get_schedule_dates(self):
		for d in self.get('po_details'):
			if d.prevdoc_detail_docname and not d.schedule_date:
				d.schedule_date = frappe.db.get_value("Material Request Item",
						d.prevdoc_detail_docname, "schedule_date")

	def get_last_purchase_rate(self):
		frappe.get_doc('Purchase Common').get_last_purchase_rate(self)

	# Check for Stopped status
	def check_for_stopped_status(self, pc_obj):
		check_list =[]
		for d in self.get('po_details'):
			if d.meta.get_field('prevdoc_docname') and d.prevdoc_docname and d.prevdoc_docname not in check_list:
				check_list.append(d.prevdoc_docname)
				pc_obj.check_for_stopped_status( d.prevdoc_doctype, d.prevdoc_docname)

	def update_requested_qty(self):
		material_request_map = {}
		for d in self.get("po_details"):
			if d.prevdoc_doctype and d.prevdoc_doctype == "Material Request" and d.prevdoc_detail_docname:
				material_request_map.setdefault(d.prevdoc_docname, []).append(d.prevdoc_detail_docname)

		for mr, mr_item_rows in material_request_map.items():
			if mr and mr_item_rows:
				mr_obj = frappe.get_doc("Material Request", mr)

				if mr_obj.status in ["Stopped", "Cancelled"]:
					frappe.throw(_("Material Request {0} is cancelled or stopped").format(mr), frappe.InvalidStatusError)

				mr_obj.update_requested_qty(mr_item_rows)

	def update_ordered_qty(self, po_item_rows=None):
		"""update requested qty (before ordered_qty is updated)"""
		from erpnext.stock.utils import get_bin

		def _update_ordered_qty(item_code, warehouse):
			ordered_qty = frappe.db.sql("""
				select sum((po_item.qty - ifnull(po_item.received_qty, 0))*po_item.conversion_factor)
				from `tabPurchase Order Item` po_item, `tabPurchase Order` po
				where po_item.item_code=%s and po_item.warehouse=%s
				and po_item.qty > ifnull(po_item.received_qty, 0) and po_item.parent=po.name
				and po.status!='Stopped' and po.docstatus=1""", (item_code, warehouse))

			bin_doc = get_bin(item_code, warehouse)
			bin_doc.ordered_qty = flt(ordered_qty[0][0]) if ordered_qty else 0
			bin_doc.save()

		item_wh_list = []
		for d in self.get("po_details"):
			if (not po_item_rows or d.name in po_item_rows) and [d.item_code, d.warehouse] not in item_wh_list \
					and frappe.db.get_value("Item", d.item_code, "is_stock_item") == "Yes" and d.warehouse:
				item_wh_list.append([d.item_code, d.warehouse])

		for item_code, warehouse in item_wh_list:
			_update_ordered_qty(item_code, warehouse)

	def check_modified_date(self):
		mod_db = frappe.db.sql("select modified from `tabPurchase Order` where name = %s",
			self.name)
		date_diff = frappe.db.sql("select TIMEDIFF('%s', '%s')" % ( mod_db[0][0],cstr(self.modified)))

		if date_diff and date_diff[0][0]:
			msgprint(_("{0} {1} has been modified. Please refresh.").format(self.doctype, self.name),
				raise_exception=True)

	def update_status(self, status):
		self.check_modified_date()
		frappe.db.set(self,'status',cstr(status))

		self.update_requested_qty()
		self.update_ordered_qty()

		msgprint(_("Status of {0} {1} is now {2}").format(self.doctype, self.name, status))

	def on_submit(self):
		super(PurchaseOrder, self).on_submit()

		purchase_controller = frappe.get_doc("Purchase Common")

		self.update_prevdoc_status()
		self.update_requested_qty()
		self.update_ordered_qty()

		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
			self.company, self.grand_total)

		purchase_controller.update_last_purchase_rate(self, is_submit = 1)

		frappe.db.set(self,'status','Submitted')

	def on_cancel(self):
		pc_obj = frappe.get_doc('Purchase Common')
		self.check_for_stopped_status(pc_obj)

		# Check if Purchase Receipt has been submitted against current Purchase Order
		pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Receipt', docname = self.name, detail_doctype = 'Purchase Receipt Item')

		# Check if Purchase Invoice has been submitted against current Purchase Order
		submitted = frappe.db.sql_list("""select t1.name
			from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2
			where t1.name = t2.parent and t2.purchase_order = %s and t1.docstatus = 1""",
			self.name)
		if submitted:
			throw(_("Purchase Invoice {0} is already submitted").format(", ".join(submitted)))

		frappe.db.set(self,'status','Cancelled')

		self.update_prevdoc_status()

		# Must be called after updating ordered qty in Material Request
		self.update_requested_qty()
		self.update_ordered_qty()

		pc_obj.update_last_purchase_rate(self, is_submit = 0)

	def on_update(self):
		pass

def set_missing_values(source, target):
	target.ignore_pricing_rule = 1
	target.run_method("set_missing_values")
	target.run_method("calculate_taxes_and_totals")

@frappe.whitelist()
def make_purchase_receipt(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.received_qty)
		target.stock_qty = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.conversion_factor)
		target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate)
		target.base_amount = (flt(obj.qty) - flt(obj.received_qty)) * \
			flt(obj.rate) * flt(source_parent.conversion_rate)

	doc = get_mapped_doc("Purchase Order", source_name,	{
		"Purchase Order": {
			"doctype": "Purchase Receipt",
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"Purchase Order Item": {
			"doctype": "Purchase Receipt Item",
			"field_map": {
				"name": "prevdoc_detail_docname",
				"parent": "prevdoc_docname",
				"parenttype": "prevdoc_doctype",
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.received_qty < doc.qty
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return doc

@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
	def postprocess(source, target):
		set_missing_values(source, target)
		#Get the advance paid Journal Vouchers in Purchase Invoice Advance
		target.get_advances()

	def update_item(obj, target, source_parent):
		target.amount = flt(obj.amount) - flt(obj.billed_amt)
		target.base_amount = target.amount * flt(source_parent.conversion_rate)
		target.qty = target.amount / flt(obj.rate) if (flt(obj.rate) and flt(obj.billed_amt)) else flt(obj.qty)

	doc = get_mapped_doc("Purchase Order", source_name,	{
		"Purchase Order": {
			"doctype": "Purchase Invoice",
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"Purchase Order Item": {
			"doctype": "Purchase Invoice Item",
			"field_map": {
				"name": "po_detail",
				"parent": "purchase_order",
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.base_amount==0 or doc.billed_amt < doc.amount
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
			"add_if_empty": True
		}
	}, target_doc, postprocess)

	return doc
