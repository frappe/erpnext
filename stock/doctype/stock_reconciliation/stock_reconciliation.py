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
from webnotes.utils import cstr, flt



class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		
	def validate(self):
		self.validate_data()
		
	def on_submit(self):
		self.create_stock_ledger_entries()
		
	def on_cancel(self):
		pass
		
	def validate_data(self):
		data = json.loads(self.doc.reconciliation_json)
		if data[0] != ["Item Code", "Warehouse", "Quantity", "Valuation Rate"]:
			msgprint(_("""Hey! You seem to be using the wrong template. \
				Click on 'Download Template' button to get the correct template."""),
				raise_exception=1)
				
		def _get_msg(row_num, msg):
			return _("Row # ") + ("%d: " % (row_num+2)) + _(msg)
		
		self.validation_messages = []
		item_warehouse_combinations = []
		for row_num, row in enumerate(data[1:]):
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
					You can add/delete Serial No directly, to modify stock of this item."""))
		
			# docstatus should be < 2
			validate_cancelled_item(item_code, item.docstatus, verbose=0)
				
		except Exception, e:
			self.validation_messages.append(_("Row # ") + ("%d: " % (row_num+2)) + cstr(e))
			
	def create_stock_ledger_entries(self):
		"""	find difference between current and expected entries
			and create stock ledger entries based on the difference"""
		from stock.utils import get_previous_sle, get_valuation_method

		def _qty_diff(qty, previous_sle):
			return qty != "" and (flt(qty) - flt(previous_sle.get("qty_after_transaction"))) or 0.0

		def _rate_diff(rate, previous_sle):
			return rate != "" and (flt(rate) - flt(previous_sle.get("valuation_rate"))) or 0.0
			
		def _get_incoming_rate(qty, valuation_rate, previous_qty, previous_valuation_rate):
			if previous_valuation_rate == 0:
				return valuation_rate
			else:
				return (qty * valuation_rate - previous_qty * previous_valuation_rate) \
					/ flt(qty - previous_qty)
			
		row_template = ["item_code", "warehouse", "qty", "valuation_rate"]
		
		data = json.loads(self.doc.reconciliation_json)
		for row_num, row in enumerate(data[1:]):
			row = webnotes._dict(zip(row_template, row))
			
			args = webnotes._dict({
				"__islocal": 1,
				"item_code": row.item_code,
				"warehouse": row.warehouse,
				"posting_date": self.doc.posting_date,
				"posting_time": self.doc.posting_time,
				"voucher_type": self.doc.doctype,
				"voucher_no": self.doc.name,
				"company": webnotes.conn.get_default("company")
			})
			previous_sle = get_previous_sle(args)
			
			qty_diff = _qty_diff(row.qty, previous_sle)
						
			if get_valuation_method(row.item_code) == "Moving Average":
				if qty_diff:
					incoming_rate = _get_incoming_rate(flt(row.qty), flt(row.valuation_rate),
						flt(previous_sle.qty_after_transaction),
						flt(previous_sle.valuation_rate))
					
					# create sle
					webnotes.model_wrapper([args.update({
						"actual_qty": qty_diff,
						"incoming_rate": incoming_rate
					})]).save()
					
				elif _rate_diff(row.valuation_rate, previous_sle) and \
						previous_sle.qty_after_transaction >= 0:
					# make +1, -1 entry
					incoming_rate = _get_incoming_rate(flt(previous_sle.qty_after_transaction) + 1,
						flt(row.valuation_rate), flt(previous_sle.qty_after_transaction),
						flt(previous_sle.valuation_rate))
					
					# +1 entry
					webnotes.model_wrapper([args.copy().update({
						"actual_qty": 1,
						"incoming_rate": incoming_rate
					})]).save()
					
					# -1 entry
					webnotes.model_wrapper([args.update({"actual_qty": -1})]).save()
				
				# else:
				# 	# show message that stock is negative, hence can't update valuation
					
			else:
				# FIFO
				previous_stock_queue = json.loads(previous_sle.stock_queue)
				
				if previous_stock_queue != [[row.qty, row.valuation_rate]]:
					# make entry as per attachment
					sle_wrapper = webnotes.model_wrapper([args.copy().update({
						"actual_qty": row.qty,
						"incoming_rate": row.valuation_rate
					})])
					sle_wrapper.save()
				
					# Make reverse entry
					qty = sum((flt(fifo_item[0]) for fifo_item in previous_stock_queue))
					webnotes.model_wrapper([args.update({"actual_qty": -1 * qty})]).save()
				
				
				
	
		

		
		
@webnotes.whitelist()
def upload():
	from webnotes.utils.datautils import read_csv_content_from_uploaded_file
	return read_csv_content_from_uploaded_file()