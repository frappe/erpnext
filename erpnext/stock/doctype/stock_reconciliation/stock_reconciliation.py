# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
import json
from frappe import msgprint, _
from frappe.utils import cstr, flt, cint
from erpnext.stock.stock_ledger import update_entries_after
from erpnext.controllers.stock_controller import StockController

class StockReconciliation(StockController):
	def __init__(self, arg1, arg2=None):
		super(StockReconciliation, self).__init__(arg1, arg2)
		self.head_row = ["Item Code", "Warehouse", "Quantity", "Valuation Rate"]

	def validate(self):
		self.validate_data()
		self.validate_expense_account()

	def on_submit(self):
		self.update_stock_ledger()
		self.make_gl_entries()

	def on_cancel(self):
		self.delete_and_repost_sle()
		self.make_gl_entries_on_cancel()

	def validate_data(self):
		if not self.reconciliation_json:
			return

		data = json.loads(self.reconciliation_json)

		# strip out extra columns (if any)
		data = [row[:4] for row in data]

		if self.head_row not in data:
			msgprint(_("""Wrong Template: Unable to find head row."""),
				raise_exception=1)

		# remove the help part and save the json
		head_row_no = 0
		if data.index(self.head_row) != 0:
			head_row_no = data.index(self.head_row)
			data = data[head_row_no:]
			self.reconciliation_json = json.dumps(data)

		def _get_msg(row_num, msg):
			return _("Row # {0}: ").format(row_num+head_row_no+2) + msg

		self.validation_messages = []
		item_warehouse_combinations = []

		# validate no of rows
		rows = data[1:]
		if len(rows) > 100:
			msgprint(_("""Sorry! We can only allow upto 100 rows for Stock Reconciliation."""),
				raise_exception=True)
		for row_num, row in enumerate(rows):
			# find duplicates
			if [row[0], row[1]] in item_warehouse_combinations:
				self.validation_messages.append(_get_msg(row_num, _("Duplicate entry")))
			else:
				item_warehouse_combinations.append([row[0], row[1]])

			self.validate_item(row[0], row_num+head_row_no+2)

			# validate warehouse
			if not frappe.db.get_value("Warehouse", row[1]):
				self.validation_messages.append(_get_msg(row_num, _("Warehouse not found in the system")))

			# if both not specified
			if row[2] in ["", None] and row[3] in ["", None]:
				self.validation_messages.append(_get_msg(row_num,
					_("Please specify either Quantity or Valuation Rate or both")))

			# do not allow negative quantity
			if flt(row[2]) < 0:
				self.validation_messages.append(_get_msg(row_num,
					_("Negative Quantity is not allowed")))

			# do not allow negative valuation
			if flt(row[3]) < 0:
				self.validation_messages.append(_get_msg(row_num,
					_("Negative Valuation Rate is not allowed")))

		# throw all validation messages
		if self.validation_messages:
			for msg in self.validation_messages:
				msgprint(msg)

			raise frappe.ValidationError

	def validate_item(self, item_code, row_num):
		from erpnext.stock.doctype.item.item import validate_end_of_life, \
			validate_is_stock_item, validate_cancelled_item

		# using try except to catch all validation msgs and display together

		try:
			item = frappe.get_doc("Item", item_code)
			if not item:
				raise frappe.ValidationError, (_("Item: {0} not found in the system").format(item_code))

			# end of life and stock item
			validate_end_of_life(item_code, item.end_of_life, verbose=0)
			validate_is_stock_item(item_code, item.is_stock_item, verbose=0)

			# item should not be serialized
			if item.has_serial_no == "Yes":
				raise frappe.ValidationError, _("Serialized Item {0} cannot be updated \
					using Stock Reconciliation").format(item_code)

			# item managed batch-wise not allowed
			if item.has_batch_no == "Yes":
				raise frappe.ValidationError, _("Item: {0} managed batch-wise, can not be reconciled using \
					Stock Reconciliation, instead use Stock Entry").format(item_code)

			# docstatus should be < 2
			validate_cancelled_item(item_code, item.docstatus, verbose=0)

		except Exception, e:
			self.validation_messages.append(_("Row # ") + ("%d: " % (row_num)) + cstr(e))

	def update_stock_ledger(self):
		"""	find difference between current and expected entries
			and create stock ledger entries based on the difference"""
		from erpnext.stock.stock_ledger import get_previous_sle

		row_template = ["item_code", "warehouse", "qty", "valuation_rate"]

		if not self.reconciliation_json:
			msgprint(_("""Stock Reconciliation file not uploaded"""), raise_exception=1)

		data = json.loads(self.reconciliation_json)
		for row_num, row in enumerate(data[data.index(self.head_row)+1:]):
			row = frappe._dict(zip(row_template, row))
			row["row_num"] = row_num

			if row.qty in ("", None) or row.valuation_rate in ("", None):
				previous_sle = get_previous_sle({
					"item_code": row.item_code,
					"warehouse": row.warehouse,
					"posting_date": self.posting_date,
					"posting_time": self.posting_time
				})

				if row.qty in ("", None):
					row.qty = previous_sle.get("qty_after_transaction")

				if row.valuation_rate in ("", None):
					row.valuation_rate = previous_sle.get("valuation_rate")

			# if row.qty and not row.valuation_rate:
			# 	frappe.throw(_("Valuation Rate required for Item {0}").format(row.item_code))

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
			"fiscal_year": self.fiscal_year,
			"is_cancelled": "No",
			"qty_after_transaction": row.qty,
			"valuation_rate": row.valuation_rate
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
		if not cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):
			return

		if not self.expense_account:
			msgprint(_("Please enter Expense Account"), raise_exception=1)
		elif not frappe.db.sql("""select name from `tabStock Ledger Entry` limit 1"""):
			if frappe.db.get_value("Account", self.expense_account, "report_type") == "Profit and Loss":
				frappe.throw(_("Difference Account must be a 'Liability' type account, since this Stock Reconciliation is an Opening Entry"))

@frappe.whitelist()
def upload():
	from frappe.utils.csvutils import read_csv_content_from_uploaded_file
	csv_content = read_csv_content_from_uploaded_file()
	return filter(lambda x: x and any(x), csv_content)
