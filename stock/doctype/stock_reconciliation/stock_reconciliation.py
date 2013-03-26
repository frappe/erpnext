# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
import json
from webnotes import msgprint, _
from webnotes.utils import cstr, flt, cint
from stock.stock_ledger import update_entries_after
from controllers.stock_controller import StockController

class DocType(StockController):
	def setup(self):
		self.head_row = ["Item Code", "Warehouse", "Quantity", "Valuation Rate"]
		self.entries = []
		
	def validate(self):
		self.validate_data()
		
	def on_submit(self):
		self.insert_stock_ledger_entries()
		self.set_stock_value_difference()
		self.make_gl_entries()
		
	def on_cancel(self):
		self.delete_stock_ledger_entries()
		self.make_gl_entries()
		
	def validate_data(self):
		if not self.doc.reconciliation_json:
			return
			
		data = json.loads(self.doc.reconciliation_json)
		if self.head_row not in data:
			msgprint(_("""Hey! You seem to be using the wrong template. \
				Click on 'Download Template' button to get the correct template."""),
				raise_exception=1)
		
		# remove the help part and save the json
		if data.index(self.head_row) != 0:
			data = data[data.index(self.head_row):]
			self.doc.reconciliation_json = json.dumps(data)
				
		def _get_msg(row_num, msg):
			return _("Row # ") + ("%d: " % (row_num+2)) + _(msg)
		
		self.validation_messages = []
		item_warehouse_combinations = []
		
		# validate no of rows
		rows = data[data.index(self.head_row)+1:]
		if len(rows) > 100:
			msgprint(_("""Sorry! We can only allow upto 100 rows for Stock Reconciliation."""),
				raise_exception=True)
		
		for row_num, row in enumerate(rows):
			# find duplicates
			if [row[0], row[1]] in item_warehouse_combinations:
				self.validation_messages.append(_get_msg(row_num, "Duplicate entry"))
			else:
				item_warehouse_combinations.append([row[0], row[1]])
			
			self.validate_item(row[0], row_num)
			# note: warehouse will be validated through link validation
			
			# if both not specified
			if row[2] == "" and row[3] == "":
				self.validation_messages.append(_get_msg(row_num,
					"Please specify either Quantity or Valuation Rate or both"))
			
			# do not allow negative quantity
			if flt(row[2]) < 0:
				self.validation_messages.append(_get_msg(row_num, 
					"Negative Quantity is not allowed"))
			
			# do not allow negative valuation
			if flt(row[3]) < 0:
				self.validation_messages.append(_get_msg(row_num, 
					"Negative Valuation Rate is not allowed"))
		
		# throw all validation messages
		if self.validation_messages:
			for msg in self.validation_messages:
				msgprint(msg)
			
			raise webnotes.ValidationError
			
	def validate_item(self, item_code, row_num):
		from stock.utils import validate_end_of_life, validate_is_stock_item, \
			validate_cancelled_item
		
		# using try except to catch all validation msgs and display together
		
		try:
			item = webnotes.doc("Item", item_code)
			
			# end of life and stock item
			validate_end_of_life(item_code, item.end_of_life, verbose=0)
			validate_is_stock_item(item_code, item.is_stock_item, verbose=0)
		
			# item should not be serialized
			if item.has_serial_no == "Yes":
				raise webnotes.ValidationError, (_("Serialized Item: '") + item_code +
					_("""' can not be managed using Stock Reconciliation.\
					You can add/delete Serial No directly, \
					to modify stock of this item."""))
		
			# docstatus should be < 2
			validate_cancelled_item(item_code, item.docstatus, verbose=0)
				
		except Exception, e:
			self.validation_messages.append(_("Row # ") + ("%d: " % (row_num+2)) + cstr(e))
			
	def insert_stock_ledger_entries(self):
		"""	find difference between current and expected entries
			and create stock ledger entries based on the difference"""
		from stock.utils import get_valuation_method
		from stock.stock_ledger import get_previous_sle
			
		row_template = ["item_code", "warehouse", "qty", "valuation_rate"]
		
		if not self.doc.reconciliation_json:
			msgprint(_("""Stock Reconciliation file not uploaded"""), raise_exception=1)
		
		data = json.loads(self.doc.reconciliation_json)
		for row_num, row in enumerate(data[data.index(self.head_row)+1:]):
			row = webnotes._dict(zip(row_template, row))
			row["row_num"] = row_num
			previous_sle = get_previous_sle({
				"item_code": row.item_code,
				"warehouse": row.warehouse,
				"posting_date": self.doc.posting_date,
				"posting_time": self.doc.posting_time
			})
			
			# check valuation rate mandatory
			if row.qty != "" and not row.valuation_rate and \
					flt(previous_sle.get("qty_after_transaction")) <= 0:
				webnotes.msgprint(_("As existing qty for item: ") + row.item_code + 
					_(" is less than equals to zero in the system, \
						valuation rate is mandatory for this item"), raise_exception=1)
			
			change_in_qty = row.qty != "" and \
				(flt(row.qty) - flt(previous_sle.get("qty_after_transaction")))
			
			change_in_rate = row.valuation_rate != "" and \
				(flt(row.valuation_rate) - flt(previous_sle.get("valuation_rate")))
			
			if get_valuation_method(row.item_code) == "Moving Average":
				self.sle_for_moving_avg(row, previous_sle, change_in_qty, change_in_rate)
					
			else:
				self.sle_for_fifo(row, previous_sle, change_in_qty, change_in_rate)
					
	def sle_for_moving_avg(self, row, previous_sle, change_in_qty, change_in_rate):
		"""Insert Stock Ledger Entries for Moving Average valuation"""
		def _get_incoming_rate(qty, valuation_rate, previous_qty, previous_valuation_rate):
			if previous_valuation_rate == 0:
				return flt(valuation_rate)
			else:
				if valuation_rate == "":
					valuation_rate = previous_valuation_rate
				return (qty * valuation_rate - previous_qty * previous_valuation_rate) \
					/ flt(qty - previous_qty)
		
		if change_in_qty:
			# if change in qty, irrespective of change in rate
			incoming_rate = _get_incoming_rate(flt(row.qty), flt(row.valuation_rate),
				flt(previous_sle.get("qty_after_transaction")),
				flt(previous_sle.get("valuation_rate")))
				
			row["voucher_detail_no"] = "Row: " + cstr(row.row_num) + "/Actual Entry"
			self.insert_entries({"actual_qty": change_in_qty, "incoming_rate": incoming_rate}, row)
			
		elif change_in_rate and flt(previous_sle.get("qty_after_transaction")) > 0:
			# if no change in qty, but change in rate 
			# and positive actual stock before this reconciliation
			incoming_rate = _get_incoming_rate(
				flt(previous_sle.get("qty_after_transaction"))+1, flt(row.valuation_rate),
				flt(previous_sle.get("qty_after_transaction")), 
				flt(previous_sle.get("valuation_rate")))
				
			# +1 entry
			row["voucher_detail_no"] = "Row: " + cstr(row.row_num) + "/Valuation Adjustment +1"
			self.insert_entries({"actual_qty": 1, "incoming_rate": incoming_rate}, row)
			
			# -1 entry
			row["voucher_detail_no"] = "Row: " + cstr(row.row_num) + "/Valuation Adjustment -1"
			self.insert_entries({"actual_qty": -1}, row)
		
	def sle_for_fifo(self, row, previous_sle, change_in_qty, change_in_rate):
		"""Insert Stock Ledger Entries for FIFO valuation"""
		previous_stock_queue = json.loads(previous_sle.get("stock_queue") or "[]")
		previous_stock_qty = sum((batch[0] for batch in previous_stock_queue))
		previous_stock_value = sum((batch[0] * batch[1] for batch in \
			previous_stock_queue))
			
		def _insert_entries():
			if previous_stock_queue != [[row.qty, row.valuation_rate]]:
				# make entry as per attachment
				if row.qty:
					row["voucher_detail_no"] = "Row: " + cstr(row.row_num) + "/Actual Entry"
					self.insert_entries({"actual_qty": row.qty, 
						"incoming_rate": flt(row.valuation_rate)}, row)
				
				# Make reverse entry
				if previous_stock_qty:
					row["voucher_detail_no"] = "Row: " + cstr(row.row_num) + "/Reverse Entry"
					self.insert_entries({"actual_qty": -1 * previous_stock_qty, 
						"incoming_rate": previous_stock_qty < 0 and 
							flt(row.valuation_rate) or 0}, row)
					
					
		if change_in_qty:
			if row.valuation_rate == "":
				# dont want change in valuation
				if previous_stock_qty > 0:
					# set valuation_rate as previous valuation_rate
					row.valuation_rate = previous_stock_value / flt(previous_stock_qty)
			
			_insert_entries()
					
		elif change_in_rate and previous_stock_qty > 0:
			# if no change in qty, but change in rate 
			# and positive actual stock before this reconciliation
			
			row.qty = previous_stock_qty
			_insert_entries()
					
	def insert_entries(self, opts, row):
		"""Insert Stock Ledger Entries"""		
		args = webnotes._dict({
			"doctype": "Stock Ledger Entry",
			"item_code": row.item_code,
			"warehouse": row.warehouse,
			"posting_date": self.doc.posting_date,
			"posting_time": self.doc.posting_time,
			"voucher_type": self.doc.doctype,
			"voucher_no": self.doc.name,
			"company": self.doc.company,
			"is_cancelled": "No",
			"voucher_detail_no": row.voucher_detail_no,
			"fiscal_year": self.doc.fiscal_year,
		})
		args.update(opts)
		# create stock ledger entry
		sle_wrapper = webnotes.bean([args])
		sle_wrapper.ignore_permissions = 1
		sle_wrapper.insert()
		
		# update bin
		webnotes.get_obj('Warehouse', row.warehouse).update_bin(args)
		
		# append to entries
		self.entries.append(args)
		
	def delete_stock_ledger_entries(self):
		"""	Delete Stock Ledger Entries related to this Stock Reconciliation
			and repost future Stock Ledger Entries"""
					
		existing_entries = webnotes.conn.sql("""select item_code, warehouse 
			from `tabStock Ledger Entry` where voucher_type='Stock Reconciliation' 
			and voucher_no=%s""", self.doc.name, as_dict=1)
				
		# delete entries
		webnotes.conn.sql("""delete from `tabStock Ledger Entry` 
			where voucher_type='Stock Reconciliation' and voucher_no=%s""", self.doc.name)
		
		# repost future entries for selected item_code, warehouse
		for entries in existing_entries:
			update_entries_after({
				"item_code": entries.item_code,
				"warehouse": entries.warehouse,
				"posting_date": self.doc.posting_date,
				"posting_time": self.doc.posting_time
			})
			
	def set_stock_value_difference(self):
		"""stock_value_difference is the increment in the stock value"""
		from stock.utils import get_buying_amount
		
		item_list = [d.item_code for d in self.entries]
		warehouse_list = [d.warehouse for d in self.entries]
		stock_ledger_entries = self.get_stock_ledger_entries(item_list, warehouse_list)
		
		self.doc.stock_value_difference = 0.0
		for d in self.entries:
			self.doc.stock_value_difference -= get_buying_amount(d.item_code, d.warehouse, 
				d.actual_qty, self.doc.doctype, self.doc.name, d.voucher_detail_no, 
				stock_ledger_entries)
		webnotes.conn.set(self.doc, "stock_value_difference", self.doc.stock_value_difference)
		
	def make_gl_entries(self):
		if not cint(webnotes.defaults.get_global_default("auto_inventory_accounting")):
			return
		
		if not self.doc.expense_account:
			msgprint(_("Please enter Expense Account"), raise_exception=1)
			
		from accounts.general_ledger import make_gl_entries
				
		gl_entries = self.get_gl_entries_for_stock(self.doc.expense_account, 
			self.doc.stock_value_difference)
		if gl_entries:
			make_gl_entries(gl_entries, cancel=self.doc.docstatus == 2)
		
@webnotes.whitelist()
def upload():
	from webnotes.utils.datautils import read_csv_content_from_uploaded_file
	return read_csv_content_from_uploaded_file()