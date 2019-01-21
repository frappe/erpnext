
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, formatdate
from frappe.model.document import Document
from datetime import date
from erpnext.controllers.item_variant import ItemTemplateCannotHaveStock
from erpnext.accounts.utils import get_fiscal_year

class StockFreezeError(frappe.ValidationError): pass

exclude_from_linked_with = True

class StockLedgerEntry(Document):
	def autoname(self):
		"""
		Temporarily name doc for fast insertion
		name will be changed using autoname options (in a scheduled job)
		"""
		self.name = frappe.generate_hash(txt="", length=10)

	def validate(self):
		self.flags.ignore_submit_comment = True
		from erpnext.stock.utils import validate_warehouse_company
		self.validate_mandatory()
		self.validate_item()
		self.validate_batch()
		validate_warehouse_company(self.warehouse, self.company)
		self.scrub_posting_time()
		self.validate_and_set_fiscal_year()
		self.block_transactions_against_group_warehouse()

	def on_submit(self):
		self.check_stock_frozen_date()
		self.actual_amt_check()

		if not self.get("via_landed_cost_voucher") and self.voucher_type != 'Stock Reconciliation':
			from erpnext.stock.doctype.serial_no.serial_no import process_serial_no
			process_serial_no(self)

	#check for item quantity available in stock
	def actual_amt_check(self):
		if self.batch_no and not self.get("allow_negative_stock"):
			batch_bal_after_transaction = flt(frappe.db.sql("""select sum(actual_qty)
				from `tabStock Ledger Entry`
				where warehouse=%s and item_code=%s and batch_no=%s""",
				(self.warehouse, self.item_code, self.batch_no))[0][0])

			if batch_bal_after_transaction < 0:
				frappe.throw(_("Stock balance in Batch {0} will become negative {1} for Item {2} at Warehouse {3}")
					.format(self.batch_no, batch_bal_after_transaction, self.item_code, self.warehouse))

	def validate_mandatory(self):
		mandatory = ['warehouse','posting_date','voucher_type','voucher_no','company']
		for k in mandatory:
			if not self.get(k):
				frappe.throw(_("{0} is required").format(self.meta.get_label(k)))

		if self.voucher_type != "Stock Reconciliation" and not self.actual_qty:
			frappe.throw(_("Actual Qty is mandatory"))

	def validate_item(self):
		item_det = frappe.db.sql("""select name, has_batch_no, docstatus,
			is_stock_item, has_variants, stock_uom, create_new_batch
			from tabItem where name=%s""", self.item_code, as_dict=True)

		if not item_det:
			frappe.throw(_("Item {0} not found").format(self.item_code))

		item_det = item_det[0]

		if item_det.is_stock_item != 1:
			frappe.throw(_("Item {0} must be a stock Item").format(self.item_code))

		# check if batch number is required
		if self.voucher_type != 'Stock Reconciliation':
			if item_det.has_batch_no ==1:
				if not self.batch_no:
					frappe.throw(_("Batch number is mandatory for Item {0}").format(self.item_code))
				elif not frappe.db.get_value("Batch",{"item": self.item_code, "name": self.batch_no}):
					frappe.throw(_("{0} is not a valid Batch Number for Item {1}").format(self.batch_no, self.item_code))

			elif item_det.has_batch_no ==0 and self.batch_no and self.is_cancelled == "No":
				frappe.throw(_("The Item {0} cannot have Batch").format(self.item_code))

		if item_det.has_variants:
			frappe.throw(_("Stock cannot exist for Item {0} since has variants").format(self.item_code),
				ItemTemplateCannotHaveStock)

		self.stock_uom = item_det.stock_uom

	def check_stock_frozen_date(self):
		stock_frozen_upto = frappe.db.get_value('Stock Settings', None, 'stock_frozen_upto') or ''
		if stock_frozen_upto:
			stock_auth_role = frappe.db.get_value('Stock Settings', None,'stock_auth_role')
			if getdate(self.posting_date) <= getdate(stock_frozen_upto) and not stock_auth_role in frappe.get_roles():
				frappe.throw(_("Stock transactions before {0} are frozen").format(formatdate(stock_frozen_upto)), StockFreezeError)

		stock_frozen_upto_days = int(frappe.db.get_value('Stock Settings', None, 'stock_frozen_upto_days') or 0)
		if stock_frozen_upto_days:
			stock_auth_role = frappe.db.get_value('Stock Settings', None,'stock_auth_role')
			older_than_x_days_ago = (add_days(getdate(self.posting_date), stock_frozen_upto_days) <= date.today())
			if older_than_x_days_ago and not stock_auth_role in frappe.get_roles():
				frappe.throw(_("Not allowed to update stock transactions older than {0}").format(stock_frozen_upto_days), StockFreezeError)

	def scrub_posting_time(self):
		if not self.posting_time or self.posting_time == '00:0':
			self.posting_time = '00:00'

	def validate_batch(self):
		if self.batch_no and self.voucher_type != "Stock Entry":
			expiry_date = frappe.db.get_value("Batch", self.batch_no, "expiry_date")
			if expiry_date:
				if getdate(self.posting_date) > getdate(expiry_date):
					frappe.throw(_("Batch {0} of Item {1} has expired.").format(self.batch_no, self.item_code))

	def validate_and_set_fiscal_year(self):
		if not self.fiscal_year:
			self.fiscal_year = get_fiscal_year(self.posting_date, company=self.company)[0]
		else:
			from erpnext.accounts.utils import validate_fiscal_year
			validate_fiscal_year(self.posting_date, self.fiscal_year, self.company,
				self.meta.get_label("posting_date"), self)

	def block_transactions_against_group_warehouse(self):
		from erpnext.stock.utils import is_group_warehouse
		is_group_warehouse(self.warehouse)

def on_doctype_update():
	if not frappe.db.has_index('tabStock Ledger Entry', 'posting_sort_index'):
		frappe.db.commit()
		frappe.db.add_index("Stock Ledger Entry",
			fields=["posting_date", "posting_time", "name"],
			index_name="posting_sort_index")

	frappe.db.add_index("Stock Ledger Entry", ["voucher_no", "voucher_type"])
	frappe.db.add_index("Stock Ledger Entry", ["batch_no", "item_code", "warehouse"])

