# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe, erpnext
from frappe import _
from frappe.utils import cint, flt, cstr, now
from erpnext.stock.utils import get_valuation_method
import json

from six import iteritems

# future reposting
class NegativeStockError(frappe.ValidationError): pass

_exceptions = frappe.local('stockledger_exceptions')
# _exceptions = []

def make_sl_entries(sl_entries, is_amended=None, allow_negative_stock=False, via_landed_cost_voucher=False):
	if sl_entries:
		from erpnext.stock.utils import update_bin

		cancel = True if sl_entries[0].get("is_cancelled") == "Yes" else False
		if cancel:
			set_as_cancel(sl_entries[0].get('voucher_no'), sl_entries[0].get('voucher_type'))

		for sle in sl_entries:
			sle_id = None
			if sle.get('is_cancelled') == 'Yes':
				sle['actual_qty'] = -flt(sle['actual_qty'])

			if sle.get("actual_qty") or sle.get("voucher_type")=="Stock Reconciliation":
				sle_id = make_entry(sle, allow_negative_stock, via_landed_cost_voucher)

			args = sle.copy()
			args.update({
				"sle_id": sle_id,
				"is_amended": is_amended
			})
			update_bin(args, allow_negative_stock, via_landed_cost_voucher)

		if cancel:
			delete_cancelled_entry(sl_entries[0].get('voucher_type'), sl_entries[0].get('voucher_no'))

def set_as_cancel(voucher_type, voucher_no):
	frappe.db.sql("""update `tabStock Ledger Entry` set is_cancelled='Yes',
		modified=%s, modified_by=%s
		where voucher_no=%s and voucher_type=%s""",
		(now(), frappe.session.user, voucher_type, voucher_no))

def make_entry(args, allow_negative_stock=False, via_landed_cost_voucher=False):
	args.update({"doctype": "Stock Ledger Entry"})
	sle = frappe.get_doc(args)
	sle.flags.ignore_permissions = 1
	sle.allow_negative_stock=allow_negative_stock
	sle.via_landed_cost_voucher = via_landed_cost_voucher
	sle.insert()
	sle.submit()
	return sle.name

def delete_cancelled_entry(voucher_type, voucher_no):
	frappe.db.sql("""delete from `tabStock Ledger Entry`
		where voucher_type=%s and voucher_no=%s""", (voucher_type, voucher_no))

class update_entries_after(object):
	"""
		update valution rate and qty after transaction
		from the current time-bucket onwards

		:param args: args as dict

			args = {
				"item_code": "ABC",
				"warehouse": "XYZ",
				"posting_date": "2012-12-12",
				"posting_time": "12:00"
			}
	"""
	def __init__(self, args, allow_zero_rate=False, allow_negative_stock=None, via_landed_cost_voucher=False, verbose=1):
		from frappe.model.meta import get_field_precision

		self.exceptions = []
		self.verbose = verbose
		self.allow_zero_rate = allow_zero_rate
		self.allow_negative_stock = allow_negative_stock
		self.via_landed_cost_voucher = via_landed_cost_voucher
		if not self.allow_negative_stock:
			self.allow_negative_stock = cint(frappe.db.get_single_value("Stock Settings",
				"allow_negative_stock"))

		self.args = args
		for key, value in iteritems(args):
			setattr(self, key, value)

		self.previous_sle = self.get_sle_before_datetime()
		self.previous_sle = self.previous_sle[0] if self.previous_sle else frappe._dict()

		for key in ("qty_after_transaction", "valuation_rate", "stock_value"):
			setattr(self, key, flt(self.previous_sle.get(key)))

		self.company = frappe.db.get_value("Warehouse", self.warehouse, "company")
		self.precision = get_field_precision(frappe.get_meta("Stock Ledger Entry").get_field("stock_value"),
			currency=frappe.get_cached_value('Company',  self.company,  "default_currency"))

		self.prev_stock_value = self.previous_sle.stock_value or 0.0
		self.stock_queue = json.loads(self.previous_sle.stock_queue or "[]")
		self.valuation_method = get_valuation_method(self.item_code)
		self.stock_value_difference = 0.0
		self.build()

	def build(self):
		# includes current entry!
		entries_to_fix = self.get_sle_after_datetime()

		for sle in entries_to_fix:
			self.process_sle(sle)

		if self.exceptions:
			self.raise_exceptions()

		self.update_bin()

	def update_bin(self):
		# update bin
		bin_name = frappe.db.get_value("Bin", {
			"item_code": self.item_code,
			"warehouse": self.warehouse
		})

		if not bin_name:
			bin_doc = frappe.get_doc({
				"doctype": "Bin",
				"item_code": self.item_code,
				"warehouse": self.warehouse
			})
			bin_doc.insert(ignore_permissions=True)
		else:
			bin_doc = frappe.get_doc("Bin", bin_name)

		bin_doc.update({
			"valuation_rate": self.valuation_rate,
			"actual_qty": self.qty_after_transaction,
			"stock_value": self.stock_value
		})
		bin_doc.flags.via_stock_ledger_entry = True

		bin_doc.save(ignore_permissions=True)

	def process_sle(self, sle):
		if (sle.serial_no and not self.via_landed_cost_voucher) or not cint(self.allow_negative_stock):
			# validate negative stock for serialized items, fifo valuation
			# or when negative stock is not allowed for moving average
			if not self.validate_negative_stock(sle):
				self.qty_after_transaction += flt(sle.actual_qty)
				return

		if sle.serial_no:
			self.get_serialized_values(sle)
			self.qty_after_transaction += flt(sle.actual_qty)
			self.stock_value = flt(self.qty_after_transaction) * flt(self.valuation_rate)
		else:
			if sle.voucher_type=="Stock Reconciliation":
				# assert
				self.valuation_rate = sle.valuation_rate
				self.qty_after_transaction = sle.qty_after_transaction
				self.stock_queue = [[self.qty_after_transaction, self.valuation_rate]]
				self.stock_value = flt(self.qty_after_transaction) * flt(self.valuation_rate)
			else:
				if self.valuation_method == "Moving Average":
					self.get_moving_average_values(sle)
					self.qty_after_transaction += flt(sle.actual_qty)
					self.stock_value = flt(self.qty_after_transaction) * flt(self.valuation_rate)
				else:
					self.get_fifo_values(sle)
					self.qty_after_transaction += flt(sle.actual_qty)
					self.stock_value = sum((flt(batch[0]) * flt(batch[1]) for batch in self.stock_queue))

		# rounding as per precision
		self.stock_value = flt(self.stock_value, self.precision)

		if self.prev_stock_value < 0 and self.stock_value >= 0:
			stock_value_difference = sle.actual_qty * self.valuation_rate
		else:
			stock_value_difference = self.stock_value - self.prev_stock_value

		self.prev_stock_value = self.stock_value

		# update current sle
		sle.qty_after_transaction = self.qty_after_transaction
		sle.valuation_rate = self.valuation_rate
		sle.stock_value = self.stock_value
		sle.stock_queue = json.dumps(self.stock_queue)
		sle.stock_value_difference = stock_value_difference
		sle.doctype="Stock Ledger Entry"
		frappe.get_doc(sle).db_update()

	def validate_negative_stock(self, sle):
		"""
			validate negative stock for entries current datetime onwards
			will not consider cancelled entries
		"""
		diff = self.qty_after_transaction + flt(sle.actual_qty)

		if diff < 0 and abs(diff) > 0.0001:
			# negative stock!
			exc = sle.copy().update({"diff": diff})
			self.exceptions.append(exc)
			return False
		else:
			return True

	def get_serialized_values(self, sle):
		incoming_rate = flt(sle.incoming_rate)
		actual_qty = flt(sle.actual_qty)
		serial_no = cstr(sle.serial_no).split("\n")

		if incoming_rate < 0:
			# wrong incoming rate
			incoming_rate = self.valuation_rate

		stock_value_change = 0
		if incoming_rate:
			stock_value_change = actual_qty * incoming_rate
		elif actual_qty < 0:
			# In case of delivery/stock issue, get average purchase rate
			# of serial nos of current entry
			stock_value_change = -1 * flt(frappe.db.sql("""select sum(purchase_rate)
				from `tabSerial No` where name in (%s)""" % (", ".join(["%s"]*len(serial_no))),
				tuple(serial_no))[0][0])

		new_stock_qty = self.qty_after_transaction + actual_qty

		if new_stock_qty > 0:
			new_stock_value = (self.qty_after_transaction * self.valuation_rate) + stock_value_change
			if new_stock_value >= 0:
				# calculate new valuation rate only if stock value is positive
				# else it remains the same as that of previous entry
				self.valuation_rate = new_stock_value / new_stock_qty

		if not self.valuation_rate and sle.voucher_detail_no:
			allow_zero_rate = self.check_if_allow_zero_valuation_rate(sle.voucher_type, sle.voucher_detail_no)
			if not allow_zero_rate:
				self.valuation_rate = get_valuation_rate(sle.item_code, sle.warehouse,
					sle.voucher_type, sle.voucher_no, self.allow_zero_rate,
					currency=erpnext.get_company_currency(sle.company))

	def get_moving_average_values(self, sle):
		actual_qty = flt(sle.actual_qty)
		new_stock_qty = flt(self.qty_after_transaction) + actual_qty
		if new_stock_qty >= 0:
			if actual_qty > 0:
				if flt(self.qty_after_transaction) <= 0:
					self.valuation_rate = sle.incoming_rate
				else:
					new_stock_value = (self.qty_after_transaction * self.valuation_rate) + \
						(actual_qty * sle.incoming_rate)

					self.valuation_rate = new_stock_value / new_stock_qty

			elif sle.outgoing_rate:
				if new_stock_qty:
					new_stock_value = (self.qty_after_transaction * self.valuation_rate) + \
						(actual_qty * sle.outgoing_rate)

					self.valuation_rate = new_stock_value / new_stock_qty
				else:
					self.valuation_rate = sle.outgoing_rate

		else:
			if flt(self.qty_after_transaction) >= 0 and sle.outgoing_rate:
				self.valuation_rate = sle.outgoing_rate

			if not self.valuation_rate and actual_qty > 0:
				self.valuation_rate = sle.incoming_rate

			# Get valuation rate from previous SLE or Item master, if item does not have the
			# allow zero valuration rate flag set
			if not self.valuation_rate and sle.voucher_detail_no:
				allow_zero_valuation_rate = self.check_if_allow_zero_valuation_rate(sle.voucher_type, sle.voucher_detail_no)
				if not allow_zero_valuation_rate:
					self.valuation_rate = get_valuation_rate(sle.item_code, sle.warehouse,
						sle.voucher_type, sle.voucher_no, self.allow_zero_rate,
						currency=erpnext.get_company_currency(sle.company))

	def get_fifo_values(self, sle):
		incoming_rate = flt(sle.incoming_rate)
		actual_qty = flt(sle.actual_qty)
		outgoing_rate = flt(sle.outgoing_rate)

		if actual_qty > 0:
			if not self.stock_queue:
				self.stock_queue.append([0, 0])

			# last row has the same rate, just updated the qty
			if self.stock_queue[-1][1]==incoming_rate:
				self.stock_queue[-1][0] += actual_qty
			else:
				if self.stock_queue[-1][0] > 0:
					self.stock_queue.append([actual_qty, incoming_rate])
				else:
					qty = self.stock_queue[-1][0] + actual_qty
					self.stock_queue[-1] = [qty, incoming_rate]
		else:
			qty_to_pop = abs(actual_qty)
			while qty_to_pop:
				if not self.stock_queue:
					# Get valuation rate from last sle if exists or from valuation rate field in item master
					allow_zero_valuation_rate = self.check_if_allow_zero_valuation_rate(sle.voucher_type, sle.voucher_detail_no)
					if not allow_zero_valuation_rate:
						_rate = get_valuation_rate(sle.item_code, sle.warehouse,
							sle.voucher_type, sle.voucher_no, self.allow_zero_rate,
							currency=erpnext.get_company_currency(sle.company))
					else:
						_rate = 0

					self.stock_queue.append([0, _rate])

				index = None
				if outgoing_rate > 0:
					# Find the entry where rate matched with outgoing rate
					for i, v in enumerate(self.stock_queue):
						if v[1] == outgoing_rate:
							index = i
							break

					# If no entry found with outgoing rate, collapse stack
					if index == None:
						new_stock_value = sum((d[0]*d[1] for d in self.stock_queue)) - qty_to_pop*outgoing_rate
						new_stock_qty = sum((d[0] for d in self.stock_queue)) - qty_to_pop
						self.stock_queue = [[new_stock_qty, new_stock_value/new_stock_qty if new_stock_qty > 0 else outgoing_rate]]
						break
				else:
					index = 0

				# select first batch or the batch with same rate
				batch = self.stock_queue[index]
				if qty_to_pop >= batch[0]:
					# consume current batch
					qty_to_pop = qty_to_pop - batch[0]
					self.stock_queue.pop(index)
					if not self.stock_queue and qty_to_pop:
						# stock finished, qty still remains to be withdrawn
						# negative stock, keep in as a negative batch
						self.stock_queue.append([-qty_to_pop, outgoing_rate or batch[1]])
						break

				else:
					# qty found in current batch
					# consume it and exit
					batch[0] = batch[0] - qty_to_pop
					qty_to_pop = 0

		stock_value = sum((flt(batch[0]) * flt(batch[1]) for batch in self.stock_queue))
		stock_qty = sum((flt(batch[0]) for batch in self.stock_queue))

		if stock_qty:
			self.valuation_rate = stock_value / flt(stock_qty)

		if not self.stock_queue:
			self.stock_queue.append([0, sle.incoming_rate or sle.outgoing_rate or self.valuation_rate])

	def check_if_allow_zero_valuation_rate(self, voucher_type, voucher_detail_no):
		ref_item_dt = voucher_type + (" Detail" if voucher_type == "Stock Entry" else " Item")
		return frappe.db.get_value(ref_item_dt, voucher_detail_no, "allow_zero_valuation_rate")

	def get_sle_before_datetime(self):
		"""get previous stock ledger entry before current time-bucket"""
		return get_stock_ledger_entries(self.args, "<", "desc", "limit 1", for_update=False)

	def get_sle_after_datetime(self):
		"""get Stock Ledger Entries after a particular datetime, for reposting"""
		return get_stock_ledger_entries(self.previous_sle or frappe._dict({
				"item_code": self.args.get("item_code"), "warehouse": self.args.get("warehouse") }),
			">", "asc", for_update=True)

	def raise_exceptions(self):
		deficiency = min(e["diff"] for e in self.exceptions)

		if ((self.exceptions[0]["voucher_type"], self.exceptions[0]["voucher_no"]) in
			frappe.local.flags.currently_saving):

			msg = _("{0} units of {1} needed in {2} to complete this transaction.").format(
				abs(deficiency), frappe.get_desk_link('Item', self.item_code),
				frappe.get_desk_link('Warehouse', self.warehouse))
		else:
			msg = _("{0} units of {1} needed in {2} on {3} {4} for {5} to complete this transaction.").format(
				abs(deficiency), frappe.get_desk_link('Item', self.item_code),
				frappe.get_desk_link('Warehouse', self.warehouse),
				self.exceptions[0]["posting_date"], self.exceptions[0]["posting_time"],
				frappe.get_desk_link(self.exceptions[0]["voucher_type"], self.exceptions[0]["voucher_no"]))

		if self.verbose:
			frappe.throw(msg, NegativeStockError, title='Insufficent Stock')
		else:
			raise NegativeStockError(msg)

def get_previous_sle(args, for_update=False):
	"""
		get the last sle on or before the current time-bucket,
		to get actual qty before transaction, this function
		is called from various transaction like stock entry, reco etc

		args = {
			"item_code": "ABC",
			"warehouse": "XYZ",
			"posting_date": "2012-12-12",
			"posting_time": "12:00",
			"sle": "name of reference Stock Ledger Entry"
		}
	"""
	args["name"] = args.get("sle", None) or ""
	sle = get_stock_ledger_entries(args, "<=", "desc", "limit 1", for_update=for_update)
	return sle and sle[0] or {}

def get_stock_ledger_entries(previous_sle, operator=None, order="desc", limit=None, for_update=False, debug=False):
	"""get stock ledger entries filtered by specific posting datetime conditions"""
	conditions = " and timestamp(posting_date, posting_time) {0} timestamp(%(posting_date)s, %(posting_time)s)".format(operator)
	if previous_sle.get("warehouse"):
		conditions += " and warehouse = %(warehouse)s"
	elif previous_sle.get("warehouse_condition"):
		conditions += " and " + previous_sle.get("warehouse_condition")

	if not previous_sle.get("posting_date"):
		previous_sle["posting_date"] = "1900-01-01"
	if not previous_sle.get("posting_time"):
		previous_sle["posting_time"] = "00:00"

	if operator in (">", "<=") and previous_sle.get("name"):
		conditions += " and name!=%(name)s"

	return frappe.db.sql("""select *, timestamp(posting_date, posting_time) as "timestamp" from `tabStock Ledger Entry`
		where item_code = %%(item_code)s
		and ifnull(is_cancelled, 'No')='No'
		%(conditions)s
		order by timestamp(posting_date, posting_time) %(order)s, name %(order)s
		%(limit)s %(for_update)s""" % {
			"conditions": conditions,
			"limit": limit or "",
			"for_update": for_update and "for update" or "",
			"order": order
		}, previous_sle, as_dict=1, debug=debug)

def get_valuation_rate(item_code, warehouse, voucher_type, voucher_no,
	allow_zero_rate=False, currency=None, company=None, raise_error_if_no_rate=True):
	# Get valuation rate from last sle for the same item and warehouse
	if not company:
		company = erpnext.get_default_company()

	last_valuation_rate = frappe.db.sql("""select valuation_rate
		from `tabStock Ledger Entry`
		where item_code = %s and warehouse = %s
		and valuation_rate >= 0
		order by posting_date desc, posting_time desc, name desc limit 1""", (item_code, warehouse))

	if not last_valuation_rate:
		# Get valuation rate from last sle for the item against any warehouse
		last_valuation_rate = frappe.db.sql("""select valuation_rate
			from `tabStock Ledger Entry`
			where item_code = %s and valuation_rate > 0
			order by posting_date desc, posting_time desc, name desc limit 1""", item_code)

	if last_valuation_rate:
		return flt(last_valuation_rate[0][0]) # as there is previous records, it might come with zero rate

	# If negative stock allowed, and item delivered without any incoming entry,
	# system does not found any SLE, then take valuation rate from Item
	valuation_rate = frappe.db.get_value("Item", item_code, "valuation_rate")

	if not valuation_rate:
		# try Item Standard rate
		valuation_rate = frappe.db.get_value("Item", item_code, "standard_rate")

		if not valuation_rate:
			# try in price list
			valuation_rate = frappe.db.get_value('Item Price',
				dict(item_code=item_code, buying=1, currency=currency),
				'price_list_rate')

	if not allow_zero_rate and not valuation_rate and raise_error_if_no_rate \
			and cint(erpnext.is_perpetual_inventory_enabled(company)):
		frappe.local.message_log = []
		frappe.throw(_("Valuation rate not found for the Item {0}, which is required to do accounting entries for {1} {2}. If the item is transacting as a zero valuation rate item in the {1}, please mention that in the {1} Item table. Otherwise, please create an incoming stock transaction for the item or mention valuation rate in the Item record, and then try submiting/cancelling this entry").format(item_code, voucher_type, voucher_no))

	return valuation_rate
