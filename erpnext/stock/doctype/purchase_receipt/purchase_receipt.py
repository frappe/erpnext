# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cstr, flt, cint

from frappe import _
import frappe.defaults

from erpnext.controllers.buying_controller import BuyingController
from erpnext.accounts.utils import get_account_currency
from frappe.desk.notifications import clear_doctype_notifications

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class PurchaseReceipt(BuyingController):
	def __init__(self, arg1, arg2=None):
		super(PurchaseReceipt, self).__init__(arg1, arg2)
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
			'overflow_type': 'receipt'
		},
		{
			'source_dt': 'Purchase Receipt Item',
			'target_dt': 'Purchase Order Item',
			'join_field': 'prevdoc_detail_docname',
			'target_field': 'returned_qty',
			'target_parent_dt': 'Purchase Order',
			# 'target_parent_field': 'per_received',
			# 'target_ref_field': 'qty',
			'source_field': '-1 * qty',
			# 'percent_join_field': 'prevdoc_docname',
			# 'overflow_type': 'receipt',
			'extra_cond': """ and exists (select name from `tabPurchase Receipt` where name=`tabPurchase Receipt Item`.parent and is_return=1)"""
		}]

	def onload(self):
		billed_qty = frappe.db.sql("""select sum(qty) from `tabPurchase Invoice Item`
			where purchase_receipt=%s and docstatus=1""", self.name)
		if billed_qty:
			total_qty = sum((item.qty for item in self.get("items")))
			self.set_onload("billing_complete", (billed_qty[0][0] == total_qty))
			
		self.set_onload("has_return_entry", len(frappe.db.exists({"doctype": "Purchase Receipt", 
			"is_return": 1, "return_against": self.name, "docstatus": 1})))

	def validate(self):
		super(PurchaseReceipt, self).validate()

		self.set_status()
		self.po_required()
		self.validate_with_previous_doc()
		self.validate_purchase_return()
		self.validate_rejected_warehouse()
		self.validate_accepted_rejected_qty()
		self.validate_inspection()
		self.validate_uom_is_integer("uom", ["qty", "received_qty"])
		self.validate_uom_is_integer("stock_uom", "stock_qty")

		pc_obj = frappe.get_doc('Purchase Common')
		pc_obj.validate_for_items(self)
		self.check_for_stopped_or_closed_status(pc_obj)

		# sub-contracting
		self.validate_for_subcontracting()
		self.create_raw_materials_supplied("supplied_items")
		self.set_landed_cost_voucher_amount()
		self.update_valuation_rate("items")


	def set_landed_cost_voucher_amount(self):
		for d in self.get("items"):
			lc_voucher_amount = frappe.db.sql("""select sum(applicable_charges)
				from `tabLanded Cost Item`
				where docstatus = 1 and purchase_receipt_item = %s""", d.name)
			d.landed_cost_voucher_amount = lc_voucher_amount[0][0] if lc_voucher_amount else 0.0

	def validate_purchase_return(self):
		for d in self.get("items"):
			if self.is_return and flt(d.rejected_qty) != 0:
				frappe.throw(_("Row #{0}: Rejected Qty can not be entered in Purchase Return").format(d.idx))

			# validate rate with ref PR

	def validate_rejected_warehouse(self):
		for d in self.get("items"):
			if flt(d.rejected_qty) and not d.rejected_warehouse:
				d.rejected_warehouse = self.rejected_warehouse
				if not d.rejected_warehouse:
					frappe.throw(_("Rejected Warehouse is mandatory against regected item"))

	# validate accepted and rejected qty
	def validate_accepted_rejected_qty(self):
		for d in self.get("items"):
			if not flt(d.received_qty) and flt(d.qty):
				d.received_qty = flt(d.qty) - flt(d.rejected_qty)

			elif not flt(d.qty) and flt(d.rejected_qty):
				d.qty = flt(d.received_qty) - flt(d.rejected_qty)

			elif not flt(d.rejected_qty):
				d.rejected_qty = flt(d.received_qty) -  flt(d.qty)

			# Check Received Qty = Accepted Qty + Rejected Qty
			if ((flt(d.qty) + flt(d.rejected_qty)) != flt(d.received_qty)):
				frappe.throw(_("Accepted + Rejected Qty must be equal to Received quantity for Item {0}").format(d.item_code))


	def validate_with_previous_doc(self):
		super(PurchaseReceipt, self).validate_with_previous_doc({
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

		if cint(frappe.db.get_single_value('Buying Settings', 'maintain_same_rate')) and not self.is_return:
			self.validate_rate_with_reference_doc([["Purchase Order", "prevdoc_docname", "prevdoc_detail_docname"]])

	def po_required(self):
		if frappe.db.get_value("Buying Settings", None, "po_required") == 'Yes':
			 for d in self.get('items'):
				 if not d.prevdoc_docname:
					 frappe.throw(_("Purchase Order number required for Item {0}").format(d.item_code))

	def update_stock_ledger(self, allow_negative_stock=False, via_landed_cost_voucher=False):
		sl_entries = []
		stock_items = self.get_stock_items()

		for d in self.get('items'):
			if d.item_code in stock_items and d.warehouse:
				pr_qty = flt(d.qty) * flt(d.conversion_factor)

				if pr_qty:
					val_rate_db_precision = 6 if cint(self.precision("valuation_rate", d)) <= 6 else 9
					rate = flt(d.valuation_rate, val_rate_db_precision)
					sle = self.get_sl_entries(d, {
						"actual_qty": flt(pr_qty),
						"serial_no": cstr(d.serial_no).strip()
					})
					if self.is_return:
						sle.update({
							"outgoing_rate": rate
						})
					else:
						sle.update({
							"incoming_rate": rate
						})
					sl_entries.append(sle)

				if flt(d.rejected_qty) > 0:
					sl_entries.append(self.get_sl_entries(d, {
						"warehouse": d.rejected_warehouse,
						"actual_qty": flt(d.rejected_qty) * flt(d.conversion_factor),
						"serial_no": cstr(d.rejected_serial_no).strip(),
						"incoming_rate": 0.0
					}))

		self.bk_flush_supp_wh(sl_entries)
		self.make_sl_entries(sl_entries, allow_negative_stock=allow_negative_stock,
			via_landed_cost_voucher=via_landed_cost_voucher)

	def update_ordered_qty(self):
		po_map = {}
		for d in self.get("items"):
			if d.prevdoc_doctype and d.prevdoc_doctype == "Purchase Order" and d.prevdoc_detail_docname:
				po_map.setdefault(d.prevdoc_docname, []).append(d.prevdoc_detail_docname)

		for po, po_item_rows in po_map.items():
			if po and po_item_rows:
				po_obj = frappe.get_doc("Purchase Order", po)

				if po_obj.status in ["Stopped", "Cancelled"]:
					frappe.throw(_("{0} {1} is cancelled or stopped").format(_("Purchase Order"), po),
						frappe.InvalidStatusError)

				po_obj.update_ordered_qty(po_item_rows)

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
		for d in self.get('supplied_items'):
			# negative quantity is passed as raw material qty has to be decreased
			# when PR is submitted and it has to be increased when PR is cancelled
			sl_entries.append(self.get_sl_entries(d, {
				"item_code": d.rm_item_code,
				"warehouse": self.supplier_warehouse,
				"actual_qty": -1*flt(d.consumed_qty),
			}))

	def validate_inspection(self):
		for d in self.get('items'):		 #Enter inspection date for all items that require inspection
			if frappe.db.get_value("Item", d.item_code, "inspection_required") and not d.qa_no:
				frappe.msgprint(_("Quality Inspection required for Item {0}").format(d.item_code))
				if self.docstatus==1:
					raise frappe.ValidationError

	# Check for Stopped status
	def check_for_stopped_or_closed_status(self, pc_obj):
		check_list =[]
		for d in self.get('items'):
			if d.meta.get_field('prevdoc_docname') and d.prevdoc_docname and d.prevdoc_docname not in check_list:
				check_list.append(d.prevdoc_docname)
				pc_obj.check_for_stopped_or_closed_status(d.prevdoc_doctype, d.prevdoc_docname)

	# on submit
	def on_submit(self):
		purchase_controller = frappe.get_doc("Purchase Common")

		# Check for Approving Authority
		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype, self.company, self.base_grand_total)

		# Set status as Submitted
		frappe.db.set(self, 'status', 'Submitted')

		self.update_prevdoc_status()
		self.update_ordered_qty()

		if not self.is_return:
			purchase_controller.update_last_purchase_rate(self, 1)

		self.update_stock_ledger()

		from erpnext.stock.doctype.serial_no.serial_no import update_serial_nos_after_submit
		update_serial_nos_after_submit(self, "items")

		self.make_gl_entries()

	def check_next_docstatus(self):
		submit_rv = frappe.db.sql("""select t1.name
			from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2
			where t1.name = t2.parent and t2.purchase_receipt = %s and t1.docstatus = 1""",
			(self.name))
		if submit_rv:
			frappe.throw(_("Purchase Invoice {0} is already submitted").format(self.submit_rv[0][0]))

	def on_cancel(self):
		pc_obj = frappe.get_doc('Purchase Common')

		self.check_for_stopped_or_closed_status(pc_obj)
		# Check if Purchase Invoice has been submitted against current Purchase Order
		submitted = frappe.db.sql("""select t1.name
			from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2
			where t1.name = t2.parent and t2.purchase_receipt = %s and t1.docstatus = 1""",
			self.name)
		if submitted:
			frappe.throw(_("Purchase Invoice {0} is already submitted").format(submitted[0][0]))

		frappe.db.set(self,'status','Cancelled')

		self.update_stock_ledger()

		self.update_prevdoc_status()
		# Must be called after updating received qty in PO
		self.update_ordered_qty()

		if not self.is_return:
			pc_obj.update_last_purchase_rate(self, 0)

		self.make_gl_entries_on_cancel()

	def get_current_stock(self):
		for d in self.get('supplied_items'):
			if self.supplier_warehouse:
				bin = frappe.db.sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.rm_item_code, self.supplier_warehouse), as_dict = 1)
				d.current_stock = bin and flt(bin[0]['actual_qty']) or 0

	def get_rate(self,arg):
		return frappe.get_doc('Purchase Common').get_rate(arg,self)

	def get_gl_entries(self, warehouse_account=None):
		from erpnext.accounts.general_ledger import process_gl_map

		stock_rbnb = self.get_company_default("stock_received_but_not_billed")
		expenses_included_in_valuation = self.get_company_default("expenses_included_in_valuation")

		gl_entries = []
		warehouse_with_no_account = []
		negative_expense_to_be_booked = 0.0
		stock_items = self.get_stock_items()
		for d in self.get("items"):
			if d.item_code in stock_items and flt(d.valuation_rate) and flt(d.qty):
				if warehouse_account.get(d.warehouse):

					val_rate_db_precision = 6 if cint(d.precision("valuation_rate")) <= 6 else 9

					# warehouse account
					stock_value_diff = flt(flt(d.valuation_rate, val_rate_db_precision) * flt(d.qty)
						* flt(d.conversion_factor),	d.precision("base_net_amount"))

					gl_entries.append(self.get_gl_dict({
						"account": warehouse_account[d.warehouse]["name"],
						"against": stock_rbnb,
						"cost_center": d.cost_center,
						"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
						"debit": stock_value_diff
					}, warehouse_account[d.warehouse]["account_currency"]))

					# stock received but not billed
					stock_rbnb_currency = get_account_currency(stock_rbnb)
					gl_entries.append(self.get_gl_dict({
						"account": stock_rbnb,
						"against": warehouse_account[d.warehouse]["name"],
						"cost_center": d.cost_center,
						"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
						"credit": flt(d.base_net_amount, d.precision("base_net_amount")),
						"credit_in_account_currency": flt(d.base_net_amount, d.precision("base_net_amount")) \
							if stock_rbnb_currency==self.company_currency else flt(d.net_amount, d.precision("net_amount"))
					}, stock_rbnb_currency))

					negative_expense_to_be_booked += flt(d.item_tax_amount)

					# Amount added through landed-cost-voucher
					if flt(d.landed_cost_voucher_amount):
						gl_entries.append(self.get_gl_dict({
							"account": expenses_included_in_valuation,
							"against": warehouse_account[d.warehouse]["name"],
							"cost_center": d.cost_center,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"credit": flt(d.landed_cost_voucher_amount)
						}))

					# sub-contracting warehouse
					if flt(d.rm_supp_cost) and warehouse_account.get(self.supplier_warehouse):
						gl_entries.append(self.get_gl_dict({
							"account": warehouse_account[self.supplier_warehouse]["name"],
							"against": warehouse_account[d.warehouse]["name"],
							"cost_center": d.cost_center,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"credit": flt(d.rm_supp_cost)
						}, warehouse_account[self.supplier_warehouse]["account_currency"]))

					# divisional loss adjustment
					sle_valuation_amount = flt(flt(d.valuation_rate, val_rate_db_precision) * flt(d.qty) * flt(d.conversion_factor),
							self.precision("base_net_amount", d))

					distributed_amount = flt(flt(d.base_net_amount, self.precision("base_net_amount", d))) + \
						flt(d.landed_cost_voucher_amount) + flt(d.rm_supp_cost) + flt(d.item_tax_amount)

					divisional_loss = flt(distributed_amount - sle_valuation_amount, self.precision("base_net_amount", d))
					if divisional_loss:
						gl_entries.append(self.get_gl_dict({
							"account": stock_rbnb,
							"against": warehouse_account[d.warehouse]["name"],
							"cost_center": d.cost_center,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"debit": divisional_loss
						}, stock_rbnb_currency))

				elif d.warehouse not in warehouse_with_no_account or \
					d.rejected_warehouse not in warehouse_with_no_account:
						warehouse_with_no_account.append(d.warehouse)

		# Cost center-wise amount breakup for other charges included for valuation
		valuation_tax = {}
		for tax in self.get("taxes"):
			if tax.category in ("Valuation", "Valuation and Total") and flt(tax.base_tax_amount_after_discount_amount):
				if not tax.cost_center:
					frappe.throw(_("Cost Center is required in row {0} in Taxes table for type {1}").format(tax.idx, _(tax.category)))
				valuation_tax.setdefault(tax.cost_center, 0)
				valuation_tax[tax.cost_center] += \
					(tax.add_deduct_tax == "Add" and 1 or -1) * flt(tax.base_tax_amount_after_discount_amount)

		if negative_expense_to_be_booked and valuation_tax:
			# Backward compatibility:
			# If expenses_included_in_valuation account has been credited in against PI
			# and charges added via Landed Cost Voucher,
			# post valuation related charges on "Stock Received But Not Billed"

			negative_expense_booked_in_pi = frappe.db.sql("""select name from `tabPurchase Invoice Item` pi
				where docstatus = 1 and purchase_receipt=%s
				and exists(select name from `tabGL Entry` where voucher_type='Purchase Invoice'
					and voucher_no=pi.parent and account=%s)""", (self.name, expenses_included_in_valuation))

			if negative_expense_booked_in_pi:
				expenses_included_in_valuation = stock_rbnb

			against_account = ", ".join([d.account for d in gl_entries if flt(d.debit) > 0])
			total_valuation_amount = sum(valuation_tax.values())
			amount_including_divisional_loss = negative_expense_to_be_booked
			i = 1
			for cost_center, amount in valuation_tax.items():
				if i == len(valuation_tax):
					applicable_amount = amount_including_divisional_loss
				else:
					applicable_amount = negative_expense_to_be_booked * (amount / total_valuation_amount)
					amount_including_divisional_loss -= applicable_amount

				gl_entries.append(
					self.get_gl_dict({
						"account": expenses_included_in_valuation,
						"cost_center": cost_center,
						"credit": applicable_amount,
						"remarks": self.remarks or _("Accounting Entry for Stock"),
						"against": against_account
					})
				)

				i += 1

		if warehouse_with_no_account:
			frappe.msgprint(_("No accounting entries for the following warehouses") + ": \n" +
				"\n".join(warehouse_with_no_account))

		return process_gl_map(gl_entries)

	def update_status(self, status):
		self.set_status(update=True, status = status)
		self.notify_update()
		clear_doctype_notifications(self)

@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		if len(target.get("items")) == 0:
			frappe.throw(_("All items have already been invoiced"))

		doc = frappe.get_doc(target)
		doc.ignore_pricing_rule = 1
		doc.run_method("set_missing_values")
		doc.run_method("calculate_taxes_and_totals")

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = source_doc.qty - invoiced_qty_map.get(source_doc.name, 0)

	doclist = get_mapped_doc("Purchase Receipt", source_name,	{
		"Purchase Receipt": {
			"doctype": "Purchase Invoice",
			"validation": {
				"docstatus": ["=", 1],
			},
		},
		"Purchase Receipt Item": {
			"doctype": "Purchase Invoice Item",
			"field_map": {
				"name": "pr_detail",
				"parent": "purchase_receipt",
				"prevdoc_detail_docname": "po_detail",
				"prevdoc_docname": "purchase_order",
			},
			"postprocess": update_item,
			"filter": lambda d: abs(d.qty) - abs(invoiced_qty_map.get(d.name, 0))<=0
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return doclist

def get_invoiced_qty_map(purchase_receipt):
	"""returns a map: {pr_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for pr_detail, qty in frappe.db.sql("""select pr_detail, qty from `tabPurchase Invoice Item`
		where purchase_receipt=%s and docstatus=1""", purchase_receipt):
			if not invoiced_qty_map.get(pr_detail):
				invoiced_qty_map[pr_detail] = 0
			invoiced_qty_map[pr_detail] += qty

	return invoiced_qty_map

@frappe.whitelist()
def make_purchase_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc
	return make_return_doc("Purchase Receipt", source_name, target_doc)


@frappe.whitelist()
def update_purchase_receipt_status(docname, status):
	pr = frappe.get_doc("Purchase Receipt", docname)
	pr.update_status(status)
