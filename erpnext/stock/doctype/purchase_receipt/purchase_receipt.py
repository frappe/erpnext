# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cstr, flt, cint

from frappe import msgprint, _
import frappe.defaults
from erpnext.stock.utils import update_bin

from erpnext.controllers.buying_controller import BuyingController
class PurchaseReceipt(BuyingController):
		self.tname = 'Purchase Receipt Item'
		self.fname = 'purchase_receipt_details'
		self.count = 0
		self.status_updater = [{
			'source_dt': 'Purchase Receipt Item',
			'target_dt': 'Purchase Order Item',
			'join_field': 'prevdoc_detail_docname',
			'target_field': 'received_qty',
			'target_parent_dt': 'Purchase Order',
			'target_parent_field': 'per_received',
			'target_ref_field': 'qty',
			'source_field': 'qty',
			'percent_join_field': 'prevdoc_docname',
		}]
		
	def onload(self):
		billed_qty = frappe.db.sql("""select sum(ifnull(qty, 0)) from `tabPurchase Invoice Item`
			where purchase_receipt=%s""", self.name)
		if billed_qty:
			total_qty = sum((item.qty for item in self.get("purchase_receipt_details")))
			self.set("__billing_complete", billed_qty[0][0] == total_qty)

	def validate(self):
		super(DocType, self).validate()
		
		self.po_required()

		if not self.status:
			self.status = "Draft"

		from erpnext.utilities import validate_status
		validate_status(self.status, ["Draft", "Submitted", "Cancelled"])

		self.validate_with_previous_doc()
		self.validate_rejected_warehouse()
		self.validate_accepted_rejected_qty()
		self.validate_inspection()
		self.validate_uom_is_integer("uom", ["qty", "received_qty"])
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_challan_no()

		pc_obj = frappe.get_doc(dt='Purchase Common')
		pc_obj.validate_for_items(self)
		self.check_for_stopped_status(pc_obj)

		# sub-contracting
		self.validate_for_subcontracting()
		self.update_raw_materials_supplied("pr_raw_material_details")
		
		self.update_valuation_rate("purchase_receipt_details")

	def validate_rejected_warehouse(self):
		for d in self.get("purchase_receipt_details"):
			if flt(d.rejected_qty) and not d.rejected_warehouse:
				d.rejected_warehouse = self.rejected_warehouse
				if not d.rejected_warehouse:
					frappe.throw(_("Rejected Warehouse is mandatory against regected item"))		

	# validate accepted and rejected qty
	def validate_accepted_rejected_qty(self):
		for d in self.get("purchase_receipt_details"):
			if not flt(d.received_qty) and flt(d.qty):
				d.received_qty = flt(d.qty) - flt(d.rejected_qty)

			elif not flt(d.qty) and flt(d.rejected_qty):
				d.qty = flt(d.received_qty) - flt(d.rejected_qty)

			elif not flt(d.rejected_qty):
				d.rejected_qty = flt(d.received_qty) -  flt(d.qty)

			# Check Received Qty = Accepted Qty + Rejected Qty
			if ((flt(d.qty) + flt(d.rejected_qty)) != flt(d.received_qty)):

				msgprint("Sum of Accepted Qty and Rejected Qty must be equal to Received quantity. Error for Item: " + cstr(d.item_code))
				raise Exception


	def validate_challan_no(self):
		"Validate if same challan no exists for same supplier in a submitted purchase receipt"
		if self.challan_no:
			exists = frappe.db.sql("""
			SELECT name FROM `tabPurchase Receipt`
			WHERE name!=%s AND supplier=%s AND challan_no=%s
		AND docstatus=1""", (self.name, self.supplier, self.challan_no))
			if exists:
				frappe.msgprint("Another Purchase Receipt using the same Challan No. already exists.\
			Please enter a valid Challan No.", raise_exception=1)
			
	def validate_with_previous_doc(self):
		super(DocType, self).validate_with_previous_doc(self.tname, {
			"Purchase Order": {
				"ref_dn_field": "prevdoc_docname",
				"compare_fields": [["supplier", "="], ["company", "="],	["currency", "="]],
			},
			"Purchase Order Item": {
				"ref_dn_field": "prevdoc_detail_docname",
				"compare_fields": [["project_name", "="], ["uom", "="], ["item_code", "="]],
				"is_child_table": True
			}
		})
		
		if cint(frappe.defaults.get_global_default('maintain_same_rate')):
			super(DocType, self).validate_with_previous_doc(self.tname, {
				"Purchase Order Item": {
					"ref_dn_field": "prevdoc_detail_docname",
					"compare_fields": [["rate", "="]],
					"is_child_table": True
				}
			})
			

	def po_required(self):
		if frappe.db.get_value("Buying Settings", None, "po_required") == 'Yes':
			 for d in self.get('purchase_receipt_details'):
				 if not d.prevdoc_docname:
					 msgprint("Purchse Order No. required against item %s"%d.item_code)
					 raise Exception

	def update_stock(self):
		sl_entries = []
		stock_items = self.get_stock_items()
		
		for d in self.get('purchase_receipt_details'):
			if d.item_code in stock_items and d.warehouse:
				pr_qty = flt(d.qty) * flt(d.conversion_factor)
				
				if pr_qty:
					sl_entries.append(self.get_sl_entries(d, {
						"actual_qty": flt(pr_qty),
						"serial_no": cstr(d.serial_no).strip(),
						"incoming_rate": d.valuation_rate
					}))
				
				if flt(d.rejected_qty) > 0:
					sl_entries.append(self.get_sl_entries(d, {
						"warehouse": d.rejected_warehouse,
						"actual_qty": flt(d.rejected_qty) * flt(d.conversion_factor),
						"serial_no": cstr(d.rejected_serial_no).strip(),
						"incoming_rate": d.valuation_rate
					}))
						
		self.bk_flush_supp_wh(sl_entries)
		self.make_sl_entries(sl_entries)
				
	def update_ordered_qty(self):
		stock_items = self.get_stock_items()
		for d in self.get("purchase_receipt_details"):
			if d.item_code in stock_items and d.warehouse \
					and cstr(d.prevdoc_doctype) == 'Purchase Order':
									
				already_received_qty = self.get_already_received_qty(d.prevdoc_docname, 
					d.prevdoc_detail_docname)
				po_qty, ordered_warehouse = self.get_po_qty_and_warehouse(d.prevdoc_detail_docname)
				
				if not ordered_warehouse:
					frappe.throw(_("Warehouse is missing in Purchase Order"))
				
				if already_received_qty + d.qty > po_qty:
					ordered_qty = - (po_qty - already_received_qty) * flt(d.conversion_factor)
				else:
					ordered_qty = - flt(d.qty) * flt(d.conversion_factor)
				
				update_bin({
					"item_code": d.item_code,
					"warehouse": ordered_warehouse,
					"posting_date": self.posting_date,
					"ordered_qty": flt(ordered_qty) if self.docstatus==1 else -flt(ordered_qty)
				})

	def get_already_received_qty(self, po, po_detail):
		qty = frappe.db.sql("""select sum(qty) from `tabPurchase Receipt Item` 
			where prevdoc_detail_docname = %s and docstatus = 1 
			and prevdoc_doctype='Purchase Order' and prevdoc_docname=%s 
			and parent != %s""", (po_detail, po, self.name))
		return qty and flt(qty[0][0]) or 0.0
		
	def get_po_qty_and_warehouse(self, po_detail):
		po_qty, po_warehouse = frappe.db.get_value("Purchase Order Item", po_detail, 
			["qty", "warehouse"])
		return po_qty, po_warehouse
	
	def bk_flush_supp_wh(self, sl_entries):
		for d in self.get('pr_raw_material_details'):
			# negative quantity is passed as raw material qty has to be decreased 
			# when PR is submitted and it has to be increased when PR is cancelled
			sl_entries.append(self.get_sl_entries(d, {
				"item_code": d.rm_item_code,
				"warehouse": self.supplier_warehouse,
				"actual_qty": -1*flt(d.consumed_qty),
				"incoming_rate": 0
			}))

	def validate_inspection(self):
		for d in self.get('purchase_receipt_details'):		 #Enter inspection date for all items that require inspection
			ins_reqd = frappe.db.sql("select inspection_required from `tabItem` where name = %s",
				(d.item_code,), as_dict = 1)
			ins_reqd = ins_reqd and ins_reqd[0]['inspection_required'] or 'No'
			if ins_reqd == 'Yes' and not d.qa_no:
				msgprint("Item: " + d.item_code + " requires QA Inspection. Please enter QA No or report to authorized person to create Quality Inspection")

	# Check for Stopped status
	def check_for_stopped_status(self, pc_obj):
		check_list =[]
		for d in self.get('purchase_receipt_details'):
			if d.fields.has_key('prevdoc_docname') and d.prevdoc_docname and d.prevdoc_docname not in check_list:
				check_list.append(d.prevdoc_docname)
				pc_obj.check_for_stopped_status( d.prevdoc_doctype, d.prevdoc_docname)

	# on submit
	def on_submit(self):
		purchase_controller = frappe.get_doc("Purchase Common")

		# Check for Approving Authority
		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype, self.company, self.grand_total)

		# Set status as Submitted
		frappe.db.set(self, 'status', 'Submitted')

		self.update_prevdoc_status()
		
		self.update_ordered_qty()
		
		self.update_stock()

		from erpnext.stock.doctype.serial_no.serial_no import update_serial_nos_after_submit
		update_serial_nos_after_submit(self, "purchase_receipt_details")

		purchase_controller.update_last_purchase_rate(self, 1)
		
		self.make_gl_entries()

	def check_next_docstatus(self):
		submit_rv = frappe.db.sql("""select t1.name 
			from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2 
			where t1.name = t2.parent and t2.purchase_receipt = %s and t1.docstatus = 1""", 
			(self.name))
		if submit_rv:
			msgprint("Purchase Invoice : " + cstr(self.submit_rv[0][0]) + " has already been submitted !")
			raise Exception , "Validation Error."


	def on_cancel(self):
		pc_obj = frappe.get_doc('Purchase Common')

		self.check_for_stopped_status(pc_obj)
		# Check if Purchase Invoice has been submitted against current Purchase Order
		submitted = frappe.db.sql("""select t1.name 
			from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2 
			where t1.name = t2.parent and t2.purchase_receipt = %s and t1.docstatus = 1""", 
			self.name)
		if submitted:
			frappe.throw("Purchase Invoice : " + cstr(submitted[0][0]) + 
				" has already been submitted !")
		
		frappe.db.set(self,'status','Cancelled')

		self.update_ordered_qty()
		
		self.update_stock()

		self.update_prevdoc_status()
		pc_obj.update_last_purchase_rate(self, 0)
		
		self.make_cancel_gl_entries()
			
	def get_current_stock(self):
		for d in self.get('pr_raw_material_details'):
			if self.supplier_warehouse:
				bin = frappe.db.sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.rm_item_code, self.supplier_warehouse), as_dict = 1)
				d.current_stock = bin and flt(bin[0]['actual_qty']) or 0

	def get_rate(self,arg):
		return frappe.get_doc('Purchase Common').get_rate(arg,self)
		
	def get_gl_entries(self, warehouse_account=None):
		against_stock_account = self.get_company_default("stock_received_but_not_billed")
		
		gl_entries = super(DocType, self).get_gl_entries(warehouse_account, against_stock_account)
		return gl_entries
		
	
@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc
	
	def set_missing_values(source, target):
		bean = frappe.get_doc(target)
		bean.run_method("set_missing_values")

	doclist = get_mapped_doc("Purchase Receipt", source_name,	{
		"Purchase Receipt": {
			"doctype": "Purchase Invoice", 
			"validation": {
				"docstatus": ["=", 1],
			}
		}, 
		"Purchase Receipt Item": {
			"doctype": "Purchase Invoice Item", 
			"field_map": {
				"name": "pr_detail", 
				"parent": "purchase_receipt", 
				"prevdoc_detail_docname": "po_detail", 
				"prevdoc_docname": "purchase_order", 
			},
		}, 
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges", 
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return [d.fields for d in doclist]