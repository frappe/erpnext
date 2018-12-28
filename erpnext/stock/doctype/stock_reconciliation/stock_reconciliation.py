# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
import frappe.defaults
from frappe import msgprint, _
from frappe.utils import cstr, flt, cint
from erpnext.stock.stock_ledger import update_entries_after
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.utils import get_stock_balance

class OpeningEntryAccountError(frappe.ValidationError): pass
class EmptyStockReconciliationItemsError(frappe.ValidationError): pass

class StockReconciliation(StockController):
	def __init__(self, *args, **kwargs):
		super(StockReconciliation, self).__init__(*args, **kwargs)
		self.head_row = ["Item Code", "Warehouse", "Quantity", "Valuation Rate"]

	def validate(self):
		if not self.expense_account:
			self.expense_account = frappe.db.get_value("Company", self.company, "stock_adjustment_account")
		if not self.cost_center:
			self.cost_center = frappe.db.get_value("Company", self.company, "cost_center")
		self.validate_posting_time()
		self.remove_items_with_no_change()
		self.validate_data()
		self.validate_expense_account()
		self.set_total_qty_and_amount()

	def on_submit(self):
		self.update_stock_ledger()
		self.make_gl_entries()

	def on_cancel(self):
		self.delete_and_repost_sle()
		self.make_gl_entries_on_cancel()

	def remove_items_with_no_change(self):
		"""Remove items if qty or rate is not changed"""
		self.difference_amount = 0.0
		def _changed(item):
			qty, rate = get_stock_balance(item.item_code, item.warehouse,
					self.posting_date, self.posting_time, with_valuation_rate=True)
			if (item.qty==None or item.qty==qty) and (item.valuation_rate==None or item.valuation_rate==rate):
				return False
			else:
				# set default as current rates
				if item.qty==None:
					item.qty = qty

				if item.valuation_rate==None:
					item.valuation_rate = rate

				item.current_qty = qty
				item.current_valuation_rate = rate
				self.difference_amount += (flt(item.qty, item.precision("qty")) * \
					flt(item.valuation_rate or rate, item.precision("valuation_rate")) \
					- flt(qty, item.precision("qty")) * flt(rate, item.precision("valuation_rate")))
				return True

		items = filter(lambda d: _changed(d), self.items)

		if not items:
			frappe.throw(_("None of the items have any change in quantity or value."),
				EmptyStockReconciliationItemsError)

		elif len(items) != len(self.items):
			self.items = items
			for i, item in enumerate(self.items):
				item.idx = i + 1
			frappe.msgprint(_("Removed items with no change in quantity or value."))

	def validate_data(self):
		def _get_msg(row_num, msg):
			return _("Row # {0}: ").format(row_num+1) + msg

		self.validation_messages = []
		item_warehouse_combinations = []

		default_currency = frappe.db.get_default("currency")

		for row_num, row in enumerate(self.items):
			# find duplicates
			if [row.item_code, row.warehouse] in item_warehouse_combinations:
				self.validation_messages.append(_get_msg(row_num, _("Duplicate entry")))
			else:
				item_warehouse_combinations.append([row.item_code, row.warehouse])

			self.validate_item(row.item_code, row_num+1)

			# validate warehouse
			if not frappe.db.get_value("Warehouse", row.warehouse):
				self.validation_messages.append(_get_msg(row_num, _("Warehouse not found in the system")))

			# if both not specified
			if row.qty in ["", None] and row.valuation_rate in ["", None]:
				self.validation_messages.append(_get_msg(row_num,
					_("Please specify either Quantity or Valuation Rate or both")))

			# do not allow negative quantity
			if flt(row.qty) < 0:
				self.validation_messages.append(_get_msg(row_num,
					_("Negative Quantity is not allowed")))

			# do not allow negative valuation
			if flt(row.valuation_rate) < 0:
				self.validation_messages.append(_get_msg(row_num,
					_("Negative Valuation Rate is not allowed")))

			if row.qty and row.valuation_rate in ["", None]:
				row.valuation_rate = get_stock_balance(row.item_code, row.warehouse,
							self.posting_date, self.posting_time, with_valuation_rate=True)[1]
				if not row.valuation_rate:
					# try if there is a buying price list in default currency
					buying_rate = frappe.db.get_value("Item Price", {"item_code": row.item_code,
						"buying": 1, "currency": default_currency}, "price_list_rate")
					if buying_rate:
						row.valuation_rate = buying_rate

					else:
						# get valuation rate from Item
						row.valuation_rate = frappe.get_value('Item', row.item_code, 'valuation_rate')

		# throw all validation messages
		if self.validation_messages:
			for msg in self.validation_messages:
				msgprint(msg)

			raise frappe.ValidationError(self.validation_messages)

	def validate_item(self, item_code, row_num):
		from erpnext.stock.doctype.item.item import validate_end_of_life, \
			validate_is_stock_item, validate_cancelled_item

		# using try except to catch all validation msgs and display together

		try:
			item = frappe.get_doc("Item", item_code)

			# end of life and stock item
			validate_end_of_life(item_code, item.end_of_life, item.disabled, verbose=0)
			validate_is_stock_item(item_code, item.is_stock_item, verbose=0)

			# item should not be serialized
			if item.has_serial_no == 1:
				raise frappe.ValidationError(_("Serialized Item {0} cannot be updated using Stock Reconciliation, please use Stock Entry").format(item_code))

			# item managed batch-wise not allowed
			if item.has_batch_no == 1:
				raise frappe.ValidationError(_("Batched Item {0} cannot be updated using Stock Reconciliation, instead use Stock Entry").format(item_code))

			# docstatus should be < 2
			validate_cancelled_item(item_code, item.docstatus, verbose=0)

		except Exception as e:
			self.validation_messages.append(_("Row # ") + ("%d: " % (row_num)) + cstr(e))

	def update_stock_ledger(self):
		"""	find difference between current and expected entries
			and create stock ledger entries based on the difference"""
		from erpnext.stock.stock_ledger import get_previous_sle

		for row in self.items:
			previous_sle = get_previous_sle({
				"item_code": row.item_code,
				"warehouse": row.warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time
			})
			if previous_sle:
				if row.qty in ("", None):
					row.qty = previous_sle.get("qty_after_transaction", 0)

				if row.valuation_rate in ("", None):
					row.valuation_rate = previous_sle.get("valuation_rate", 0)

			if row.qty and not row.valuation_rate:
				frappe.throw(_("Valuation Rate required for Item in row {0}").format(row.idx))

			if ((previous_sle and row.qty == previous_sle.get("qty_after_transaction")
				and (row.valuation_rate == previous_sle.get("valuation_rate") or row.qty == 0))
				or (not previous_sle and not row.qty)):
					continue

			self.insert_entries(row)

	def insert_entries(self, row):
		"""Insert Stock Ledger Entries"""
		args = frappe._dict({
			"doctype": "Stock Ledger Entry",
			"item_code": row.item_code,
			"warehouse": row.warehouse,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"company": self.company,
			"stock_uom": frappe.db.get_value("Item", row.item_code, "stock_uom"),
			"is_cancelled": "No",
			"qty_after_transaction": flt(row.qty, row.precision("qty")),
			"valuation_rate": flt(row.valuation_rate, row.precision("valuation_rate"))
		})
		self.make_sl_entries([args])

	def delete_and_repost_sle(self):
		"""	Delete Stock Ledger Entries related to this voucher
			and repost future Stock Ledger Entries"""

		existing_entries = frappe.db.sql("""select distinct item_code, warehouse
			from `tabStock Ledger Entry` where voucher_type=%s and voucher_no=%s""",
			(self.doctype, self.name), as_dict=1)

		# delete entries
		frappe.db.sql("""delete from `tabStock Ledger Entry`
			where voucher_type=%s and voucher_no=%s""", (self.doctype, self.name))

		# repost future entries for selected item_code, warehouse
		for entries in existing_entries:
			update_entries_after({
				"item_code": entries.item_code,
				"warehouse": entries.warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time
			})

	def get_gl_entries(self, warehouse_account=None):
		if not self.cost_center:
			msgprint(_("Please enter Cost Center"), raise_exception=1)

		return super(StockReconciliation, self).get_gl_entries(warehouse_account,
			self.expense_account, self.cost_center)

	def validate_expense_account(self):
		if not cint(erpnext.is_perpetual_inventory_enabled(self.company)):
			return

		if not self.expense_account:
			msgprint(_("Please enter Expense Account"), raise_exception=1)
		elif not frappe.db.sql("""select name from `tabStock Ledger Entry` limit 1"""):
			if frappe.db.get_value("Account", self.expense_account, "report_type") == "Profit and Loss":
				frappe.throw(_("Difference Account must be a Asset/Liability type account, since this Stock Reconciliation is an Opening Entry"), OpeningEntryAccountError)

	def set_total_qty_and_amount(self):
		for d in self.get("items"):
			d.amount = flt(d.qty, d.precision("qty")) * flt(d.valuation_rate, d.precision("valuation_rate"))
			d.current_amount = (flt(d.current_qty,
				d.precision("current_qty")) * flt(d.current_valuation_rate, d.precision("current_valuation_rate")))

			d.quantity_difference = flt(d.qty) - flt(d.current_qty)
			d.amount_difference = flt(d.amount) - flt(d.current_amount)

	def get_items_for(self, warehouse):
		self.items = []
		for item in get_items(warehouse, self.posting_date, self.posting_time):
			self.append("items", item)

	def submit(self):
		if len(self.items) > 100:
			self.queue_action('submit')
		else:
			self._submit()

	def cancel(self):
		if len(self.items) > 100:
			self.queue_action('cancel')
		else:
			self._cancel()

@frappe.whitelist()
def get_items(warehouse, posting_date, posting_time):
	lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
	items = frappe.db.sql("""select item_code, warehouse from tabBin
		where exists(select name from `tabWarehouse` where lft >= %s and rgt <= %s and name=`tabBin`.warehouse)
	""", (lft, rgt))

	items += frappe.db.sql("""select name, default_warehouse from tabItem
		where exists(select name from `tabWarehouse` where lft >= %s and rgt <= %s and name=`tabItem`.default_warehouse)
			and is_stock_item = 1 and has_serial_no = 0 and has_batch_no = 0 and has_variants = 0 and disabled = 0
	""", (lft, rgt))

	res = []
	for item, wh in set(items):
		stock_bal = get_stock_balance(item, wh, posting_date, posting_time,
			with_valuation_rate=True)

		if frappe.db.get_value("Item", item, "disabled") == 0:

			res.append({
				"item_code": item,
				"warehouse": wh,
				"qty": stock_bal[0],
				"item_name": frappe.db.get_value('Item', item, 'item_name'),
				"valuation_rate": stock_bal[1],
				"current_qty": stock_bal[0],
				"current_valuation_rate": stock_bal[1]
			})

	return res

@frappe.whitelist()
def get_stock_balance_for(item_code, warehouse, posting_date, posting_time):
	frappe.has_permission("Stock Reconciliation", "write", throw = True)

	qty, rate = get_stock_balance(item_code, warehouse,
		posting_date, posting_time, with_valuation_rate=True)

	return {
		'qty': qty,
		'rate': rate
	}
