# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint


class UnableToSelectBatchError(frappe.ValidationError): pass

class Batch(Document):
	def autoname(self):
		'''Generate random ID for batch if not specified'''
		if not self.batch_id:
			if frappe.db.get_value('Item', self.item, 'create_new_batch'):
				temp = None
				while not temp:
					temp = frappe.generate_hash()[:7].upper()
					if frappe.db.exists('Batch', temp):
						temp = None

				self.batch_id = temp
			else:
				frappe.throw(_('Batch ID is mandatory'), frappe.MandatoryError)

		self.name = self.batch_id

	def onload(self):
		self.image = frappe.db.get_value('Item', self.item, 'image')

	def validate(self):
		self.item_has_batch_enabled()

	def item_has_batch_enabled(self):
		if frappe.db.get_value("Item",self.item,"has_batch_no") == 0:
			frappe.throw(_("The selected item cannot have Batch"))

@frappe.whitelist()
def get_batch_qty(batch_no=None, warehouse=None, item_code=None):
	'''Returns batch actual qty if warehouse is passed,
		or returns dict of qty by warehouse if warehouse is None

	The user must pass either batch_no or batch_no + warehouse or item_code + warehouse

	:param batch_no: Optional - give qty for this batch no
	:param warehouse: Optional - give qty for this warehouse
	:param item_code: Optional - give qty for this item'''
	out = 0
	if batch_no and warehouse:
		out = float(frappe.db.sql("""select sum(actual_qty)
			from `tabStock Ledger Entry`
			where warehouse=%s and batch_no=%s""",
			(warehouse, batch_no))[0][0] or 0)

	if batch_no and not warehouse:
		out = frappe.db.sql('''select warehouse, sum(actual_qty) as qty
			from `tabStock Ledger Entry`
			where batch_no=%s
			group by warehouse''', batch_no, as_dict=1)

	if not batch_no and item_code and warehouse:
		out = frappe.db.sql('''select batch_no, sum(actual_qty) as qty
			from `tabStock Ledger Entry`
			where item_code = %s and warehouse=%s
			group by batch_no''', (item_code, warehouse), as_dict=1)

	return out

@frappe.whitelist()
def get_batches_by_oldest(item_code, warehouse):
	'''Returns the oldest batch and qty for the given item_code and warehouse'''
	batches = get_batch_qty(item_code = item_code, warehouse = warehouse)
	batches_dates = [[batch, frappe.get_value('Batch', batch.batch_no, 'expiry_date')] for batch in batches]
	batches_dates.sort(key=lambda tup: tup[1])
	return batches_dates

@frappe.whitelist()
def split_batch(batch_no, item_code, warehouse, qty, new_batch_id = None):
	'''Split the batch into a new batch'''
	batch = frappe.get_doc(dict(doctype='Batch', item=item_code, batch_id=new_batch_id)).insert()
	stock_entry = frappe.get_doc(dict(
		doctype='Stock Entry',
		purpose='Repack',
		items=[
			dict(
				item_code = item_code,
				qty = float(qty or 0),
				s_warehouse = warehouse,
				batch_no = batch_no
			),
			dict(
				item_code = item_code,
				qty = float(qty or 0),
				t_warehouse = warehouse,
				batch_no = batch.name
			),
		]
	))
	stock_entry.insert()
	stock_entry.submit()

	return batch.name

def set_batch_nos(doc, warehouse_field, throw = False):
	'''Automatically select `batch_no` for outgoing items in item table'''
	for d in doc.items:
		qty = d.get('stock_qty') or d.get('transfer_qty') or d.get('qty') or 0
		has_batch_no = frappe.db.get_value('Item', d.item_code, 'has_batch_no')
		warehouse = d.get(warehouse_field, None)
		if has_batch_no and warehouse and qty > 0:
			if not d.batch_no:
				d.batch_no = get_batch_no(d.item_code, warehouse, qty, throw)
			else:
				batch_qty = get_batch_qty(batch_no=d.batch_no, warehouse=warehouse)
				if flt(batch_qty, d.precision("qty")) < flt(qty, d.precision("qty")):
					frappe.throw(_("Row #{0}: The batch {1} has only {2} qty. Please select another batch which has {3} qty available or split the row into multiple rows, to deliver/issue from multiple batches").format(d.idx, d.batch_no, batch_qty, qty))

@frappe.whitelist()
def get_batch_no(item_code, warehouse, qty=1, throw=False):
	"""
	Get batch number using First Expiring First Out method.
	:param item_code: `item_code` of Item Document
	:param warehouse: name of Warehouse to check
	:param qty: quantity of Items
	:return: String represent batch number of batch with sufficient quantity else an empty String
	"""

	batch_no = None
	batches = get_batches(item_code, warehouse, qty, throw)

	for batch in batches:
		if cint(qty) <= cint(batch.qty):
			batch_no = batch.batch_id
			break

	if not batch_no:
		frappe.msgprint(_('Please select a Batch for Item {0}. Unable to find a single batch that fulfills this requirement').format(frappe.bold(item_code)))
		if throw:
			raise UnableToSelectBatchError

	return batch_no


def get_batches(item_code, warehouse, qty=1, throw=False):
	batches = frappe.db.sql(
		'select batch_id, sum(actual_qty) as qty from `tabBatch` join `tabStock Ledger Entry` '
		'on `tabBatch`.batch_id = `tabStock Ledger Entry`.batch_no '
		'where `tabStock Ledger Entry`.item_code = %s and  `tabStock Ledger Entry`.warehouse = %s '
		'and (`tabBatch`.expiry_date >= CURDATE() or `tabBatch`.expiry_date IS NULL)'
		'group by batch_id '
		'order by `tabBatch`.expiry_date ASC, `tabBatch`.creation ASC',
		(item_code, warehouse),
		as_dict=True
	)

	return batches
