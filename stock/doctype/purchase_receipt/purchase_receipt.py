# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt, cint
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint
import webnotes.defaults
from stock.utils import update_bin

from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
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
		billed_qty = webnotes.conn.sql("""select sum(ifnull(qty, 0)) from `tabPurchase Invoice Item`
			where purchase_receipt=%s""", self.doc.name)
		if billed_qty:
			total_qty = sum((item.qty for item in self.doclist.get({"parentfield": "purchase_receipt_details"})))
			self.doc.fields["__billing_complete"] = billed_qty[0][0] == total_qty

	# get available qty at warehouse
	def get_bin_details(self, arg = ''):
		return get_obj(dt='Purchase Common').get_bin_details(arg)


	# validate accepted and rejected qty
	def validate_accepted_rejected_qty(self):
		for d in getlist(self.doclist, "purchase_receipt_details"):

			# If Reject Qty than Rejected warehouse is mandatory
			if flt(d.rejected_qty) and (not self.doc.rejected_warehouse):
				msgprint("Rejected Warehouse is necessary if there are rejections.")
				raise Exception

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
		if self.doc.challan_no:
			exists = webnotes.conn.sql("""
			SELECT name FROM `tabPurchase Receipt`
			WHERE name!=%s AND supplier=%s AND challan_no=%s
		AND docstatus=1""", (self.doc.name, self.doc.supplier, self.doc.challan_no))
			if exists:
				webnotes.msgprint("Another Purchase Receipt using the same Challan No. already exists.\
			Please enter a valid Challan No.", raise_exception=1)
			
	def validate_with_previous_doc(self):
		super(DocType, self).validate_with_previous_doc(self.tname, {
			"Purchase Order": {
				"ref_dn_field": "prevdoc_docname",
				"compare_fields": [["supplier", "="], ["company", "="],	["currency", "="]],
			},
			"Purchase Order Item": {
				"ref_dn_field": "prevdoc_detail_docname",
				"compare_fields": [["project_name", "="], ["warehouse", "="], 
					["uom", "="], ["item_code", "="]],
				"is_child_table": True
			}
		})
		
		if cint(webnotes.defaults.get_global_default('maintain_same_rate')):
			super(DocType, self).validate_with_previous_doc(self.tname, {
				"Purchase Order Item": {
					"ref_dn_field": "prevdoc_detail_docname",
					"compare_fields": [["import_rate", "="]],
					"is_child_table": True
				}
			})
			

	def po_required(self):
		if webnotes.conn.get_value("Buying Settings", None, "po_required") == 'Yes':
			 for d in getlist(self.doclist,'purchase_receipt_details'):
				 if not d.prevdoc_docname:
					 msgprint("Purchse Order No. required against item %s"%d.item_code)
					 raise Exception

	def validate(self):
		super(DocType, self).validate()
		
		self.po_required()

		if not self.doc.status:
			self.doc.status = "Draft"

		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Cancelled"])

		self.validate_with_previous_doc()
		self.validate_accepted_rejected_qty()
		self.validate_inspection()
		self.validate_uom_is_integer("uom", ["qty", "received_qty"])
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_challan_no()

		pc_obj = get_obj(dt='Purchase Common')
		pc_obj.validate_for_items(self)
		pc_obj.get_prevdoc_date(self)
		self.check_for_stopped_status(pc_obj)

		# sub-contracting
		self.validate_for_subcontracting()
		self.update_raw_materials_supplied("pr_raw_material_details")
		
		self.update_valuation_rate("purchase_receipt_details")
		
	def on_update(self):
		if self.doc.rejected_warehouse:
			for d in getlist(self.doclist,'purchase_receipt_details'):
				d.rejected_warehouse = self.doc.rejected_warehouse

	def update_stock(self):
		sl_entries = []
		stock_items = self.get_stock_items()
		
		for d in getlist(self.doclist, 'purchase_receipt_details'):
			if d.item_code in stock_items and d.warehouse:
				pr_qty = flt(d.qty) * flt(d.conversion_factor)
				self.update_ordered_qty(pr_qty, d)
				
				if pr_qty:
					sl_entries.append(self.get_sl_entries(d, {
						"actual_qty": flt(pr_qty),
						"serial_no": cstr(d.serial_no).strip(),
						"incoming_rate": d.valuation_rate
					}))
				
				if flt(d.rejected_qty) > 0:
					sl_entries.append(self.get_sl_entries(d, {
						"warehouse": self.doc.rejected_warehouse,
						"actual_qty": flt(d.rejected_qty) * flt(d.conversion_factor),
						"serial_no": cstr(d.rejected_serial_no).strip(),
						"incoming_rate": d.valuation_rate
					}))
						
		self.bk_flush_supp_wh(sl_entries)
		self.make_sl_entries(sl_entries)
		
	def update_ordered_qty(self, pr_qty, d):
		pc_obj = get_obj('Purchase Common')
		if cstr(d.prevdoc_doctype) == 'Purchase Order':
			# get qty and pending_qty of prevdoc
			curr_ref_qty = pc_obj.get_qty( d.doctype, 'prevdoc_detail_docname',
			 	d.prevdoc_detail_docname, 'Purchase Order Item', 
				'Purchase Order - Purchase Receipt', self.doc.name)
			max_qty, qty, curr_qty = flt(curr_ref_qty.split('~~~')[1]), \
			 	flt(curr_ref_qty.split('~~~')[0]), 0

			if flt(qty) + flt(pr_qty) > flt(max_qty):
				curr_qty = (flt(max_qty) - flt(qty)) * flt(d.conversion_factor)
			else:
				curr_qty = flt(pr_qty)
				
			args = {
				"item_code": d.item_code,
				"warehouse": d.warehouse,
				"posting_date": self.doc.posting_date,
				"ordered_qty": self.doc.docstatus==1 and -1*flt(curr_qty) or flt(curr_qty)
			}
			update_bin(args)
	
	def bk_flush_supp_wh(self, sl_entries):
		for d in getlist(self.doclist, 'pr_raw_material_details'):
			# negative quantity is passed as raw material qty has to be decreased 
			# when PR is submitted and it has to be increased when PR is cancelled
			sl_entries.append(self.get_sl_entries(d, {
				"item_code": d.rm_item_code,
				"warehouse": self.doc.supplier_warehouse,
				"actual_qty": -1*flt(consumed_qty),
				"incoming_rate": 0
			}))

	def validate_inspection(self):
		for d in getlist(self.doclist, 'purchase_receipt_details'):		 #Enter inspection date for all items that require inspection
			ins_reqd = webnotes.conn.sql("select inspection_required from `tabItem` where name = %s",
				(d.item_code,), as_dict = 1)
			ins_reqd = ins_reqd and ins_reqd[0]['inspection_required'] or 'No'
			if ins_reqd == 'Yes' and not d.qa_no:
				msgprint("Item: " + d.item_code + " requires QA Inspection. Please enter QA No or report to authorized person to create Quality Inspection")

	# Check for Stopped status
	def check_for_stopped_status(self, pc_obj):
		check_list =[]
		for d in getlist(self.doclist, 'purchase_receipt_details'):
			if d.fields.has_key('prevdoc_docname') and d.prevdoc_docname and d.prevdoc_docname not in check_list:
				check_list.append(d.prevdoc_docname)
				pc_obj.check_for_stopped_status( d.prevdoc_doctype, d.prevdoc_docname)

	# on submit
	def on_submit(self):
		purchase_controller = webnotes.get_obj("Purchase Common")
		purchase_controller.is_item_table_empty(self)

		# Check for Approving Authority
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.grand_total)

		# Set status as Submitted
		webnotes.conn.set(self.doc, 'status', 'Submitted')

		self.update_prevdoc_status()
		
		# Update Stock
		self.update_stock()

		self.update_serial_nos()

		# Update last purchase rate
		purchase_controller.update_last_purchase_rate(self, 1)
		
		self.make_gl_entries()
		
	def update_serial_nos(self, cancel=False):
		from stock.doctype.stock_ledger_entry.stock_ledger_entry import update_serial_nos_after_submit, get_serial_nos
		update_serial_nos_after_submit(self, "Purchase Receipt", "purchase_receipt_details")

		for d in self.doclist.get({"parentfield": "purchase_receipt_details"}):
			for serial_no in get_serial_nos(d.serial_no):
				sr = webnotes.bean("Serial No", serial_no)
				if cancel:
					sr.doc.supplier = None
					sr.doc.supplier_name = None
				else:
					sr.doc.supplier = self.doc.supplier
					sr.doc.supplier_name = self.doc.supplier_name
				sr.save()

	def check_next_docstatus(self):
		submit_rv = webnotes.conn.sql("select t1.name from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2 where t1.name = t2.parent and t2.purchase_receipt = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_rv:
			msgprint("Purchase Invoice : " + cstr(self.submit_rv[0][0]) + " has already been submitted !")
			raise Exception , "Validation Error."


	def on_cancel(self):
		pc_obj = get_obj('Purchase Common')

		self.check_for_stopped_status(pc_obj)
		# 1.Check if Purchase Invoice has been submitted against current Purchase Order
		# pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Invoice', docname = self.doc.name, detail_doctype = 'Purchase Invoice Item')

		submitted = webnotes.conn.sql("select t1.name from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2 where t1.name = t2.parent and t2.purchase_receipt = '%s' and t1.docstatus = 1" % self.doc.name)
		if submitted:
			msgprint("Purchase Invoice : " + cstr(submitted[0][0]) + " has already been submitted !")
			raise Exception

		# 2.Set Status as Cancelled
		webnotes.conn.set(self.doc,'status','Cancelled')

		# 3. Cancel Serial No
		self.update_stock()
		self.update_serial_nos(cancel=True)

		self.update_prevdoc_status()
		pc_obj.update_last_purchase_rate(self, 0)
		
		self.make_cancel_gl_entries()
			
	def get_current_stock(self):
		for d in getlist(self.doclist, 'pr_raw_material_details'):
			if self.doc.supplier_warehouse:
				bin = webnotes.conn.sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.rm_item_code, self.doc.supplier_warehouse), as_dict = 1)
				d.current_stock = bin and flt(bin[0]['actual_qty']) or 0


	def get_rate(self,arg):
		return get_obj('Purchase Common').get_rate(arg,self)
			
	def get_gl_entries_for_stock(self):
		against_stock_account = self.get_company_default("stock_received_but_not_billed")
		
		gl_entries = super(DocType, self).get_gl_entries_for_stock(against_stock_account, None)
		return gl_entries
		
	
@webnotes.whitelist()
def make_purchase_invoice(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist
	
	def set_missing_values(source, target):
		bean = webnotes.bean(target)
		bean.run_method("set_missing_values")
		bean.run_method("set_supplier_defaults")

	doclist = get_mapped_doclist("Purchase Receipt", source_name,	{
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
				"purchase_rate": "rate"
			},
		}, 
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges", 
			"add_if_empty": True
		}
	}, target_doclist, set_missing_values)

	return [d.fields for d in doclist]