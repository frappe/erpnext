# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
import frappe.defaults
from erpnext.controllers.selling_controller import SellingController
from erpnext.stock.doctype.serial_no.serial_no import get_delivery_note_serial_no
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.utils import cint, flt
from six import string_types


form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}


class DeliveryNote(SellingController):
	def __init__(self, *args, **kwargs):
		super(DeliveryNote, self).__init__(*args, **kwargs)
		self.status_map = [
			["Draft", None],
			["To Bill", "eval:self.per_completed < 100 and self.docstatus == 1"],
			["Completed", "eval:self.per_completed == 100 and self.docstatus == 1"],
			["Return", "eval:self.is_return and self.docstatus == 1"],
			["Cancelled", "eval:self.docstatus==2"],
			["Closed", "eval:self.status=='Closed'"],
		]

	def validate(self):
		self.validate_posting_time()
		super(DeliveryNote, self).validate()
		self.validate_order_required()
		self.check_sales_order_on_hold_or_close()
		self.validate_project_customer()
		self.validate_warehouse()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import validate_inter_company_party
		validate_inter_company_party(self.doctype, self.customer, self.company, self.inter_company_reference)

		from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
		make_packing_list(self)

		self.validate_with_previous_doc()
		self.set_billing_status()
		self.set_installation_status()
		self.set_status()
		self.set_title()

		self.update_current_stock()

	def on_submit(self):
		self.validate_packed_qty()

		# Check for Approving Authority
		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype, self.company, self.base_grand_total, self)

		# update delivered qty in sales order
		self.validate_previous_docstatus()
		self.update_billing_status()
		self.update_previous_doc_status()

		if not self.is_return:
			self.check_credit_limit()

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import update_linked_doc
		update_linked_doc(self.doctype, self.name, self.inter_company_reference)

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		self.update_stock_ledger()
		self.make_gl_entries()

	def on_cancel(self):
		super(DeliveryNote, self).on_cancel()

		self.check_next_docstatus()

		self.update_billing_status()
		self.update_previous_doc_status()
		self.cancel_packing_slips()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import unlink_inter_company_doc
		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_reference)

	def before_print(self):
		def toggle_print_hide(meta, fieldname):
			df = meta.get_field(fieldname)
			if self.get("print_without_amount"):
				df.set("__print_hide", 1)
			else:
				df.delete_key("__print_hide")

		item_meta = frappe.get_meta("Delivery Note Item")
		print_hide_fields = {
			"parent": ["grand_total", "rounded_total", "in_words", "currency", "total", "taxes"],
			"items": ["rate", "amount", "discount_amount", "price_list_rate", "discount_percentage"]
		}

		for key, fieldname in print_hide_fields.items():
			for f in fieldname:
				toggle_print_hide(self.meta if key == "parent" else item_meta, f)

		super(DeliveryNote, self).before_print()

	def set_title(self):
		self.title = self.customer_name or self.customer

	def validate_previous_docstatus(self):
		for d in self.get('items'):
			if d.sales_order and frappe.db.get_value("Sales Order", d.sales_order, "docstatus", cache=1) != 1:
				frappe.throw(_("Row #{0}: Sales Order {1} is not submitted").format(d.idx, d.sales_order))

			if d.sales_invoice and frappe.db.get_value("Sales Invoice", d.sales_invoice, "docstatus", cache=1) != 1:
				frappe.throw(_("Row #{0}: Sales Invoice {1} is not submitted").format(d.idx, d.delivery_note))

			if self.return_against and frappe.db.get_value("Delivery Note", self.return_against, "docstatus", cache=1) != 1:
				frappe.throw(_("Return Against Delivery Note {0} is not submitted").format(self.return_against))

	def update_previous_doc_status(self):
		sales_orders = set()
		sales_invoices = set()
		sales_order_row_names = set()
		sales_invoice_row_names = set()
		delivery_note_row_names = set()

		for d in self.items:
			if d.sales_order:
				sales_orders.add(d.sales_order)
			if d.sales_invoice:
				sales_invoices.add(d.sales_invoice)
			if d.sales_order_item:
				sales_order_row_names.add(d.sales_order_item)
			if d.sales_invoice_item:
				sales_invoice_row_names.add(d.sales_invoice_item)
			if d.delivery_note_item:
				delivery_note_row_names.add(d.delivery_note_item)

		# Update Sales Orders
		for name in sales_orders:
			doc = frappe.get_doc("Sales Order", name)
			doc.set_delivery_status(update=True)
			doc.validate_delivered_qty(from_doctype=self.doctype, row_names=sales_order_row_names)

			if self.is_return:
				doc.set_billing_status(update=True)

			doc.set_status(update=True)
			doc.notify_update()

		# Update Sales Invoices
		for name in sales_invoices:
			doc = frappe.get_doc("Sales Invoice", name)
			doc.set_delivery_status(update=True)
			doc.validate_delivered_qty(from_doctype=self.doctype, row_names=sales_invoice_row_names)
			doc.set_status(update=True)
			doc.notify_update()

		# Update Returned Against Delivery Note
		if self.is_return and self.return_against:
			doc = frappe.get_doc("Delivery Note", self.return_against)
			doc.update_billing_status()
			doc.validate_returned_qty(from_doctype=self.doctype, row_names=delivery_note_row_names)
			doc.validate_billed_qty(from_doctype=self.doctype, row_names=delivery_note_row_names)

		self.update_project_billing_and_sales()

	def update_billing_status(self, update_modified=True):
		updated_delivery_notes = [self.name]

		for d in self.get("items"):
			# If Delivery Note is against Sales Invoice
			if d.sales_invoice_item:
				d.db_set('billed_qty', d.qty if self.docstatus == 1 else 0, update_modified=update_modified)
				d.db_set('billed_amt', d.amount if self.docstatus == 1 else 0, update_modified=update_modified)
			else:
				# If Delivery Note is against Sales Order but not a return
				if d.sales_order_item and not self.is_return:
					updated_delivery_notes += update_indirectly_billed_qty_for_dn_against_so(d.sales_order_item,
						update_modified=update_modified)
				else:
					update_directly_billed_qty_for_dn(self, d.name, update_modified=update_modified)

				d.load_from_db()

		for dn in set(updated_delivery_notes):
			dn_doc = self if (dn == self.name) else frappe.get_doc("Delivery Note", dn)
			dn_doc.set_billing_status(update=True, update_modified=update_modified)
			dn_doc.set_status(update=True)
			dn_doc.notify_update()

	def set_billing_status(self, update=False, update_modified=True):
		delivery_return_qty_map = self.get_delivery_return_qty_map()

		# update values in rows
		for d in self.items:
			if self.docstatus == 0:
				d.billed_qty = 0
				d.billed_amt = 0

			d.returned_qty = flt(delivery_return_qty_map.get(d.name))
			if update:
				d.db_set({
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

	def set_installation_status(self, update=False, update_modified=True):
		get_installed_qty_map = self.get_installed_qty_map()

		# update values in rows
		for d in self.items:
			d.installed_qty = flt(get_installed_qty_map.get(d.name))
			if update:
				d.db_set({
					'installed_qty': d.installed_qty,
				}, update_modified=update_modified)

		# update percentage in parent
		self.per_installed = self.calculate_status_percentage('installed_qty', 'qty', self.items)
		if self.per_installed is None:
			total_installed_qty = flt(sum([flt(d.installed_qty) for d in self.items]), self.precision('total_qty'))
			self.per_installed = 100 if total_installed_qty else 0

		# update installation_status
		self.installation_status = self.get_completion_status('per_installed', 'Installed')

		if update:
			self.db_set({
				'per_installed': self.per_installed,
				'installation_status': self.installation_status,
			}, update_modified=update_modified)

	def get_delivery_return_qty_map(self):
		delivery_return_qty_map = {}
		if self.docstatus == 1:
			row_names = [d.name for d in self.items]
			if row_names:
				delivery_return_qty_map = dict(frappe.db.sql("""
					select i.delivery_note_item, -1 * sum(i.qty)
					from `tabDelivery Note Item` i
					inner join `tabDelivery Note` p on p.name = i.parent
					where p.docstatus = 1 and p.is_return = 1 and p.reopen_order = 0 and i.delivery_note_item in %s
					group by i.delivery_note_item
				""", [row_names]))

		return delivery_return_qty_map

	def get_installed_qty_map(self):
		installled_qty_map = {}
		if self.docstatus == 1:
			row_names = [d.name for d in self.items]
			if row_names:
				installled_qty_map = dict(frappe.db.sql("""
					select i.prevdoc_detail_docname, sum(i.qty)
					from `tabInstallation Note Item` i
					inner join `tabInstallation Note` p on p.name = i.parent
					where p.docstatus = 1 and i.prevdoc_doctype = 'Delivery Note' and i.prevdoc_detail_docname in %s
					group by i.prevdoc_detail_docname
				""", [row_names]))

		return installled_qty_map

	def validate_returned_qty(self, from_doctype=None, row_names=None):
		self.validate_completed_qty('returned_qty', 'qty', self.items,
			allowance_type=None, from_doctype=from_doctype, row_names=row_names)

	def validate_billed_qty(self, from_doctype=None, row_names=None):
		self.validate_completed_qty(['billed_qty', 'returned_qty'], 'qty', self.items,
			allowance_type='billing', from_doctype=from_doctype, row_names=row_names)

		if frappe.get_cached_value("Accounts Settings", None, "validate_over_billing_in_sales_invoice"):
			self.validate_completed_qty('billed_amt', 'amount', self.items,
				allowance_type='billing', from_doctype=from_doctype, row_names=row_names)

	def validate_installed_qty(self, from_doctype=None, row_names=None):
		self.validate_completed_qty('installed_qty', 'qty', self.items,
			allowance_type=None, from_doctype=from_doctype, row_names=row_names)

	def update_status(self, status):
		self.set_status(update=True, status=status)
		self.update_project_billing_and_sales()
		self.notify_update()
		clear_doctype_notifications(self)

	def set_actual_qty(self):
		for d in self.get('items'):
			if d.item_code and d.warehouse:
				actual_qty = frappe.db.sql("""select actual_qty from `tabBin`
					where item_code = %s and warehouse = %s""", (d.item_code, d.warehouse))
				d.actual_qty = actual_qty and flt(actual_qty[0][0]) or 0

	def validate_order_required(self):
		"""check in manage account if sales order required or not"""
		so_required = frappe.get_cached_value("Selling Settings", None, 'so_required') == 'Yes'
		if self.get('transaction_type'):
			tt_so_required = frappe.get_cached_value('Transaction Type', self.get('transaction_type'), 'so_required')
			if tt_so_required:
				so_required = tt_so_required == 'Yes'

		if so_required:
			for d in self.get('items'):
				if not d.sales_order:
					frappe.throw(_("Sales Order required for Item {0}").format(d.item_code))

	def validate_with_previous_doc(self):
		super(DeliveryNote, self).validate_with_previous_doc({
			"Sales Order": {
				"ref_dn_field": "sales_order",
				"compare_fields": [["customer", "="], ["company", "="], ["project", "="], ["currency", "="]]
			},
			"Sales Order Item": {
				"ref_dn_field": "sales_order_item",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
			"Sales Invoice": {
				"ref_dn_field": "sales_invoice",
				"compare_fields": [["customer", "="], ["company", "="], ["project", "="], ["currency", "="]]
			},
			"Sales Invoice Item": {
				"ref_dn_field": "sales_invoice_item",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="], ["vehicle", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
			"Delivery Note Item": {
				"ref_dn_field": "delivery_note_item",
				"compare_fields": [["item_code", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
			"Quotation": {
				"ref_dn_field": "quotation",
				"compare_fields": [["company", "="]]
			},
		})

		if cint(frappe.get_cached_value('Selling Settings', None, 'maintain_same_sales_rate')) and not self.is_return:
			self.validate_rate_with_reference_doc([["Sales Order", "sales_order", "sales_order_item"],
				["Sales Invoice", "sales_invoice", "sales_invoice_item"]])

	def validate_warehouse(self):
		super(DeliveryNote, self).validate_warehouse()

		for d in self.get_item_list():
			if frappe.get_cached_value("Item", d['item_code'], "is_stock_item") == 1:
				if not d['warehouse']:
					frappe.throw(_("Warehouse required for stock Item {0}").format(d["item_code"]))

	def update_current_stock(self):
		if self.get("_action") and self._action != "update_after_submit":
			for d in self.get('items'):
				d.actual_qty = frappe.db.get_value("Bin", {"item_code": d.item_code,
					"warehouse": d.warehouse}, "actual_qty")

			for d in self.get('packed_items'):
				bin_qty = frappe.db.get_value("Bin", {"item_code": d.item_code,
					"warehouse": d.warehouse}, ["actual_qty", "projected_qty"], as_dict=True)
				if bin_qty:
					d.actual_qty = flt(bin_qty.actual_qty)
					d.projected_qty = flt(bin_qty.projected_qty)

	def check_credit_limit(self):
		from erpnext.selling.doctype.customer.customer import check_credit_limit

		extra_amount = 0
		validate_against_credit_limit = False
		bypass_credit_limit_check_at_sales_order = cint(frappe.db.get_value("Customer Credit Limit",
			filters={'parent': self.customer, 'parenttype': 'Customer', 'company': self.company},
			fieldname="bypass_credit_limit_check"))

		if bypass_credit_limit_check_at_sales_order:
			validate_against_credit_limit = True
			extra_amount = self.base_grand_total
		else:
			for d in self.get("items"):
				if not (d.sales_order or d.sales_invoice):
					validate_against_credit_limit = True
					break

		if validate_against_credit_limit:
			check_credit_limit(self.customer, self.company,
				bypass_credit_limit_check_at_sales_order, extra_amount)

	def validate_packed_qty(self):
		"""
			Validate that if packed qty exists, it should be equal to qty
		"""
		if not any([flt(d.get('packed_qty')) for d in self.get("items")]):
			return
		has_error = False
		for d in self.get("items"):
			if flt(d.get('qty')) != flt(d.get('packed_qty')):
				frappe.msgprint(_("Packed quantity must equal quantity for Item {0} in row {1}").format(d.item_code, d.idx))
				has_error = True
		if has_error:
			raise frappe.ValidationError

	def check_next_docstatus(self):
		submit_rv = frappe.db.sql("""select t1.name
			from `tabSales Invoice` t1,`tabSales Invoice Item` t2
			where t1.name = t2.parent and t2.delivery_note = %s and t1.docstatus = 1""",
			(self.name))
		if submit_rv:
			frappe.throw(_("Sales Invoice {0} has already been submitted").format(submit_rv[0][0]))

		submit_in = frappe.db.sql("""select t1.name
			from `tabInstallation Note` t1, `tabInstallation Note Item` t2
			where t1.name = t2.parent and t2.prevdoc_docname = %s and t1.docstatus = 1""",
			(self.name))
		if submit_in:
			frappe.throw(_("Installation Note {0} has already been submitted").format(submit_in[0][0]))

	def cancel_packing_slips(self):
		"""
			Cancel submitted packing slips related to this delivery note
		"""
		res = frappe.db.sql("""SELECT name FROM `tabPacking Slip` WHERE delivery_note = %s
			AND docstatus = 1""", self.name)

		if res:
			for r in res:
				ps = frappe.get_doc('Packing Slip', r[0])
				ps.cancel()
			frappe.msgprint(_("Packing Slip(s) cancelled"))


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Shipments'),
	})
	return list_context


def update_directly_billed_qty_for_dn(delivery_note, delivery_note_item, update_modified=True):
	if isinstance(delivery_note, string_types):
		is_delivery_return = frappe.db.get_value("Delivery Note", delivery_note, "is_return", cache=1)
	else:
		is_delivery_return = delivery_note.get('is_return')

	claim_customer = frappe.db.get_value("Delivery Note Item", delivery_note_item, "claim_customer")
	claim_customer_cond = ""
	if claim_customer:
		claim_customer_cond = " and (inv.bill_to = {0} or i.amount != 0)"\
			.format(frappe.db.escape(claim_customer))

	billed = frappe.db.sql("""
		select i.qty, i.amount, inv.is_return, inv.update_stock, inv.reopen_order, inv.depreciation_type
		from `tabSales Invoice Item` i
		inner join `tabSales Invoice` inv on inv.name = i.parent
		where i.delivery_note_item=%s and inv.docstatus = 1 {0}
	""".format(claim_customer_cond), delivery_note_item, as_dict=1)

	billed_qty, billed_amt = calculate_billed_qty_and_amount(billed, for_delivery_return=is_delivery_return)
	frappe.db.set_value("Delivery Note Item", delivery_note_item, {"billed_qty": billed_qty, "billed_amt": billed_amt},
		None, update_modified=update_modified)


def update_indirectly_billed_qty_for_dn_against_so(sales_order_item, update_modified=True):
	claim_customer = frappe.db.get_value("Sales Order Item", sales_order_item, "claim_customer")
	claim_customer_cond = ""
	if claim_customer:
		claim_customer_cond = " and (inv.bill_to = {0} or item.amount != 0)" \
			.format(frappe.db.escape(claim_customer))

	# Billed against Sales Order directly
	billed_against_so = frappe.db.sql("""
		select item.qty, item.amount, inv.is_return, inv.update_stock, inv.reopen_order, inv.depreciation_type
		from `tabSales Invoice Item` item, `tabSales Invoice` inv
		where inv.name = item.parent and inv.docstatus = 1
			and item.sales_order_item=%s and (item.delivery_note_item is null or item.delivery_note_item = '') {0}
	""".format(claim_customer_cond), sales_order_item, as_dict=1)

	billed_qty_against_so, billed_amt_against_so = calculate_billed_qty_and_amount(billed_against_so)

	# Get all Delivery Note Item rows against the Sales Order Item row
	dn_details = frappe.db.sql("""
		select dn_item.name, dn_item.amount, dn_item.qty, dn_item.returned_qty,
			dn_item.sales_invoice_item, dn_item.parent
		from `tabDelivery Note Item` dn_item, `tabDelivery Note` dn
		where dn.name = dn_item.parent and dn_item.sales_order_item = %s and ifnull(dn_item.sales_invoice_item, '') = ''
			and dn.docstatus = 1 and dn.is_return = 0
		order by dn_item.billed_qty, dn.posting_date, dn.posting_time, dn.creation
	""", sales_order_item, as_dict=1)

	updated_dn = []
	for dnd in dn_details:
		billed_qty_against_dn = 0
		billed_amt_against_dn = 0

		# If delivered against Sales Invoice
		if dnd.sales_invoice_item:
			billed_qty_against_dn = flt(dnd.qty)
			billed_amt_against_dn = flt(dnd.amount)
			billed_qty_against_so -= billed_qty_against_dn
			billed_amt_against_so -= billed_amt_against_dn
		else:
			# Get billed qty directly against Delivery Note
			billed_against_dn = frappe.db.sql("""
				select item.qty, item.amount, inv.is_return, inv.update_stock, inv.reopen_order, inv.depreciation_type
				from `tabSales Invoice Item` item, `tabSales Invoice` inv
				where inv.name=item.parent and item.delivery_note_item=%s and item.docstatus=1 {0}
			""".format(claim_customer_cond), dnd.name, as_dict=1)

			billed_qty_against_dn, billed_amt_against_dn = calculate_billed_qty_and_amount(billed_against_dn)

		# Distribute billed qty and amt directly against SO between DNs based on FIFO
		pending_qty_to_bill = flt(dnd.qty) - flt(dnd.returned_qty) - billed_qty_against_dn
		if billed_qty_against_so and pending_qty_to_bill > 0:
			billed_qty_against_dn += min(billed_qty_against_so, pending_qty_to_bill)
			billed_qty_against_so -= min(billed_qty_against_so, pending_qty_to_bill)

		pending_amt_to_bill = flt(dnd.amount) - billed_amt_against_dn
		pending_amt_to_bill -= flt(dnd.amount) / flt(dnd.qty) * flt(dnd.returned_qty) if dnd.qty else 0
		if billed_amt_against_so and pending_amt_to_bill > 0:
			billed_amt_against_dn += min(billed_amt_against_so, pending_amt_to_bill)
			billed_amt_against_so -= min(billed_amt_against_so, pending_amt_to_bill)

		frappe.db.set_value("Delivery Note Item", dnd.name, {
			"billed_qty": billed_qty_against_dn, "billed_amt": billed_amt_against_dn
		}, None, update_modified=update_modified)

		updated_dn.append(dnd.parent)

	return updated_dn


def calculate_billed_qty_and_amount(billed_data, for_delivery_return=False):
	billed_qty = 0
	billed_amt = 0

	depreciation_types = set()

	for d in billed_data:
		if for_delivery_return or not d.is_return or (d.reopen_order and not d.update_stock):
			billed_amt += d.amount

			depreciation_types.add(d.depreciation_type or 'No Depreciation')
			if d.depreciation_type != 'Depreciation Amount Only':
				billed_qty += d.qty

	if 'No Depreciation' not in depreciation_types:
		has_depreciation_amount = 'Depreciation Amount Only' in depreciation_types
		has_after_depreciation_amount = 'After Depreciation Amount' in depreciation_types
		if not has_depreciation_amount or not has_after_depreciation_amount:
			billed_qty = 0

	return billed_qty, billed_amt


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, only_items=None, skip_postprocess=False):
	if frappe.flags.args and only_items is None:
		only_items = cint(frappe.flags.args.only_items)

	def get_pending_qty(source_doc):
		return source_doc.qty - source_doc.billed_qty - source_doc.returned_qty

	def item_condition(source, source_parent, target_parent):
		if source.name in [d.delivery_note_item for d in target_parent.get('items') if d.delivery_note_item]:
			return False

		if cint(target_parent.get('claim_billing')):
			bill_to = target_parent.get('bill_to') or target_parent.get('customer')
			if bill_to:
				if source.claim_customer != bill_to:
					return False
			else:
				if not source.claim_customer:
					return False

		if source_parent.get('is_return'):
			return get_pending_qty(source) <= 0
		else:
			return get_pending_qty(source) > 0

	def update_item(source, target, source_parent, target_parent):
		target.project = source_parent.get('project')
		target.qty = get_pending_qty(source)
		target.delivered_qty = source.qty
		target.depreciation_percentage = None

		if target_parent:
			target_parent.set_rate_zero_for_claim_item(source, target)

		if source.serial_no and source_parent.per_billed > 0:
			target.serial_no = get_delivery_note_serial_no(source.item_code,
				target.qty, source_parent.name)

	def postprocess(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

	mapping = {
		"Delivery Note": {
			"doctype": "Sales Invoice",
			"field_map": {
				"is_return": "is_return",
				"remarks": "remarks",
				"vehicle_booking_order": "vehicle_booking_order",
			},
			"field_no_map": [
				"has_stin",
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Delivery Note Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"name": "delivery_note_item",
				"parent": "delivery_note",
				"sales_order": "sales_order",
				"sales_order_item": "sales_order_item",
				"quotation": "quotation",
				"quotation_item": "quotation_item",
				"serial_no": "serial_no",
				"vehicle": "vehicle",
				"cost_center": "cost_center"
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
			"field_map": {
				"incentives": "incentives"
			},
			"add_if_empty": True
		}
	}

	if only_items:
		mapping = {dt: dt_mapping for dt, dt_mapping in mapping.items() if dt == "Delivery Note Item"}

	doc = get_mapped_doc("Delivery Note", source_name, mapping, target_doc,
		postprocess=postprocess if not skip_postprocess else None,
		explicit_child_tables=only_items)

	return doc


@frappe.whitelist()
def make_inter_company_purchase_receipt(source_name, target_doc=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_transaction
	return make_inter_company_transaction("Delivery Note", source_name, target_doc)


@frappe.whitelist()
def make_delivery_trip(source_name, target_doc=None):
	def update_stop_details(source_doc, target_doc, source_parent, target_parent):
		target_doc.customer = source_parent.customer
		target_doc.address = source_parent.shipping_address_name
		target_doc.customer_address = source_parent.shipping_address
		target_doc.contact = source_parent.contact_person
		target_doc.customer_contact = source_parent.contact_display
		target_doc.grand_total = source_parent.grand_total

		# Append unique Delivery Notes in Delivery Trip
		delivery_notes.append(target_doc.delivery_note)

	delivery_notes = []

	doclist = get_mapped_doc("Delivery Note", source_name, {
		"Delivery Note": {
			"doctype": "Delivery Trip",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Delivery Note Item": {
			"doctype": "Delivery Stop",
			"field_map": {
				"parent": "delivery_note"
			},
			"condition": lambda item, source, target: item.parent not in delivery_notes,
			"postprocess": update_stop_details
		}
	}, target_doc)

	return doclist


@frappe.whitelist()
def make_installation_note(source_name, target_doc=None):
	def update_item(obj, target, source_parent, target_parent):
		target.qty = flt(obj.qty) - flt(obj.installed_qty)
		target.serial_no = obj.serial_no

	doclist = get_mapped_doc("Delivery Note", source_name, 	{
		"Delivery Note": {
			"doctype": "Installation Note",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Delivery Note Item": {
			"doctype": "Installation Note Item",
			"field_map": {
				"name": "prevdoc_detail_docname",
				"parent": "prevdoc_docname",
				"parenttype": "prevdoc_doctype",
			},
			"postprocess": update_item,
			"condition": lambda doc, source, target: doc.installed_qty < doc.qty
		}
	}, target_doc)

	return doclist


@frappe.whitelist()
def make_packing_slip(source_name, target_doc=None):
	doclist = get_mapped_doc("Delivery Note", source_name, 	{
		"Delivery Note": {
			"doctype": "Packing Slip",
			"field_map": {
				"name": "delivery_note",
				"letter_head": "letter_head"
			},
			"validation": {
				"docstatus": ["=", 0]
			}
		}
	}, target_doc)

	return doclist


@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc
	return make_return_doc("Delivery Note", source_name, target_doc)


@frappe.whitelist()
def update_delivery_note_status(docname, status):
	dn = frappe.get_doc("Delivery Note", docname)
	dn.update_status(status)
