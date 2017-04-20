# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

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
def get_batch_qty(batch_no, warehouse=None):
	'''Returns batch actual qty if warehouse is passed, or returns dict of qty by warehouse if warehouse is None'''
	frappe.has_permission('Batch', throw=True)
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
	return out

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
