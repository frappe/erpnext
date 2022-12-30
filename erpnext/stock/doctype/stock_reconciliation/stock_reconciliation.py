# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, erpnext
import frappe.defaults
from frappe import msgprint, _
from frappe.utils import cstr, flt, cint, get_datetime
from erpnext.stock.doctype.batch.batch import get_batches, get_batch_received_date
from erpnext.controllers.stock_controller import StockController
from erpnext.accounts.utils import get_company_default
from erpnext.stock.utils import get_stock_balance, get_incoming_rate
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos, validate_serial_no_ledger
from erpnext.stock.doctype.batch.batch import get_batch_qty_on
from erpnext.stock.get_item_details import get_default_cost_center, get_conversion_factor, get_default_warehouse
from frappe.model.meta import get_field_precision
import json
from six import string_types


class OpeningEntryAccountError(frappe.ValidationError): pass
class EmptyStockReconciliationItemsError(frappe.ValidationError): pass


class StockReconciliation(StockController):
	def __init__(self, *args, **kwargs):
		super(StockReconciliation, self).__init__(*args, **kwargs)
		self.head_row = ["Item Code", "Warehouse", "Quantity", "Valuation Rate"]

	def validate(self):
		if not self.expense_account:
			self.expense_account = get_difference_account(self.purpose, self.company)
		if not self.cost_center:
			self.cost_center = frappe.get_cached_value('Company',  self.company,  "cost_center")

		self.validate_posting_time()

		self.set_loose_qty()
		self.update_current_qty_valuation_rate()

		if self._action == "submit":
			self.remove_items_with_no_change()

		self.validate_data()
		self.validate_expense_account()
		self.set_total_qty_and_amount()

	def on_submit(self):
		self.update_stock_ledger()
		self.make_gl_entries()

		from erpnext.stock.doctype.serial_no.serial_no import update_serial_nos_after_submit
		update_serial_nos_after_submit(self, "items")

	def on_cancel(self):
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()

	@frappe.whitelist()
	def update_item_details(self):
		self.validate_posting_time()
		self.set_loose_qty()
		self.update_current_qty_valuation_rate()
		self.set_total_qty_and_amount()

	def set_loose_qty(self):
		for item in self.items:
			if item.item_code:
				if not item.loose_uom:
					item.loose_qty = 0
					item.conversion_factor = 1
				elif item.loose_uom == item.stock_uom:
					item.conversion_factor = 1
				elif not flt(item.conversion_factor):
					item.conversion_factor = get_conversion_factor(item.item_code, item.loose_uom)["conversion_factor"]

				item.stock_loose_qty = flt(item.loose_qty) * flt(item.conversion_factor)
				item.total_qty = flt(flt(item.qty) + item.stock_loose_qty, item.precision("total_qty"))

	def update_current_qty_valuation_rate(self):
		for item in self.items:
			if not item.item_code:
				continue

			qty, rate, amount, serial_nos = get_stock_balance_for(item.item_code, item.warehouse,
				self.posting_date, self.posting_time, item.batch_no)

			item.current_qty = qty
			item.current_valuation_rate = rate
			item.current_amount = amount
			item.current_serial_no = serial_nos

			if not cint(self.reset_rate):
				item.valuation_rate = item.current_valuation_rate

	def remove_items_with_no_change(self):
		"""Remove items if qty or rate is not changed"""
		def _changed(item):
			qty_unchanged = (item.qty is None and item.loose_qty is None) or item.total_qty == item.current_qty
			valuation_unchanged = item.valuation_rate is None or item.valuation_rate == item.current_valuation_rate
			serial_no_unchanged = not item.serial_no or (item.serial_no == item.current_serial_no)

			if qty_unchanged and valuation_unchanged and serial_no_unchanged:
				return False
			else:
				# set default as current rates
				if item.qty is None and item.loose_qty is None:
					item.qty = item.current_qty
					item.loose_qty = 0

				return True

		items = list(filter(lambda d: _changed(d), self.items))

		if not items:
			frappe.throw(_("None of the items have any change in quantity or value."),
				EmptyStockReconciliationItemsError)

		elif len(items) != len(self.items):
			self.items = items
			for i, item in enumerate(self.items):
				item.idx = i + 1

	def validate_data(self):
		def _get_msg(row_num, msg):
			return _("Row # {0}: ").format(row_num+1) + msg

		self.validation_messages = []
		unique_combinations = []

		default_currency = frappe.db.get_default("currency")

		for row_num, row in enumerate(self.items):
			key = (row.item_code, row.warehouse, cstr(row.batch_no))
			# find duplicates
			if key in unique_combinations:
				self.validation_messages.append(_get_msg(row_num, _("Duplicate entry")))
			else:
				unique_combinations.append(key)

			self.validate_item(row.item_code, row)

			# validate warehouse
			if not frappe.db.get_value("Warehouse", row.warehouse):
				self.validation_messages.append(_get_msg(row_num, _("Warehouse not found in the system")))

			# if both not specified
			if row.total_qty in ["", None] and row.valuation_rate in ["", None]:
				self.validation_messages.append(_get_msg(row_num,
					_("Please specify either Quantity or Valuation Rate or both")))

			# do not allow negative quantity
			if flt(row.total_qty) < 0:
				self.validation_messages.append(_get_msg(row_num,
					_("Negative Quantity is not allowed")))

			# serial nos qty validation
			if row.serial_no and len(get_serial_nos(row.serial_no)) != row.total_qty:
				self.validation_messages.append(_get_msg(row_num,
					_("Quantity and number of Serial Nos do not match")))

			# do not allow negative valuation
			if flt(row.valuation_rate) < 0:
				self.validation_messages.append(_get_msg(row_num,
					_("Negative Valuation Rate is not allowed")))

		# throw all validation messages
		if self.validation_messages:
			for msg in self.validation_messages:
				msgprint(msg)

			raise frappe.ValidationError(self.validation_messages)

	def validate_item(self, item_code, row):
		from erpnext.stock.doctype.item.item import validate_end_of_life, \
			validate_is_stock_item, validate_cancelled_item

		# using try except to catch all validation msgs and display together

		try:
			item = frappe.get_cached_doc("Item", item_code)

			# end of life and stock item
			validate_end_of_life(item_code, item.end_of_life, item.disabled, verbose=0)
			validate_is_stock_item(item_code, item.is_stock_item, verbose=0)

			# serialized item
			if row.serial_no and not item.has_serial_no:
				raise frappe.ValidationError(_("Serial No(s) is not required for item {0}").format(item_code))

			if self._action == "submit":
				if item.has_serial_no and not row.serial_no and not item.serial_no_series and flt(row.qty) > 0:
					raise frappe.ValidationError(_("Serial No(s) required for serialized item {0}").format(item_code))

			# batch item
			if row.batch_no and not item.has_batch_no:
				raise frappe.ValidationError(_("Batch No is not required for item {0}").format(item_code))

			if flt(row.qty) == 0 and row.serial_no:
				row.serial_no = ''

			# docstatus should be < 2
			validate_cancelled_item(item_code, item.docstatus, verbose=0)

		except Exception as e:
			self.validation_messages.append(_("Row # ") + ("%d: " % (row.idx)) + cstr(e))

	def update_stock_ledger(self):
		sl_entries = []

		for d in self.items:
			if d.serial_no or d.current_serial_no:
				self.get_sle_for_existing_serial_no_issue(d, sl_entries)
				self.get_sle_for_new_serial_no_receipt(d, sl_entries)
			else:
				self.get_sle_for_item(d, sl_entries)

		if self.docstatus == 2:
			sl_entries.reverse()

		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')

		self.validate_serial_no_ledger()

	def validate_serial_no_ledger(self):
		item_serial_nos = {}
		for d in self.items:
			for serial_no in get_serial_nos(d.serial_no):
				item_serial_nos.setdefault(d.item_code, []).append(serial_no)
			for serial_no in get_serial_nos(d.current_serial_no):
				item_serial_nos.setdefault(d.item_code, []).append(serial_no)

		for item_code, serial_nos in item_serial_nos.items():
			serial_nos = list(set(serial_nos))
			validate_serial_no_ledger(serial_nos, item_code, self.doctype, self.name, self.company)

	def get_sle_for_item(self, d, sl_entries):
		sle = {
			"reset_rate": cint(self.reset_rate)
		}
		if d.batch_no:
			sle["batch_qty_after_transaction"] = flt(d.total_qty)
			sle["batch_valuation_rate"] = flt(d.valuation_rate)
		else:
			sle["qty_after_transaction"] = flt(d.total_qty)
			sle["valuation_rate"] = flt(d.valuation_rate)

		sl_entries.append(self.get_sl_entries(d, sle))

	def get_sle_for_existing_serial_no_issue(self, d, sl_entries):
		sle = {
			"reset_rate": cint(self.reset_rate),
		}

		current_serial_nos = set(get_serial_nos(d.get('current_serial_no')))
		serial_nos = set(get_serial_nos(d.get('serial_no')))

		if cint(self.reset_rate):
			sle["actual_qty"] = -1 * len(current_serial_nos)
			sle["serial_no"] = d.get('current_serial_no')

			# serial no ledger validation will be run manually
			if self.docstatus == 1:
				sle["skip_serial_no_ledger_validation"] = True
				sle["allow_negative_stock"] = True
		else:
			serial_nos_removed = current_serial_nos - serial_nos
			sle["actual_qty"] = -1 * len(serial_nos_removed)
			sle["serial_no"] = '\n'.join(serial_nos_removed)

		if sle["actual_qty"]:
			sl_entries.append(self.get_sl_entries(d, sle))

	def get_sle_for_new_serial_no_receipt(self, d, sl_entries):
		sle = {
			"reset_rate": cint(self.reset_rate),
			"valuation_rate": d.valuation_rate,
			"batch_valuation_rate": d.valuation_rate,
			"incoming_rate": d.valuation_rate
		}

		current_serial_nos = set(get_serial_nos(d.get('current_serial_no')))
		serial_nos = set(get_serial_nos(d.get('serial_no')))

		if cint(self.reset_rate):
			sle["actual_qty"] = len(serial_nos)
			sle["serial_no"] = d.get('serial_no')

			# serial no ledger validation will be run manually
			if self.docstatus == 2:
				sle["skip_serial_no_ledger_validation"] = True
		else:
			serial_nos_added = serial_nos - current_serial_nos
			sle["actual_qty"] = len(serial_nos_added)
			sle["serial_no"] = '\n'.join(serial_nos_added)

		if sle["actual_qty"]:
			sl_entries.append(self.get_sl_entries(d, sle))

	def get_stock_voucher_items(self, sle_map):
		is_opening = "Yes" if self.purpose == "Opening Stock" else "No"
		details = []
		for item_code, voucher_detail_no in sle_map:
			details.append(frappe._dict({
				"name": voucher_detail_no,
				"expense_account": self.expense_account,
				"cost_center": self.cost_center,
				"is_opening": is_opening
			}))
		return details

	def validate_expense_account(self):
		if not cint(erpnext.is_perpetual_inventory_enabled(self.company)):
			return

		if not self.expense_account:
			msgprint(_("Please enter Expense Account"), raise_exception=1)
		elif not frappe.db.sql("""select name from `tabStock Ledger Entry` limit 1"""):
			if frappe.db.get_value("Account", self.expense_account, "report_type") == "Profit and Loss":
				frappe.throw(_("Difference Account must be a Asset/Liability type account, since this Stock Reconciliation is an Opening Entry"), OpeningEntryAccountError)

	def set_total_qty_and_amount(self):
		stock_value_precision = get_field_precision(frappe.get_meta("Stock Ledger Entry").get_field("stock_value"),
			currency=frappe.get_cached_value('Company', self.company, "default_currency"))

		self.difference_amount = 0.0
		for d in self.get("items"):
			d.quantity_difference = flt(d.total_qty) - flt(d.current_qty)
			if cint(self.reset_rate):
				d.amount = flt(d.total_qty) * flt(d.valuation_rate)
			else:
				if d.quantity_difference and d.quantity_difference < 0:
					args = get_args_for_incoming_rate(self, d)
					incoming_rate = get_incoming_rate(args, raise_error_if_no_rate=False)
					d.amount = d.current_amount + (d.quantity_difference * incoming_rate)
				else:
					d.amount = flt(d.total_qty) * flt(d.current_valuation_rate)

			if not cint(self.reset_rate):
				d.valuation_rate = d.amount / flt(d.total_qty) if flt(d.total_qty) else d.current_valuation_rate

			d.amount = flt(d.amount, stock_value_precision)
			d.amount_difference = flt(d.amount) - flt(d.current_amount)
			self.difference_amount += d.amount_difference

	def get_items_for(self, warehouse):
		self.items = []
		for item in get_items(warehouse, self.posting_date, self.posting_time, self.company):
			self.append("items", item)

	def submit(self):
		if len(self.items) > 100:
			msgprint(_("The task has been enqueued as a background job. In case there is any issue on processing in background, the system will add a comment about the error on this Stock Reconciliation and revert to the Draft stage"))
			self.queue_action('submit')
		else:
			self._submit()

	def cancel(self):
		if len(self.items) > 100:
			self.queue_action('cancel')
		else:
			self._cancel()

@frappe.whitelist()
def get_items(args):
	if isinstance(args, string_types):
		args = json.loads(args)
	args = frappe._dict(args)

	if not args.warehouse:
		frappe.throw(_("Please select Warehouse"))
	if not args.company:
		args.company = frappe.get_cached_value("Warehouse", args.warehouse, 'company')
	if not args.company:
		frappe.throw(_("Please select Company"))
	if not args.posting_date:
		frappe.throw(_("Please set Posting Date"))

	conditions = []

	if args.warehouse:
		lft, rgt = frappe.db.get_value("Warehouse", args.warehouse, ["lft", "rgt"])
		conditions.append("exists(select wh.name from `tabWarehouse` wh where wh.lft >= {0} and wh.rgt <= {1} and wh.name=bin.warehouse)"
			.format(lft, rgt))

	if args.item_code:
		conditions.append("i.name = %(item_code)s")
	else:
		if args.item_group:
			lft, rgt = frappe.db.get_value("Item Group", args.item_group, ["lft", "rgt"])
			conditions.append("exists (select ig.name from `tabItem Group` ig where ig.lft >= {0} and ig.rgt <= {1} and ig.name=i.item_group)"
				.format(lft, rgt))
		if args.brand:
			conditions.append("i.brand = %(brand)s")

	conditions = "and {0}".format(" and ".join(conditions)) if conditions else ""

	qty_condition = "both"
	if args.positive_or_negative == "Negative Only":
		qty_condition = "negative"
	elif args.positive_or_negative == "Positive Only":
		qty_condition = "positive"

	has_batch_no_condition = "or i.has_batch_no = 1" if cint(args.get_batches) else ""
	bin_qty_condition = "and (bin.actual_qty > 0 {0})".format(has_batch_no_condition)
	if qty_condition == "negative":
		bin_qty_condition = "and (bin.actual_qty < 0 {0})".format(has_batch_no_condition)
	elif qty_condition == "both":
		bin_qty_condition = "and (bin.actual_qty != 0 {0})".format(has_batch_no_condition)

	items = frappe.db.sql("""
		select i.name, bin.warehouse
		from tabBin bin, tabItem i
		where i.name=bin.item_code and i.disabled=0 {0} {1}
	""".format(bin_qty_condition, conditions), args)

	res = []
	for d in set(items):
		item_code, warehouse = d
		item_details_args = {
			"company": args.company,
			"posting_date": args.posting_date,
			"posting_time": args.posting_time,
			"item_code": item_code,
			"warehouse": warehouse,
			"reset_rate": cint(args.reset_rate),
			"loose_uom": args.loose_uom
		}
		batch_list = []

		if frappe.get_cached_value("Item", item_code, "has_batch_no") and cint(args.get_batches):
			batches = get_batches(item_code, warehouse, posting_date=args.posting_date, posting_time=args.posting_time,
				qty_condition=qty_condition)
			for b in batches:
				batch_list.append({'batch_no': b.name, 'batch_date': b.received_date})
		else:
			batch_list = [{'batch_no': None}]

		for b in batch_list:
			args_copy = item_details_args.copy()
			args_copy.update(b)
			item_details = get_item_details(args_copy)
			res.append(item_details)

	def sort_by(d):
		if args.sort_by == 'Item Group':
			return cstr(d.get('item_group')), cstr(d.get('item_code')), cstr(d.get('warehouse')), get_datetime(d.get('batch_date'))
		elif args.sort_by == 'Stock Qty':
			return -flt(d.get('current_qty'))
		else:
			return cstr(d.get('item_code')), cstr(d.get('warehouse')), get_datetime(d.get('batch_date'))

	res = sorted(res, key=sort_by)

	return res

@frappe.whitelist()
def get_item_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	if not args.item_code or not args.posting_date or not args.posting_time or not args.company:
		return out

	item = frappe.get_cached_doc("Item", args.item_code)

	out.item_code = args.item_code
	out.item_name = args.item_name or item.item_name
	out.item_group = item.item_group

	out.loose_uom = args.loose_uom or item.stock_uom
	out.stock_uom = item.stock_uom

	if not args.warehouse and args.default_warehouse:
		args.warehouse = args.default_warehouse

	if args.warehouse:
		out.warehouse = args.warehouse
	else:
		out.warehouse = get_default_warehouse(item, args, True)
		args.warehouse = out.warehouse

	out.cost_center = get_default_cost_center(item, args)

	if args.item_code and args.warehouse:
		out.current_qty, out.current_valuation_rate, out.current_amount, out.current_serial_no = get_stock_balance_for(args.item_code,
			args.warehouse, args.posting_date, args.posting_time, args.batch_no)

	if not item.has_batch_no or args.batch_no:
		qty_precision = frappe.get_precision("Stock Reconciliation Item", "qty")
		out.qty = flt(args.qty) or out.current_qty or None
		if out.qty and flt(out.qty) < 1 / (10**qty_precision):
			out.qty = "0"

	out.batch_no = args.batch_no if item.has_batch_no else None
	if args.batch_date:
		out.batch_date = args.batch_date if item.has_batch_no else None
	elif args.batch_no and item.has_batch_no:
		out.batch_date = get_batch_received_date(args.batch_no, args.warehouse)

	stock_value_precision = get_field_precision(frappe.get_meta("Stock Ledger Entry").get_field("stock_value"),
		currency=frappe.get_cached_value('Company', args.company, "default_currency"))

	out.conversion_factor = get_conversion_factor(out.item_code, out.loose_uom)["conversion_factor"]
	out.loose_qty = 0
	out.stock_loose_qty = flt(out.conversion_factor) * flt(out.loose_qty)
	out.total_qty = flt(out.qty) + flt(out.stock_loose_qty)

	out.quantity_difference = flt(out.total_qty) - flt(out.current_qty)

	# if out.quantity_difference:
	if cint(args.reset_rate):
		out.amount = flt(out.total_qty) * flt(out.current_valuation_rate)
	else:
		if out.quantity_difference < 0:
			incoming_rate = get_incoming_rate(get_args_for_incoming_rate(args, out))
			out.amount = flt(out.current_amount) + (incoming_rate * out.quantity_difference)
		else:
			out.amount = flt(out.total_qty) * flt(out.current_valuation_rate)

	out.valuation_rate = flt(out.amount / flt(out.total_qty) if flt(out.total_qty) else out.current_valuation_rate)

	out.amount = flt(out.amount, stock_value_precision)
	out.amount_difference = flt(out.amount) - flt(out.current_amount)

	return out


def get_stock_balance_for(item_code, warehouse, posting_date, posting_time, batch_no=None, with_valuation_rate=True):
	frappe.has_permission("Stock Reconciliation", "write", throw=True)

	serial_nos = ""

	item_dict = frappe.get_cached_value("Item", item_code, ["has_batch_no", "has_serial_no"], as_dict=1)
	with_serial_no = cint(item_dict.get("has_serial_no"))
	batch_no = batch_no if cint(item_dict.get("has_batch_no")) else None

	data = get_stock_balance(item_code, warehouse,
		posting_date, posting_time, batch_no=batch_no,
		with_valuation_rate=with_valuation_rate, with_serial_no=with_serial_no)

	if with_serial_no:
		qty, rate, amount, serial_nos = data
	else:
		qty, rate, amount = data

	if batch_no:
		qty = flt(get_batch_qty_on(batch_no, warehouse, posting_date, posting_time))

	return qty, rate, amount, serial_nos


@frappe.whitelist()
def get_difference_account(purpose, company):
	if purpose == 'Stock Reconciliation':
		account = get_company_default(company, "stock_adjustment_account")
	else:
		account = get_company_default(company, "temporary_opening_account")

	return account


def get_args_for_incoming_rate(args, item):
	current_serial_nos = set(get_serial_nos(item.get('current_serial_no')))
	serial_nos = set(get_serial_nos(item.get('serial_no')))

	if cint(args.get('reset_rate')):
		outgoing_serial_nos = current_serial_nos
	else:
		outgoing_serial_nos = current_serial_nos - serial_nos

	return frappe._dict({
		"item_code": item.item_code,
		"warehouse": item.warehouse,
		"batch_no": item.batch_no,
		"serial_no": "\n".join(outgoing_serial_nos),
		"posting_date": args.posting_date,
		"posting_time": args.posting_time,
		"qty": flt(item.quantity_difference),
		"voucher_type": "Stock Reconciliation",
		"voucher_no": args.get('name') or args.get('voucher_no'),
		"company": args.company
	})
