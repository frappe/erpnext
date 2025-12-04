# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.desk.form.load import get_attachments
from frappe.exceptions import QueryDeadlockError, QueryTimeoutError
from frappe.model.document import Document
from frappe.query_builder import DocType, Interval
from frappe.query_builder.functions import Max, Now
from frappe.utils import cint, get_link_to_form, get_weekday, getdate, now, nowtime
from frappe.utils.user import get_users_with_role
from rq.timeouts import JobTimeoutException

import erpnext
from erpnext.accounts.general_ledger import validate_accounting_period
from erpnext.accounts.utils import get_future_stock_vouchers, repost_gle_for_stock_vouchers
from erpnext.stock.stock_ledger import (
	get_affected_transactions,
	get_items_to_be_repost,
	repost_future_sle,
)

RecoverableErrors = (JobTimeoutException, QueryDeadlockError, QueryTimeoutError)


class RepostItemValuation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		affected_transactions: DF.Code | None
		allow_negative_stock: DF.Check
		allow_zero_rate: DF.Check
		amended_from: DF.Link | None
		based_on: DF.Literal["Transaction", "Item and Warehouse"]
		company: DF.Link | None
		current_index: DF.Int
		distinct_item_and_warehouse: DF.Code | None
		error_log: DF.LongText | None
		gl_reposting_index: DF.Int
		item_code: DF.Link | None
		items_to_be_repost: DF.Code | None
		posting_date: DF.Date
		posting_time: DF.Time | None
		recreate_stock_ledgers: DF.Check
		repost_only_accounting_ledgers: DF.Check
		reposting_data_file: DF.Attach | None
		reposting_reference: DF.Data | None
		status: DF.Literal["Queued", "In Progress", "Completed", "Skipped", "Failed"]
		total_reposting_count: DF.Int
		via_landed_cost_voucher: DF.Check
		voucher_no: DF.DynamicLink | None
		voucher_type: DF.Link | None
		warehouse: DF.Link | None
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days=None):
		days = days or 90
		table = DocType("Repost Item Valuation")
		frappe.db.delete(
			table,
			filters=(
				(table.creation < (Now() - Interval(days=days)))
				& (table.status.isin(["Completed", "Skipped"]))
			),
		)

	def validate(self):
		self.reset_repost_only_accounting_ledgers()
		self.set_company()
		self.validate_period_closing_voucher()
		self.set_status(write=False)
		self.reset_field_values()
		self.validate_accounts_freeze()
		self.reset_recreate_stock_ledgers()
		self.validate_recreate_stock_ledgers()

	def reset_repost_only_accounting_ledgers(self):
		if self.repost_only_accounting_ledgers and self.based_on != "Transaction":
			self.repost_only_accounting_ledgers = 0

	def validate_recreate_stock_ledgers(self):
		if not self.recreate_stock_ledgers:
			return

		items = []
		if self.based_on == "Item and Warehouse":
			items.append(self.item_code)
		else:
			items = get_items_to_be_repost(self.voucher_type, self.voucher_no)
			items = list(set([d.item_code for d in items]))

		if serial_batch_items := frappe.get_all(
			"Item", or_filters={"has_serial_no": 1, "has_batch_no": 1}, filters={"name": ("in", items)}
		):
			item_list = ", ".join([d.name for d in serial_batch_items])
			msg = _(
				"Since {0} are Serial No/Batch No items, you cannot enable 'Recreate Stock Ledgers' in Repost Item Valuation."
			).format(item_list)
			frappe.throw(msg)

	def validate_period_closing_voucher(self):
		# Period Closing Voucher
		year_end_date = self.get_max_period_closing_date(self.company)
		if year_end_date and getdate(self.posting_date) <= getdate(year_end_date):
			date = frappe.format(year_end_date, "Date")
			msg = f"Due to period closing, you cannot repost item valuation before {date}"
			frappe.throw(_(msg))

		# Accounting Period
		if self.voucher_type:
			validate_accounting_period(
				[
					frappe._dict(
						{
							"posting_date": self.posting_date,
							"company": self.company,
							"voucher_type": self.voucher_type,
						}
					)
				]
			)

		# Stock Closing Balance
		closing_stock = self.get_closing_stock_balance()
		if closing_stock and closing_stock[0].name:
			name = get_link_to_form("Stock Closing Entry", closing_stock[0].name)
			to_date = frappe.format(closing_stock[0].posting_date, "Date")
			frappe.throw(
				_("Due to stock closing entry {0}, you cannot repost item valuation before {1}").format(
					name, to_date
				)
			)

	def reset_recreate_stock_ledgers(self):
		if self.recreate_stock_ledgers and self.based_on != "Transaction":
			self.recreate_stock_ledgers = 0

	def get_closing_stock_balance(self):
		filters = {
			"company": self.company,
			"to_date": (">=", self.posting_date),
			"status": "Completed",
		}

		return frappe.get_all(
			"Stock Closing Entry", fields=["name", "to_date as posting_date"], filters=filters, limit=1
		)

	@staticmethod
	def get_max_period_closing_date(company):
		table = frappe.qb.DocType("Period Closing Voucher")

		query = (
			frappe.qb.from_(table)
			.select(Max(table.period_end_date))
			.where((table.company == company) & (table.docstatus == 1))
		).run()

		return query[0][0] if query and query[0][0] else None

	def validate_accounts_freeze(self):
		acc_frozen_till_date = frappe.db.get_value("Company", self.company, "accounts_frozen_till_date")
		frozen_accounts_modifier = frappe.db.get_value(
			"Company", self.company, "role_allowed_for_frozen_entries"
		)
		if not acc_frozen_till_date:
			return
		if getdate(self.posting_date) <= getdate(acc_frozen_till_date):
			if frozen_accounts_modifier and frappe.session.user in get_users_with_role(
				frozen_accounts_modifier
			):
				frappe.msgprint(_("Caution: This might alter frozen accounts."))
				return
			frappe.throw(_("You cannot repost item valuation before {}").format(acc_frozen_till_date))

	def reset_field_values(self):
		if self.based_on == "Transaction":
			self.item_code = None
			self.warehouse = None

		self.allow_negative_stock = 1

	def on_cancel(self):
		self.clear_attachment()

	def on_trash(self):
		self.clear_attachment()

	@frappe.whitelist()
	def set_company(self):
		if self.based_on == "Transaction":
			self.company = frappe.get_cached_value(self.voucher_type, self.voucher_no, "company")
		elif self.warehouse:
			self.company = frappe.get_cached_value("Warehouse", self.warehouse, "company")

	def set_status(self, status=None, write=True):
		status = status or self.status
		if not status:
			self.status = "Queued"
		else:
			self.status = status
		if write:
			self.db_set("status", self.status)

	def clear_attachment(self):
		if attachments := get_attachments(self.doctype, self.name):
			attachment = attachments[0]
			frappe.delete_doc("File", attachment.name, ignore_permissions=True)

		if self.reposting_data_file:
			self.db_set("reposting_data_file", None)

	def on_submit(self):
		"""During tests reposts are executed immediately.

		Exceptions:
		        1. "Repost Item Valuation" document has self.flags.dont_run_in_test
		        2. global flag frappe.flags.dont_execute_stock_reposts is set

		        These flags are useful for asserting real time behaviour like quantity updates.
		"""

		if not frappe.in_test:
			return
		if self.flags.dont_run_in_test or frappe.flags.dont_execute_stock_reposts:
			return

		repost(self)

	def before_cancel(self):
		self.check_pending_repost_against_cancelled_transaction()

	def check_pending_repost_against_cancelled_transaction(self):
		if self.status not in ("Queued", "In Progress"):
			return

		msg = _("Cannot cancel as processing of cancelled documents is pending.")
		msg += "<br>" + _("Please try again in an hour.")
		frappe.throw(msg, title=_("Pending processing"))

	@frappe.whitelist()
	def restart_reposting(self):
		self.set_status("Queued", write=False)
		self.current_index = 0
		self.distinct_item_and_warehouse = None
		self.items_to_be_repost = None
		self.gl_reposting_index = 0
		self.total_reposting_count = 0
		self.clear_attachment()
		self.db_update()

	def skipped_similar_reposts(self):
		repost_entries = frappe.get_all(
			"Repost Item Valuation",
			filters={
				"based_on": "Transaction",
				"voucher_type": self.voucher_type,
				"voucher_no": self.voucher_no,
				"docstatus": 1,
				"repost_only_accounting_ledgers": 1,
				"status": "Queued",
				"reposting_reference": ("is", "set"),
			},
			fields=["name", "reposting_reference"],
		)

		for entry in repost_entries:
			if (
				frappe.db.get_value("Repost Item Valuation", entry.reposting_reference, "status")
				== "Completed"
			):
				frappe.db.set_value("Repost Item Valuation", entry.name, "status", "Skipped")

	def deduplicate_similar_repost(self):
		"""Deduplicate similar reposts based on item-warehouse-posting combination."""

		if self.repost_only_accounting_ledgers:
			self.skipped_similar_reposts()
			return

		if self.based_on != "Item and Warehouse":
			return

		filters = {
			"item_code": self.item_code,
			"warehouse": self.warehouse,
			"name": self.name,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
		}

		frappe.db.sql(
			"""
			update `tabRepost Item Valuation`
			set status = 'Skipped'
			WHERE item_code = %(item_code)s
				and warehouse = %(warehouse)s
				and name != %(name)s
				and TIMESTAMP(posting_date, posting_time) > TIMESTAMP(%(posting_date)s, %(posting_time)s)
				and docstatus = 1
				and status = 'Queued'
				and based_on = 'Item and Warehouse'
				""",
			filters,
		)

	def recreate_stock_ledger_entries(self):
		"""Recreate Stock Ledger Entries for the transaction."""
		if self.based_on == "Transaction" and self.recreate_stock_ledgers:
			doc = frappe.get_doc(self.voucher_type, self.voucher_no)
			doc.db_set("docstatus", 2)
			doc.update_stock_ledger(allow_negative_stock=True)

			doc.db_set("docstatus", 1)
			doc.update_stock_ledger(allow_negative_stock=True)


@frappe.whitelist()
def bulk_restart_reposting(names):
	names = json.loads(names)
	for name in names:
		doc = frappe.get_doc("Repost Item Valuation", name)
		if doc.status != "Failed":
			continue

		doc.restart_reposting()

	frappe.msgprint(_("Repost Item Valuation restarted for selected failed records."))


def on_doctype_update():
	frappe.db.add_index("Repost Item Valuation", ["warehouse", "item_code"], "item_warehouse")


def repost(doc):
	try:
		frappe.flags.through_repost_item_valuation = True
		if not frappe.db.exists("Repost Item Valuation", doc.name):
			return

		# This is to avoid TooManyWritesError in case of large reposts
		frappe.db.MAX_WRITES_PER_TRANSACTION *= 4

		doc.set_status("In Progress")
		if not frappe.in_test:
			frappe.db.commit()

		if doc.recreate_stock_ledgers:
			doc.recreate_stock_ledger_entries()

		if not doc.repost_only_accounting_ledgers:
			repost_sl_entries(doc)

		repost_gl_entries(doc)

		doc.set_status("Completed")
		doc.db_set("reposting_data_file", None)
		remove_attached_file(doc.name)

	except Exception as e:
		if frappe.in_test:
			# Don't silently fail in tests,
			# there is no reason for reposts to fail in CI
			raise

		frappe.db.rollback()
		traceback = frappe.get_traceback(with_context=True)
		doc.log_error("Unable to repost item valuation")

		message = frappe.message_log.pop() if frappe.message_log else ""
		if isinstance(message, dict):
			message = message.get("message")

		status = "Failed"
		# If failed because of timeout, set status to In Progress
		if traceback and ("timeout" in traceback.lower() or "Deadlock found" in traceback):
			status = "In Progress"

		if traceback:
			message += "<br><br>" + "<b>Traceback:</b> <br>" + traceback

		frappe.db.set_value(
			doc.doctype,
			doc.name,
			{
				"error_log": message,
				"status": status,
			},
		)

		if status == "Failed":
			outgoing_email_account = frappe.get_cached_value(
				"Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "name"
			)

			if outgoing_email_account and not isinstance(e, RecoverableErrors):
				notify_error_to_stock_managers(doc, message)
				doc.set_status("Failed")
	finally:
		if not frappe.in_test:
			frappe.db.commit()


def remove_attached_file(docname):
	if file_name := frappe.db.get_value(
		"File", {"attached_to_name": docname, "attached_to_doctype": "Repost Item Valuation"}, "name"
	):
		frappe.delete_doc("File", file_name, ignore_permissions=True, delete_permanently=True, force=True)


def repost_sl_entries(doc):
	if doc.based_on == "Transaction":
		repost_future_sle(
			voucher_type=doc.voucher_type,
			voucher_no=doc.voucher_no,
			allow_negative_stock=doc.allow_negative_stock,
			via_landed_cost_voucher=doc.via_landed_cost_voucher,
			doc=doc,
		)
	else:
		repost_future_sle(
			args=[
				frappe._dict(
					{
						"item_code": doc.item_code,
						"warehouse": doc.warehouse,
						"posting_date": doc.posting_date,
						"posting_time": doc.posting_time,
					}
				)
			],
			allow_negative_stock=doc.allow_negative_stock,
			via_landed_cost_voucher=doc.via_landed_cost_voucher,
			doc=doc,
		)


def repost_gl_entries(doc):
	if not cint(erpnext.is_perpetual_inventory_enabled(doc.company)):
		return

	if doc.repost_only_accounting_ledgers and doc.based_on == "Transaction":
		transactions = [(doc.voucher_type, doc.voucher_no)]
		repost_gle_for_stock_vouchers(
			transactions,
			doc.posting_date,
			doc.company,
			repost_doc=doc,
		)
		return

	# directly modified transactions
	directly_dependent_transactions = _get_directly_dependent_vouchers(doc)
	repost_affected_transaction = get_affected_transactions(doc)

	transactions = directly_dependent_transactions + list(repost_affected_transaction)
	if doc.based_on == "Item and Warehouse" and not doc.repost_only_accounting_ledgers:
		make_reposting_for_accounting_ledgers(
			transactions,
			doc.company,
			repost_doc=doc,
		)
	else:
		repost_gle_for_stock_vouchers(
			transactions,
			doc.posting_date,
			doc.company,
			repost_doc=doc,
		)


def _get_directly_dependent_vouchers(doc):
	"""Get stock vouchers that are directly affected by reposting
	i.e. any one item-warehouse is present in the stock transaction"""

	items = set()
	warehouses = set()

	if doc.based_on == "Transaction":
		ref_doc = frappe.get_lazy_doc(doc.voucher_type, doc.voucher_no)
		doc_items, doc_warehouses = ref_doc.get_items_and_warehouses()
		items.update(doc_items)
		warehouses.update(doc_warehouses)

		sles = get_items_to_be_repost(doc.voucher_type, doc.voucher_no)
		sle_items = {sle.item_code for sle in sles}
		sle_warehouses = {sle.warehouse for sle in sles}
		items.update(sle_items)
		warehouses.update(sle_warehouses)
	else:
		items.add(doc.item_code)
		warehouses.add(doc.warehouse)

	affected_vouchers = get_future_stock_vouchers(
		posting_date=doc.posting_date,
		posting_time=doc.posting_time,
		for_warehouses=list(warehouses),
		for_items=list(items),
		company=doc.company,
	)
	return affected_vouchers


def notify_error_to_stock_managers(doc, traceback):
	recipients = get_recipients()

	subject = _("Error while reposting item valuation")
	message = (
		_("Hi,")
		+ "<br>"
		+ _("An error has been appeared while reposting item valuation via {0}").format(
			get_link_to_form(doc.doctype, doc.name)
		)
		+ "<br>"
		+ _(
			"Please check the error message and take necessary actions to fix the error and then restart the reposting again."
		)
	)
	frappe.sendmail(recipients=recipients, subject=subject, message=message)


def get_recipients():
	role = (
		frappe.db.get_single_value("Stock Reposting Settings", "notify_reposting_error_to_role")
		or "Stock Manager"
	)

	recipients = get_users_with_role(role)

	return recipients


def repost_entries():
	"""
	Reposts 'Repost Item Valuation' entries in queue.
	Called hourly via hooks.py.
	"""
	if not in_configured_timeslot():
		return

	riv_entries = get_repost_item_valuation_entries()

	for row in riv_entries:
		doc = frappe.get_doc("Repost Item Valuation", row.name)
		if (
			doc.repost_only_accounting_ledgers
			and doc.reposting_reference
			and frappe.db.get_value("Repost Item Valuation", doc.reposting_reference, "status") != "Completed"
		):
			continue

		if doc.status in ("Queued", "In Progress"):
			repost(doc)
			doc.deduplicate_similar_repost()


def get_repost_item_valuation_entries():
	return frappe.db.sql(
		""" SELECT name from `tabRepost Item Valuation`
		WHERE status in ('Queued', 'In Progress') and creation <= %s and docstatus = 1
		ORDER BY timestamp(posting_date, posting_time) asc, creation asc, status asc
	""",
		now(),
		as_dict=1,
	)


def in_configured_timeslot(repost_settings=None, current_time=None):
	"""Check if current time is in configured timeslot for reposting."""

	if repost_settings is None:
		repost_settings = frappe.get_cached_doc("Stock Reposting Settings")

	if not repost_settings.limit_reposting_timeslot:
		return True

	if get_weekday() == repost_settings.limits_dont_apply_on:
		return True

	start_time = repost_settings.start_time
	end_time = repost_settings.end_time

	now_time = current_time or nowtime()

	if start_time < end_time:
		return end_time >= now_time >= start_time
	else:
		return now_time >= start_time or now_time <= end_time


@frappe.whitelist()
def execute_repost_item_valuation():
	"""Execute repost item valuation via scheduler."""
	if name := frappe.db.get_value(
		"Scheduled Job Type",
		{"method": "erpnext.stock.doctype.repost_item_valuation.repost_item_valuation.repost_entries"},
		"name",
	):
		frappe.get_doc("Scheduled Job Type", name).enqueue(force=True)


def make_reposting_for_accounting_ledgers(transactions, company, repost_doc):
	for voucher_type, voucher_no in transactions:
		if frappe.db.exists(
			"Repost Item Valuation",
			{
				"voucher_type": voucher_type,
				"voucher_no": voucher_no,
				"docstatus": 1,
				"reposting_reference": repost_doc.name,
				"repost_only_accounting_ledgers": 1,
				"status": "Queued",
			},
		):
			continue

		new_repost_doc = frappe.new_doc("Repost Item Valuation")
		new_repost_doc.company = company
		new_repost_doc.voucher_type = voucher_type
		new_repost_doc.voucher_no = voucher_no
		new_repost_doc.repost_only_accounting_ledgers = 1
		new_repost_doc.reposting_reference = repost_doc.name
		new_repost_doc.flags.ignore_permissions = True
		new_repost_doc.submit()
