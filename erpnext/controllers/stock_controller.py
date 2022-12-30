# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, erpnext
from frappe.utils import cint, flt, cstr
from frappe import _
import frappe.defaults
from erpnext.accounts.utils import get_fiscal_year
from erpnext.accounts.general_ledger import make_gl_entries, delete_gl_entries, process_gl_map, delete_voucher_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.stock.stock_ledger import get_valuation_rate
from erpnext.stock import get_warehouse_account_map
from frappe.model.meta import get_field_precision
import json
from six import string_types


class QualityInspectionRequiredError(frappe.ValidationError): pass
class QualityInspectionRejectedError(frappe.ValidationError): pass
class QualityInspectionNotSubmittedError(frappe.ValidationError): pass


class StockController(AccountsController):
	def validate(self):
		super(StockController, self).validate()
		if not self.get('is_return'):
			self.validate_inspection()
		self.validate_serialized_batch()
		self.validate_customer_provided_item()
		self.validate_vehicle_item()

	def make_gl_entries(self, gl_entries=None, repost_future_gle=True, from_repost=False):
		if self.docstatus == 2:
			delete_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

		if cint(erpnext.is_perpetual_inventory_enabled(self.company)):
			if self.docstatus == 1:
				if not gl_entries:
					gl_entries = self.get_gl_entries()
				make_gl_entries(gl_entries, from_repost=from_repost)

			if (repost_future_gle or self.flags.repost_future_gle):
				update_gl_entries_for_reposted_stock_vouchers((self.doctype, self.name))

		elif self.doctype in ['Purchase Receipt', 'Purchase Invoice'] and self.docstatus == 1:
			gl_entries = []
			gl_entries = self.get_asset_gl_entry(gl_entries)
			make_gl_entries(gl_entries, from_repost=from_repost)

	def validate_serialized_batch(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
		for d in self.get("items"):
			if not (hasattr(d, 'serial_no') and d.serial_no and d.batch_no): continue

			serial_nos = get_serial_nos(d.serial_no)
			for serial_no_data in frappe.get_all("Serial No",
				filters={"name": ("in", serial_nos)}, fields=["batch_no", "name"]):
				if serial_no_data.batch_no != d.batch_no:
					frappe.throw(_("Row #{0}: Serial No {1} does not belong to Batch {2}")
						.format(d.idx, serial_no_data.name, d.batch_no))

	def get_gl_entries(self):
		warehouse_account = get_warehouse_account_map(self.company)
		sle_map = self.get_stock_ledger_entry_map()
		voucher_items = self.get_stock_voucher_items(sle_map)

		gl_list = []
		warehouse_with_no_account = []

		precision = frappe.get_precision("GL Entry", "debit")
		for item_row in voucher_items:
			sle_list = sle_map.get((item_row.item_code, item_row.name))
			if sle_list:
				for sle in sle_list:
					if warehouse_account.get(sle.warehouse):
						# from warehouse account

						self.check_expense_account(item_row)

						gl_list.append(self.get_gl_dict({
							"account": warehouse_account[sle.warehouse]["account"],
							"against": item_row.expense_account,
							"cost_center": item_row.get('cost_center') or self.get("cost_center"),
							"project": item_row.get("project") or self.get("project"),
							"remarks": self.get("remarks") or "Accounting Entry for Stock",
							"debit": flt(sle.stock_value_difference, precision),
							"is_opening": item_row.get("is_opening") or self.get("is_opening") or "No",
						}, warehouse_account[sle.warehouse]["account_currency"], item=item_row))

						# to target warehouse / expense account
						gl_list.append(self.get_gl_dict({
							"account": item_row.expense_account,
							"against": warehouse_account[sle.warehouse]["account"],
							"cost_center": item_row.get('cost_center') or self.get("cost_center"),
							"remarks": self.get("remarks") or "Accounting Entry for Stock",
							"credit": flt(sle.stock_value_difference, precision),
							"project": item_row.get("project") or self.get("project"),
							"is_opening": item_row.get("is_opening") or self.get("is_opening") or "No"
						}, item=item_row))
					elif sle.warehouse not in warehouse_with_no_account:
						warehouse_with_no_account.append(sle.warehouse)

		if warehouse_with_no_account:
			for wh in warehouse_with_no_account:
				if frappe.db.get_value("Warehouse", wh, "company"):
					frappe.throw(_("Warehouse {0} is not linked to any account, "
						"please mention the account in the warehouse record or "
						"set default inventory account in company {1}.").format(wh, self.company))

		return process_gl_map(gl_list)

	def update_stock_ledger_entries(self, sle):
		sle.valuation_rate = get_valuation_rate(sle.item_code, sle.warehouse,
			self.doctype, self.name, sle.batch_no, currency=self.company_currency, company=self.company)

		sle.stock_value = flt(sle.qty_after_transaction) * flt(sle.valuation_rate)
		sle.stock_value_difference = flt(sle.actual_qty) * flt(sle.valuation_rate)

		incoming_rate_field = ""
		if flt(sle.actual_qty) > 0:
			sle.incoming_rate = sle.valuation_rate
			incoming_rate_field = ", incoming_rate = %(incoming_rate)s"

		if sle.name:
			frappe.db.sql("""
				update
					`tabStock Ledger Entry`
				set
					stock_value = %(stock_value)s,
					valuation_rate = %(valuation_rate)s,
					stock_value_difference = %(stock_value_difference)s
					{0}
				where
					name = %(name)s
			""".format(incoming_rate_field), sle)  # nosec

		return sle

	def get_stock_voucher_items(self, sle_map):
		return self.get("items")

	def get_stock_ledger_entry_map(self):
		stock_ledger = {}
		stock_ledger_entries = frappe.db.sql("""
			select
				name, voucher_detail_no, item_code, warehouse,
				posting_date, posting_time,
				stock_value_difference, valuation_rate, actual_qty, qty_after_transaction
			from `tabStock Ledger Entry`
			where voucher_type=%s and voucher_no=%s
		""", (self.doctype, self.name), as_dict=True)

		for sle in stock_ledger_entries:
			stock_ledger.setdefault((sle.item_code, sle.voucher_detail_no), []).append(sle)

		return stock_ledger

	def make_batches(self, warehouse_field):
		'''Create batches if required. Called before submit'''
		for d in self.items:
			if d.get(warehouse_field) and not d.batch_no:
				has_batch_no, create_new_batch = frappe.db.get_value('Item', d.item_code, ['has_batch_no', 'create_new_batch'])
				if has_batch_no and create_new_batch:
					d.batch_no = frappe.get_doc(dict(
						doctype='Batch',
						item=d.item_code,
						supplier=getattr(self, 'supplier', None),
						reference_doctype=self.doctype,
						reference_name=self.name)).insert().name

	def check_expense_account(self, item):
		if not item.get("expense_account"):
			frappe.throw(_("Row #{0}: Expense Account not set for Item {1}. Please set an Expense \
				Account in the Items table").format(item.idx, frappe.bold(item.item_code)),
				title=_("Expense Account Missing"))

		else:
			is_expense_account = frappe.db.get_value("Account", item.expense_account, "report_type", cache=1) == "Profit and Loss"
			if self.doctype not in ("Purchase Receipt", "Purchase Invoice", "Stock Reconciliation", "Stock Entry") and not is_expense_account:
				override_validation = not self.get('transaction_type') or cint(frappe.get_cached_value("Transaction Type",
					self.get('transaction_type'), 'allow_non_profit_and_loss_expense_account'))

				if not override_validation:
					frappe.throw(_("Expense / Difference account ({0}) must be a 'Profit or Loss' account")
						.format(item.get("expense_account")))

			if is_expense_account and not item.get("cost_center") and not self.get("cost_center"):
				frappe.throw(_("{0} {1}: Cost Center is mandatory for Item {2}").format(
					_(self.doctype), self.name, item.get("item_code")))

	def delete_auto_created_batches(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
		for d in self.items:
			if not d.batch_no: continue

			serial_nos = get_serial_nos(d.serial_no)
			if serial_nos:
				frappe.db.set_value("Serial No", { 'name': ['in', serial_nos] }, "batch_no", None)

			d.batch_no = None
			d.db_set("batch_no", None)

		for data in frappe.get_all("Batch",
			{'reference_name': self.name, 'reference_doctype': self.doctype}):
			frappe.delete_doc("Batch", data.name)

	def get_sl_entries(self, d, args):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		sl_dict = frappe._dict({
			"item_code": d.get("item_code", None),
			"warehouse": d.get("warehouse", None),
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			'fiscal_year': get_fiscal_year(self.posting_date, company=self.company)[0],
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"voucher_detail_no": d.name,
			"actual_qty": (self.docstatus==1 and 1 or -1)*flt(d.get("stock_qty")),
			"stock_uom": frappe.db.get_value("Item", args.get("item_code") or d.get("item_code"), "stock_uom"),
			"incoming_rate": 0,
			"company": self.company,
			"batch_no": cstr(d.get("batch_no")).strip(),
			"serial_no": '\n'.join(get_serial_nos(d.get("serial_no"))),
			"project": d.get("project") or self.get('project'),
			"is_cancelled": self.docstatus==2 and "Yes" or "No"
		})

		if self.get("customer"):
			sl_dict.update({
				"party_type": "Customer",
				"party": self.get("customer")
			})
		elif self.get("supplier"):
			sl_dict.update({
				"party_type": "Supplier",
				"party": self.get("supplier")
			})
		elif self.get("party_type") and self.get("party"):
			sl_dict.update({
				"party_type": self.get("party_type"),
				"party": self.get("party")
			})

		sl_dict.update(args)
		return sl_dict

	def make_sl_entries(self, sl_entries, is_amended=None, allow_negative_stock=False,
			via_landed_cost_voucher=False):
		from erpnext.stock.stock_ledger import make_sl_entries
		make_sl_entries(sl_entries, is_amended, allow_negative_stock, via_landed_cost_voucher)

	def make_gl_entries_on_cancel(self, repost_future_gle=True):
		if frappe.db.sql("""select name from `tabGL Entry` where voucher_type=%s
			and voucher_no=%s""", (self.doctype, self.name)):
				self.make_gl_entries(repost_future_gle=repost_future_gle)

	def get_serialized_items(self):
		serialized_items = []
		item_codes = list(set([d.item_code for d in self.get("items")]))
		if item_codes:
			serialized_items = frappe.db.sql_list("""select name from `tabItem`
				where has_serial_no=1 and name in ({})""".format(", ".join(["%s"]*len(item_codes))),
				tuple(item_codes))

		return serialized_items

	def get_incoming_rate_for_sales_return(self, item_code=None, warehouse=None, batch_no=None, voucher_detail_no=None,
			against_document_type=None, against_document=None):
		incoming_rate = 0.0

		if against_document_type and against_document and voucher_detail_no:
			incoming_rate = frappe.db.sql("""
				select abs(stock_value_difference / actual_qty)
				from `tabStock Ledger Entry`
				where voucher_type = %s and voucher_no = %s
					and voucher_detail_no = %s limit 1
			""", (against_document_type, against_document, voucher_detail_no))
			incoming_rate = incoming_rate[0][0] if incoming_rate else 0.0
		elif against_document_type and against_document and item_code:
			incoming_rate = frappe.db.sql("""
				select abs(sum(stock_value_difference) / sum(actual_qty))
				from `tabStock Ledger Entry`
				where voucher_type = %s and voucher_no = %s
					and item_code = %s limit 1
			""", (against_document_type, against_document, item_code))
			incoming_rate = incoming_rate[0][0] if incoming_rate else 0.0
		elif item_code and warehouse:
			incoming_rate = get_valuation_rate(item_code, warehouse,
				self.doctype, self.name, batch_no, company=self.company, currency=self.currency)

		return incoming_rate

	def validate_warehouse(self):
		from erpnext.stock.utils import validate_warehouse_company

		warehouses = list(set([d.warehouse for d in
			self.get("items") if getattr(d, "warehouse", None)]))

		for w in warehouses:
			validate_warehouse_company(w, self.company)

	def validate_inspection(self):
		'''Checks if quality inspection is set for Items that require inspection.
		On submit, throw an exception'''
		inspection_required_fieldname = None
		if self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
			inspection_required_fieldname = "inspection_required_before_purchase"
		elif self.doctype in ["Delivery Note", "Sales Invoice"]:
			inspection_required_fieldname = "inspection_required_before_delivery"

		if ((not inspection_required_fieldname and self.doctype != "Stock Entry") or
			(self.doctype == "Stock Entry" and not self.inspection_required) or
			(self.doctype in ["Sales Invoice", "Purchase Invoice"] and not self.update_stock)):
				return

		for d in self.get('items'):
			qa_required = False
			if (inspection_required_fieldname and not d.quality_inspection and
				frappe.db.get_value("Item", d.item_code, inspection_required_fieldname)):
				qa_required = True
			elif self.doctype == "Stock Entry" and not d.quality_inspection and d.t_warehouse:
				qa_required = True
			if self.docstatus == 1 and d.quality_inspection:
				qa_doc = frappe.get_doc("Quality Inspection", d.quality_inspection)
				if qa_doc.docstatus == 0:
					link = frappe.utils.get_link_to_form('Quality Inspection', d.quality_inspection)
					frappe.throw(_("Quality Inspection: {0} is not submitted for the item: {1} in row {2}").format(link, d.item_code, d.idx), QualityInspectionNotSubmittedError)

				qa_failed = any([r.status=="Rejected" for r in qa_doc.readings])
				if qa_failed:
					frappe.throw(_("Row {0}: Quality Inspection rejected for item {1}")
						.format(d.idx, d.item_code), QualityInspectionRejectedError)
			elif qa_required :
				action = frappe.get_doc('Stock Settings').action_if_quality_inspection_is_not_submitted
				if self.docstatus==1 and action == 'Stop':
					frappe.throw(_("Quality Inspection required for Item {0} to submit").format(frappe.bold(d.item_code)),
						exc=QualityInspectionRequiredError)
				else:
					frappe.msgprint(_("Create Quality Inspection for Item {0}").format(frappe.bold(d.item_code)))

	def update_blanket_order(self):
		blanket_orders = list(set([d.blanket_order for d in self.items if d.blanket_order]))
		for blanket_order in blanket_orders:
			frappe.get_doc("Blanket Order", blanket_order).update_ordered_qty()

	def validate_customer_provided_item(self):
		for d in self.get('items'):
			# Customer Provided parts will have zero valuation rate
			if d.item_code and frappe.get_cached_value('Item', d.item_code, 'is_customer_provided_item'):
				d.allow_zero_valuation_rate = 1

	def validate_vehicle_item(self):
		for d in self.get('items'):
			if not d.get('is_vehicle') and d.get('vehicle'):
				d.vehicle = ''

			if d.get('is_vehicle'):
				is_receipt = (self.doctype == "Purchase Receipt"
					or (self.doctype == "Purchase Invoice" and self.update_stock)
					or (self.doctype == "Stock Entry" and d.get('t_warehouse') and not d.get('s_warehouse')))
				if d.meta.has_field('vehicle') and not d.get('vehicle') and not is_receipt:
					frappe.throw(_("Row #{0}: Vehicle must be set for Vehicle Item {1}").format(d.idx, d.item_code))

				if d.qty > 1 and d.get('vehicle'):
					frappe.throw(_("Row #{0}: Qty for Vehicle Item {1} ({2}) can not be greater than 1. "
						"Please split rows instead of increasing qty").format(d.idx, d.item_code, d.vehicle))

				if d.meta.has_field('serial_no'):
					d.serial_no = d.vehicle


def update_gl_entries_for_reposted_stock_vouchers(excluded_vouchers=None, only_if_value_changed=True):
	if frappe.flags.stock_ledger_vouchers_reposted:
		stock_ledger_vouchers_reposted_sorted = sorted(frappe.flags.stock_ledger_vouchers_reposted,
			key=lambda d: (d.posting_date, d.posting_time))
		vouchers = [(d.voucher_type, d.voucher_no) for d in stock_ledger_vouchers_reposted_sorted]

		if only_if_value_changed:
			vouchers = [d for d in vouchers if d in frappe.flags.stock_ledger_vouchers_value_changed]

		update_gl_entries_for_stock_voucher(vouchers, excluded_vouchers=excluded_vouchers)


def update_gl_entries_after(posting_date, posting_time, for_warehouses=None, for_items=None, item_warehouse_list=None):
	future_stock_vouchers = get_future_stock_vouchers(posting_date, posting_time,
		for_warehouses, for_items, item_warehouse_list)
	update_gl_entries_for_stock_voucher(future_stock_vouchers)


def update_gl_entries_for_stock_voucher(stock_vouchers, excluded_vouchers=None):
	gle = get_voucherwise_gl_entries(stock_vouchers)

	if excluded_vouchers and isinstance(excluded_vouchers, tuple):
		excluded_vouchers = [excluded_vouchers]

	for voucher_type, voucher_no in stock_vouchers:
		if excluded_vouchers and (voucher_type, voucher_no) in excluded_vouchers:
			continue

		existing_gle = gle.get((voucher_type, voucher_no), [])
		voucher_obj = frappe.get_doc(voucher_type, voucher_no)
		expected_gle = voucher_obj.get_gl_entries()
		if expected_gle:
			if not existing_gle or not compare_existing_and_expected_gle(existing_gle, expected_gle):
				delete_voucher_gl_entries(voucher_type, voucher_no)
				voucher_obj.make_gl_entries(gl_entries=expected_gle, repost_future_gle=False, from_repost=True)
		else:
			delete_voucher_gl_entries(voucher_type, voucher_no)


def compare_existing_and_expected_gle(existing_gle, expected_gle):
	key_fields = ('account', 'cost_center', 'party_type', 'party')
	precision = frappe.get_precision("GL Entry", "debit")

	existing_gle_map = {}
	expected_gle_map = {}

	for entry in existing_gle:
		key = tuple(cstr(entry.get(k)) for k in key_fields)
		existing_gle_map.setdefault(key, 0)
		existing_gle_map[key] += flt(entry.debit) - flt(entry.credit)

	for entry in expected_gle:
		key = tuple(cstr(entry.get(k)) for k in key_fields)
		expected_gle_map.setdefault(key, 0)
		expected_gle_map[key] += flt(entry.debit) - flt(entry.credit)

	for k, v in existing_gle_map.items():
		existing_gle_map[k] = flt(v, precision)
	for k, v in expected_gle_map.items():
		expected_gle_map[k] = flt(v, precision)

	return existing_gle_map == expected_gle_map


def get_future_stock_vouchers(posting_date, posting_time, for_warehouses=None, for_items=None, item_warehouse_list=None):
	future_stock_vouchers = []

	condition = ""
	if for_items:
		condition += " and item_code in %(item_codes)s"

	if for_warehouses:
		condition += " and warehouse in %(warehouses)s"

	if item_warehouse_list:
		condition += " and (item_code, warehouse) in %(item_warehouse_list)s"

	sle_vouchers = frappe.db.sql("""
		select distinct sle.voucher_type, sle.voucher_no
		from `tabStock Ledger Entry` sle
		where timestamp(sle.posting_date, sle.posting_time) >= timestamp(%(posting_date)s, %(posting_time)s)
		{condition}
		order by timestamp(sle.posting_date, sle.posting_time) asc, creation asc
		for update
	""".format(condition=condition), {
		"posting_date": posting_date,
		"posting_time": posting_time,
		"item_codes": for_items,
		"warehouses": for_items,
		"item_warehouse_list": item_warehouse_list
	}, as_dict=True)

	for d in sle_vouchers:
		future_stock_vouchers.append((d.voucher_type, d.voucher_no))

	return future_stock_vouchers


def get_voucherwise_gl_entries(stock_vouchers):
	voucherwise_gl = {}
	if stock_vouchers:
		gl_entries = frappe.db.sql("""
			select * from `tabGL Entry`
			where (voucher_type, voucher_no) in %s
			for update
		""", [stock_vouchers], as_dict=1)

		for d in gl_entries:
			voucherwise_gl.setdefault((d.voucher_type, d.voucher_no), []).append(d)

	return voucherwise_gl


@frappe.whitelist()
def update_item_qty_from_availability(items):
	if isinstance(items, string_types):
		items = json.loads(items)

	out = {}
	actual_qty_map = {}
	for d in items:
		d = frappe._dict(d)
		if d.item_code and d.warehouse:
			if (d.item_code, d.warehouse) not in actual_qty_map:
				actual_qty = frappe.db.sql("""select actual_qty from `tabBin`
					where item_code = %s and warehouse = %s""", (d.item_code, d.warehouse))
				actual_qty = actual_qty and flt(actual_qty[0][0]) or 0
				actual_qty_map[(d.item_code, d.warehouse)] = actual_qty
				out.setdefault(d.name, frappe._dict()).actual_qty = actual_qty
			else:
				out.setdefault(d.name, frappe._dict()).actual_qty = actual_qty_map[(d.item_code, d.warehouse)]

	for d in items:
		d = frappe._dict(d)
		if d.item_code and d.warehouse:
			remaining_qty = actual_qty_map[(d.item_code, d.warehouse)]
			if flt(d.stock_qty) > remaining_qty:
				out[d.name].qty = flt(remaining_qty / flt(d.conversion_factor),
					get_field_precision(frappe.get_meta("Delivery Note Item").get_field("qty")))
				actual_qty_map[(d.item_code, d.warehouse)] = 0
			else:
				actual_qty_map[(d.item_code, d.warehouse)] -= flt(d.stock_qty)

	return out
