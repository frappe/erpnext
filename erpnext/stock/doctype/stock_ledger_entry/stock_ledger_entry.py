# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from datetime import date

import frappe
from frappe import _
from frappe.core.doctype.role.role import get_users
from frappe.model.document import Document
from frappe.utils import add_days, cint, formatdate, get_datetime, getdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.controllers.item_variant import ItemTemplateCannotHaveStock


class StockFreezeError(frappe.ValidationError):
	pass


class BackDatedStockTransaction(frappe.ValidationError):
	pass


exclude_from_linked_with = True


class StockLedgerEntry(Document):
	def autoname(self):
		"""
		Temporarily name doc for fast insertion
		name will be changed using autoname options (in a scheduled job)
		"""
		self.name = frappe.generate_hash(txt="", length=10)
		if self.meta.autoname == "hash":
			self.to_rename = 0

	def validate(self):
		self.flags.ignore_submit_comment = True
		from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company

		self.validate_mandatory()
		self.validate_item()
		self.validate_batch()
		validate_disabled_warehouse(self.warehouse)
		validate_warehouse_company(self.warehouse, self.company)
		self.scrub_posting_time()
		self.validate_and_set_fiscal_year()
		self.block_transactions_against_group_warehouse()
		self.validate_with_last_transaction_posting_time()

	def on_submit(self):
		self.check_stock_frozen_date()
		self.calculate_batch_qty()

		if not self.get("via_landed_cost_voucher"):
			from erpnext.stock.doctype.serial_no.serial_no import process_serial_no

			process_serial_no(self)

	def calculate_batch_qty(self):
		if self.batch_no:
			batch_qty = (
				frappe.db.get_value(
					"Stock Ledger Entry",
					{"docstatus": 1, "batch_no": self.batch_no, "is_cancelled": 0},
					"sum(actual_qty)",
				)
				or 0
			)
			frappe.db.set_value("Batch", self.batch_no, "batch_qty", batch_qty)

	def validate_mandatory(self):
		mandatory = ["warehouse", "posting_date", "voucher_type", "voucher_no", "company"]
		for k in mandatory:
			if not self.get(k):
				frappe.throw(_("{0} is required").format(self.meta.get_label(k)))

		if self.voucher_type != "Stock Reconciliation" and not self.actual_qty:
			frappe.throw(_("Actual Qty is mandatory"))

	def validate_item(self):
		item_det = frappe.db.sql(
			"""select name, item_name, has_batch_no, docstatus,
			is_stock_item, has_variants, stock_uom, create_new_batch
			from tabItem where name=%s""",
			self.item_code,
			as_dict=True,
		)

		if not item_det:
			frappe.throw(_("Item {0} not found").format(self.item_code))

		item_det = item_det[0]

		if item_det.is_stock_item != 1:
			frappe.throw(_("Item {0} must be a stock Item").format(self.item_code))

		# check if batch number is valid
		if item_det.has_batch_no == 1:
			batch_item = (
				self.item_code
				if self.item_code == item_det.item_name
				else self.item_code + ":" + item_det.item_name
			)
			if not self.batch_no:
				frappe.throw(_("Batch number is mandatory for Item {0}").format(batch_item))
			elif not frappe.db.get_value("Batch", {"item": self.item_code, "name": self.batch_no}):
				frappe.throw(
					_("{0} is not a valid Batch Number for Item {1}").format(self.batch_no, batch_item)
				)

		elif item_det.has_batch_no == 0 and self.batch_no and self.is_cancelled == 0:
			frappe.throw(_("The Item {0} cannot have Batch").format(self.item_code))

		if item_det.has_variants:
			frappe.throw(
				_("Stock cannot exist for Item {0} since has variants").format(self.item_code),
				ItemTemplateCannotHaveStock,
			)

		self.stock_uom = item_det.stock_uom

	def check_stock_frozen_date(self):
		stock_settings = frappe.get_cached_doc("Stock Settings")

		if stock_settings.stock_frozen_upto:
			if (
				getdate(self.posting_date) <= getdate(stock_settings.stock_frozen_upto)
				and stock_settings.stock_auth_role not in frappe.get_roles()
			):
				frappe.throw(
					_("Stock transactions before {0} are frozen").format(
						formatdate(stock_settings.stock_frozen_upto)
					),
					StockFreezeError,
				)

		stock_frozen_upto_days = cint(stock_settings.stock_frozen_upto_days)
		if stock_frozen_upto_days:
			older_than_x_days_ago = (
				add_days(getdate(self.posting_date), stock_frozen_upto_days) <= date.today()
			)
			if older_than_x_days_ago and stock_settings.stock_auth_role not in frappe.get_roles():
				frappe.throw(
					_("Not allowed to update stock transactions older than {0}").format(stock_frozen_upto_days),
					StockFreezeError,
				)

	def scrub_posting_time(self):
		if not self.posting_time or self.posting_time == "00:0":
			self.posting_time = "00:00"

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

			validate_fiscal_year(
				self.posting_date, self.fiscal_year, self.company, self.meta.get_label("posting_date"), self
			)

	def block_transactions_against_group_warehouse(self):
		from erpnext.stock.utils import is_group_warehouse

		is_group_warehouse(self.warehouse)

	def validate_with_last_transaction_posting_time(self):
		authorized_role = frappe.db.get_single_value(
			"Stock Settings", "role_allowed_to_create_edit_back_dated_transactions"
		)
		if authorized_role:
			authorized_users = get_users(authorized_role)
			if authorized_users and frappe.session.user not in authorized_users:
				last_transaction_time = frappe.db.sql(
					"""
					select MAX(timestamp(posting_date, posting_time)) as posting_time
					from `tabStock Ledger Entry`
					where docstatus = 1 and is_cancelled = 0 and item_code = %s
					and warehouse = %s""",
					(self.item_code, self.warehouse),
				)[0][0]

				cur_doc_posting_datetime = "%s %s" % (
					self.posting_date,
					self.get("posting_time") or "00:00:00",
				)

				if last_transaction_time and get_datetime(cur_doc_posting_datetime) < get_datetime(
					last_transaction_time
				):
					msg = _("Last Stock Transaction for item {0} under warehouse {1} was on {2}.").format(
						frappe.bold(self.item_code), frappe.bold(self.warehouse), frappe.bold(last_transaction_time)
					)

					msg += "<br><br>" + _(
						"You are not authorized to make/edit Stock Transactions for Item {0} under warehouse {1} before this time."
					).format(frappe.bold(self.item_code), frappe.bold(self.warehouse))

					msg += "<br><br>" + _("Please contact any of the following users to {} this transaction.")
					msg += "<br>" + "<br>".join(authorized_users)
					frappe.throw(msg, BackDatedStockTransaction, title=_("Backdated Stock Entry"))

	def on_cancel(self):
		msg = _("Individual Stock Ledger Entry cannot be cancelled.")
		msg += "<br>" + _("Please cancel related transaction.")
		frappe.throw(msg)


def on_doctype_update():
	if not frappe.db.has_index("tabStock Ledger Entry", "posting_sort_index"):
		frappe.db.commit()
		frappe.db.add_index(
			"Stock Ledger Entry",
			fields=["posting_date", "posting_time", "name"],
			index_name="posting_sort_index",
		)

	frappe.db.add_index("Stock Ledger Entry", ["voucher_no", "voucher_type"])
	frappe.db.add_index("Stock Ledger Entry", ["batch_no", "item_code", "warehouse"])
	frappe.db.add_index("Stock Ledger Entry", ["warehouse", "item_code"], "item_warehouse")
