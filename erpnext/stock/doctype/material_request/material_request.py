# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cstr, flt
from frappe import _
from frappe.model.mapper import get_mapped_doc

from erpnext.controllers.buying_controller import BuyingController

form_grid_templates = {
	"indent_details": "templates/form_grid/material_request_grid.html"
}

class MaterialRequest(BuyingController):
	tname = 'Material Request Item'
	fname = 'indent_details'

	def check_if_already_pulled(self):
		pass#if self.[d.sales_order_no for d in self.get('indent_details')]

	def validate_qty_against_so(self):
		so_items = {} # Format --> {'SO/00001': {'Item/001': 120, 'Item/002': 24}}
		for d in self.get('indent_details'):
			if d.sales_order_no:
				if not so_items.has_key(d.sales_order_no):
					so_items[d.sales_order_no] = {d.item_code: flt(d.qty)}
				else:
					if not so_items[d.sales_order_no].has_key(d.item_code):
						so_items[d.sales_order_no][d.item_code] = flt(d.qty)
					else:
						so_items[d.sales_order_no][d.item_code] += flt(d.qty)

		for so_no in so_items.keys():
			for item in so_items[so_no].keys():
				already_indented = frappe.db.sql("""select sum(ifnull(qty, 0))
					from `tabMaterial Request Item`
					where item_code = %s and sales_order_no = %s and
					docstatus = 1 and parent != %s""", (item, so_no, self.name))
				already_indented = already_indented and flt(already_indented[0][0]) or 0

				actual_so_qty = frappe.db.sql("""select sum(ifnull(qty, 0)) from `tabSales Order Item`
					where parent = %s and item_code = %s and docstatus = 1""", (so_no, item))
				actual_so_qty = actual_so_qty and flt(actual_so_qty[0][0]) or 0

				if actual_so_qty and (flt(so_items[so_no][item]) + already_indented > actual_so_qty):
					frappe.throw(_("Material Request of maximum {0} can be made for Item {1} against Sales Order {2}").format(actual_so_qty - already_indented, item, so_no))

	def validate_schedule_date(self):
		for d in self.get('indent_details'):
			if d.schedule_date and d.schedule_date < self.transaction_date:
				frappe.throw(_("Expected Date cannot be before Material Request Date"))

	# Validate
	# ---------------------
	def validate(self):
		super(MaterialRequest, self).validate()

		self.validate_schedule_date()
		self.validate_uom_is_integer("uom", "qty")

		if not self.status:
			self.status = "Draft"

		from erpnext.utilities import validate_status
		validate_status(self.status, ["Draft", "Submitted", "Stopped", "Cancelled"])

		self.validate_value("material_request_type", "in", ["Purchase", "Transfer"])

		pc_obj = frappe.get_doc('Purchase Common')
		pc_obj.validate_for_items(self)

		# self.validate_qty_against_so()
		# NOTE: Since Item BOM and FG quantities are combined, using current data, it cannot be validated
		# Though the creation of Material Request from a Production Plan can be rethought to fix this

	def update_bin(self, is_submit, is_stopped):
		""" Update Quantity Requested for Purchase in Bin for Material Request of type 'Purchase'"""

		from erpnext.stock.utils import update_bin
		for d in self.get('indent_details'):
			if frappe.db.get_value("Item", d.item_code, "is_stock_item") == "Yes":
				if not d.warehouse:
					frappe.throw(_("Warehouse required for stock Item {0}").format(d.item_code))

				qty =flt(d.qty)
				if is_stopped:
					qty = (d.qty > d.ordered_qty) and flt(flt(d.qty) - flt(d.ordered_qty)) or 0

				args = {
					"item_code": d.item_code,
					"warehouse": d.warehouse,
					"indented_qty": (is_submit and 1 or -1) * flt(qty),
					"posting_date": self.transaction_date
				}
				update_bin(args)

	def on_submit(self):
		frappe.db.set(self, 'status', 'Submitted')
		self.update_bin(is_submit = 1, is_stopped = 0)

	def check_modified_date(self):
		mod_db = frappe.db.sql("""select modified from `tabMaterial Request` where name = %s""",
			self.name)
		date_diff = frappe.db.sql("""select TIMEDIFF('%s', '%s')"""
			% (mod_db[0][0], cstr(self.modified)))

		if date_diff and date_diff[0][0]:
			frappe.throw(_("{0} {1} has been modified. Please refresh.").format(_(self.doctype), self.name))

	def update_status(self, status):
		self.check_modified_date()
		self.update_bin(is_submit = (status == 'Submitted') and 1 or 0, is_stopped = 1)
		frappe.db.set(self, 'status', cstr(status))
		frappe.msgprint(_("Status updated to {0}").format(_(status)))

	def on_cancel(self):
		# Step 1:=> Get Purchase Common Obj
		pc_obj = frappe.get_doc('Purchase Common')

		# Step 2:=> Check for stopped status
		pc_obj.check_for_stopped_status(self.doctype, self.name)

		# Step 3:=> Check if Purchase Order has been submitted against current Material Request
		pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Order', docname = self.name, detail_doctype = 'Purchase Order Item')
		# Step 4:=> Update Bin
		self.update_bin(is_submit = 0, is_stopped = (cstr(self.status) == 'Stopped') and 1 or 0)

		# Step 5:=> Set Status
		frappe.db.set(self,'status','Cancelled')

	def update_completed_qty(self, mr_items=None):
		if self.material_request_type != "Transfer":
			return

		item_doclist = self.get("indent_details")

		if not mr_items:
			mr_items = [d.name for d in item_doclist]

		per_ordered = 0.0
		for d in item_doclist:
			if d.name in mr_items:
				d.ordered_qty =  flt(frappe.db.sql("""select sum(transfer_qty)
					from `tabStock Entry Detail` where material_request = %s
					and material_request_item = %s and docstatus = 1""",
					(self.name, d.name))[0][0])
				frappe.db.set_value(d.doctype, d.name, "ordered_qty", d.ordered_qty)

			# note: if qty is 0, its row is still counted in len(item_doclist)
			# hence adding 1 to per_ordered
			if (d.ordered_qty > d.qty) or not d.qty:
				per_ordered += 1.0
			elif d.qty > 0:
				per_ordered += flt(d.ordered_qty / flt(d.qty))

		self.per_ordered = flt((per_ordered / flt(len(item_doclist))) * 100.0, 2)
		frappe.db.set_value(self.doctype, self.name, "per_ordered", self.per_ordered)

def update_completed_qty(doc, method):
	if doc.doctype == "Stock Entry":
		material_request_map = {}

		for d in doc.get("mtn_details"):
			if d.material_request:
				material_request_map.setdefault(d.material_request, []).append(d.material_request_item)

		for mr_name, mr_items in material_request_map.items():
			mr_obj = frappe.get_doc("Material Request", mr_name)

			if mr_obj.status in ["Stopped", "Cancelled"]:
				frappe.throw(_("Material Request {0} is cancelled or stopped").format(mr_obj.name),
					frappe.InvalidStatusError)

			_update_requested_qty(doc, mr_obj, mr_items)

			# update ordered percentage and qty
			mr_obj.update_completed_qty(mr_items)

def _update_requested_qty(doc, mr_obj, mr_items):
	"""update requested qty (before ordered_qty is updated)"""
	from erpnext.stock.utils import update_bin
	for mr_item_name in mr_items:
		mr_item = mr_obj.get("indent_details", {"name": mr_item_name})
		se_detail = doc.get("mtn_details", {"material_request": mr_obj.name,
			"material_request_item": mr_item_name})

		if mr_item and se_detail:
			mr_item = mr_item[0]
			se_detail = se_detail[0]
			mr_item.ordered_qty = flt(mr_item.ordered_qty)
			mr_item.qty = flt(mr_item.qty)
			se_detail.transfer_qty = flt(se_detail.transfer_qty)

			if se_detail.docstatus == 2 and mr_item.ordered_qty > mr_item.qty \
					and se_detail.transfer_qty == mr_item.ordered_qty:
				add_indented_qty = mr_item.qty
			elif se_detail.docstatus == 1 and \
					mr_item.ordered_qty + se_detail.transfer_qty > mr_item.qty:
				add_indented_qty = mr_item.qty - mr_item.ordered_qty
			else:
				add_indented_qty = se_detail.transfer_qty

			update_bin({
				"item_code": se_detail.item_code,
				"warehouse": se_detail.t_warehouse,
				"indented_qty": (se_detail.docstatus==2 and 1 or -1) * add_indented_qty,
				"posting_date": doc.posting_date,
			})

def set_missing_values(source, target_doc):
	target_doc.run_method("set_missing_values")
	target_doc.run_method("calculate_taxes_and_totals")

def update_item(obj, target, source_parent):
	target.conversion_factor = 1
	target.qty = flt(obj.qty) - flt(obj.ordered_qty)

@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None):
	doclist = get_mapped_doc("Material Request", source_name, 	{
		"Material Request": {
			"doctype": "Purchase Order",
			"validation": {
				"docstatus": ["=", 1],
				"material_request_type": ["=", "Purchase"]
			}
		},
		"Material Request Item": {
			"doctype": "Purchase Order Item",
			"field_map": [
				["name", "prevdoc_detail_docname"],
				["parent", "prevdoc_docname"],
				["parenttype", "prevdoc_doctype"],
				["uom", "stock_uom"],
				["uom", "uom"]
			],
			"postprocess": update_item
		}
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_purchase_order_based_on_supplier(source_name, target_doc=None):
	if target_doc:
		if isinstance(target_doc, basestring):
			import json
			target_doc = frappe.get_doc(json.loads(target_doc))
		target_doc.set("po_details", [])

	material_requests, supplier_items = get_material_requests_based_on_supplier(source_name)

	def postprocess(source, target_doc):
		target_doc.supplier = source_name
		set_missing_values(source, target_doc)
		target_doc.set("po_details", [d for d in target_doc.get("po_details")
			if d.get("item_code") in supplier_items and d.get("qty" > 0)])

		return target_doc

	for mr in material_requests:
		target_doc = get_mapped_doc("Material Request", mr, 	{
			"Material Request": {
				"doctype": "Purchase Order",
			},
			"Material Request Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "prevdoc_detail_docname"],
					["parent", "prevdoc_docname"],
					["parenttype", "prevdoc_doctype"],
					["uom", "stock_uom"],
					["uom", "uom"]
				],
				"postprocess": update_item
			}
		}, target_doc, postprocess)

	return target_doc

def get_material_requests_based_on_supplier(supplier):
	supplier_items = [d[0] for d in frappe.db.get_values("Item",
		{"default_supplier": supplier})]
	if supplier_items:
		material_requests = frappe.db.sql_list("""select distinct mr.name
			from `tabMaterial Request` mr, `tabMaterial Request Item` mr_item
			where mr.name = mr_item.parent
			and mr_item.item_code in (%s)
			and mr.material_request_type = 'Purchase'
			and ifnull(mr.per_ordered, 0) < 99.99
			and mr.docstatus = 1
			and mr.status != 'Stopped'""" % ', '.join(['%s']*len(supplier_items)),
			tuple(supplier_items))
	else:
		material_requests = []
	return material_requests, supplier_items

@frappe.whitelist()
def make_supplier_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc("Material Request", source_name, {
		"Material Request": {
			"doctype": "Supplier Quotation",
			"validation": {
				"docstatus": ["=", 1],
				"material_request_type": ["=", "Purchase"]
			}
		},
		"Material Request Item": {
			"doctype": "Supplier Quotation Item",
			"field_map": {
				"name": "prevdoc_detail_docname",
				"parent": "prevdoc_docname",
				"parenttype": "prevdoc_doctype"
			}
		}
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.conversion_factor = 1
		target.qty = flt(obj.qty) - flt(obj.ordered_qty)
		target.transfer_qty = flt(obj.qty) - flt(obj.ordered_qty)

	def set_missing_values(source, target):
		target.purpose = "Material Transfer"
		target.run_method("get_stock_and_rate")

	doclist = get_mapped_doc("Material Request", source_name, {
		"Material Request": {
			"doctype": "Stock Entry",
			"validation": {
				"docstatus": ["=", 1],
				"material_request_type": ["=", "Transfer"]
			}
		},
		"Material Request Item": {
			"doctype": "Stock Entry Detail",
			"field_map": {
				"name": "material_request_item",
				"parent": "material_request",
				"uom": "stock_uom",
				"warehouse": "t_warehouse"
			},
			"postprocess": update_item
		}
	}, target_doc, set_missing_values)

	return doclist
