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


	def update_bin(self, is_submit, is_stopped = 0):
		from erpnext.stock.utils import update_bin
		pc_obj = frappe.get_doc('Purchase Common')
		for d in self.get('po_details'):
			#1. Check if is_stock_item == 'Yes'
			if frappe.db.get_value("Item", d.item_code, "is_stock_item") == "Yes":
				# this happens when item is changed from non-stock to stock item
				if not d.warehouse:
					continue

				ind_qty, po_qty = 0, flt(d.qty) * flt(d.conversion_factor)
				if is_stopped:
					po_qty = flt(d.qty) > flt(d.received_qty) and \
						flt( flt(flt(d.qty) - flt(d.received_qty))*flt(d.conversion_factor)) or 0

				# No updates in Material Request on Stop / Unstop
				if cstr(d.prevdoc_doctype) == 'Material Request' and not is_stopped:
					# get qty and pending_qty of prevdoc
					curr_ref_qty = pc_obj.get_qty(d.doctype, 'prevdoc_detail_docname',
					 	d.prevdoc_detail_docname, 'Material Request Item',
						'Material Request - Purchase Order', self.name)
					max_qty, qty, curr_qty = flt(curr_ref_qty.split('~~~')[1]), \
					 	flt(curr_ref_qty.split('~~~')[0]), 0

					if flt(qty) + flt(po_qty) > flt(max_qty):
						curr_qty = flt(max_qty) - flt(qty)
						# special case as there is no restriction
						# for Material Request - Purchase Order
						curr_qty = curr_qty > 0 and curr_qty or 0
					else:
						curr_qty = flt(po_qty)

					ind_qty = -flt(curr_qty)

				# Update ordered_qty and indented_qty in bin
				args = {
					"item_code": d.item_code,
					"warehouse": d.warehouse,
					"ordered_qty": (is_submit and 1 or -1) * flt(po_qty),
					"indented_qty": (is_submit and 1 or -1) * flt(ind_qty),
					"posting_date": self.transaction_date
				}
				update_bin(args)

	def check_modified_date(self):
		mod_db = frappe.db.sql("select modified from `tabPurchase Order` where name = %s",
			self.name)
		date_diff = frappe.db.sql("select TIMEDIFF('%s', '%s')" % ( mod_db[0][0],cstr(self.modified)))

		if date_diff and date_diff[0][0]:
			msgprint(_("{0} {1} has been modified. Please refresh.").format(self.doctype, self.name),
				raise_exception=True)

	def update_status(self, status):
		self.check_modified_date()
		# step 1:=> Set Status
		frappe.db.set(self,'status',cstr(status))

		# step 2:=> Update Bin
		self.update_bin(is_submit = (status == 'Submitted') and 1 or 0, is_stopped = 1)

		# step 3:=> Acknowledge user
		msgprint(_("Status of {0} {1} is now {2}").format(self.doctype, self.name, status))

	def on_submit(self):
		purchase_controller = frappe.get_doc("Purchase Common")

		self.update_prevdoc_status()
		self.update_bin(is_submit = 1, is_stopped = 0)

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
		self.update_bin( is_submit = 0, is_stopped = 0)
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
	def update_item(obj, target, source_parent):
		target.amount = flt(obj.amount) - flt(obj.billed_amt)
		target.base_amount = target.amount * flt(source_parent.conversion_rate)
		target.qty = target.amount / flt(obj.rate) if flt(obj.rate) else flt(obj.qty)

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
	}, target_doc, set_missing_values)

	return doc
