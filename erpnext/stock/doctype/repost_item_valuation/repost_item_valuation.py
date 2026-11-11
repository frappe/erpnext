# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.desk.form.load import get_attachments
from frappe.exceptions import QueryDeadlockError, QueryTimeoutError
from frappe.model.document import Document
from frappe.query_builder import Tuple
from frappe.query_builder.functions import CombineDatetime, Max
from frappe.utils import (
	add_days,
	cint,
	get_link_to_form,
	get_weekday,
	getdate,
	now,
	nowtime,
	to_timedelta,
)
from frappe.utils.user import get_users_with_role
from rq.timeouts import JobTimeoutException

import erpnext
from erpnext.accounts.doctype.accounting_period.accounting_period import ClosedAccountingPeriod
from erpnext.accounts.general_ledger import validate_accounting_period
from erpnext.accounts.utils import get_future_stock_vouchers, repost_gle_for_stock_vouchers
from erpnext.projects.doctype.project.project import update_consumed_material_cost_for_vouchers
from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import check_stock_frozen_date
from erpnext.stock.stock_ledger import (
	get_affected_transactions,
	get_items_to_be_repost,
	get_reposting_data,
	is_transfer_stock_entry,
	repost_future_sle,
)
from erpnext.stock.utils import get_combine_datetime
from erpnext.utilities import clear_logs_with_references

RecoverableErrors = (JobTimeoutException, QueryDeadlockError, QueryTimeoutError)

MERGED_REPOST_LIMIT = 500


class RepostItemValuation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_negative_stock: DF.Check
		allow_zero_rate: DF.Check
		amended_from: DF.Link | None
		based_on: DF.Literal["Transaction", "Item and Warehouse"]
		company: DF.Link | None
		current_index: DF.Int
		error_log: DF.LongText | None
		gl_reposting_index: DF.Int
		item_code: DF.Link | None
		items_to_be_repost: DF.Code | None
		posting_date: DF.Date
		posting_time: DF.Time | None
		recalculate_valuation_rate: DF.Check
		recreate_stock_ledgers: DF.Check
		reposting_data_file: DF.Attach | None
		reposting_reference: DF.Data | None
		status: DF.Literal["Queued", "In Progress", "Completed", "Skipped", "Failed", "Cancelled"]
		total_reposting_count: DF.Int
		total_vouchers: DF.Int
		via_landed_cost_voucher: DF.Check
		voucher_no: DF.DynamicLink | None
		voucher_type: DF.Link | None
		vouchers_posted: DF.Int
		warehouse: DF.Link | None
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days=None):
		days = days or 90
		clear_logs_with_references(
			"Repost Item Valuation",
			{
				"modified": ("<", add_days(now(), -days)),
				"status": ("in", ["Completed", "Skipped"]),
			},
		)

	def repost_now(self):
		repost(self)

	def validate(self):
		self.set_default_posting_time()
		self.set_company()
		self.validate_update_stock()
		self.validate_recalculate_valuation_rate()
		self.validate_period_closing_voucher()
		self.validate_later_vouchers_in_closed_period()
		self.set_status(write=False)
		self.reset_field_values()
		self.validate_accounts_freeze()
		check_stock_frozen_date(self.posting_date)
		self.reset_recreate_stock_ledgers()
		self.validate_recreate_stock_ledgers()

	def set_default_posting_time(self):
		if self.posting_time is None:
			self.posting_time = nowtime()

		if not self.posting_date:
			frappe.throw(_("Posting date is required"))

	def validate_update_stock(self):
		if self.voucher_type in ["Sales Invoice", "Purchase Invoice"]:
			update_stock = frappe.get_value(self.voucher_type, self.voucher_no, "update_stock")
			if not update_stock:
				msg = _(
					"Since {0} has 'Update Stock' disabled, you cannot create repost item valuation against it"
				).format(get_link_to_form(self.voucher_type, self.voucher_no))
				frappe.throw(msg)

	def validate_recalculate_valuation_rate(self):
		if self.recalculate_valuation_rate and not self.can_recalculate_valuation_rate():
			frappe.throw(
				_(
					"Recalculate Valuation Rate is only allowed for a Purchase Receipt, a Purchase Invoice with Update Stock or a Stock Entry with no row that has both a Source and Target Warehouse"
				)
			)

	def can_recalculate_valuation_rate(self):
		if self.based_on != "Transaction":
			return False

		if self.voucher_type == "Purchase Receipt":
			return True

		if self.voucher_type == "Purchase Invoice":
			return bool(frappe.db.get_value("Purchase Invoice", self.voucher_no, "update_stock"))

		if self.voucher_type == "Stock Entry":
			return not is_transfer_stock_entry(self.voucher_no)

		return False

	def validate_recreate_stock_ledgers(self):
		if not self.recreate_stock_ledgers:
			return

		items = []
		if self.based_on == "Item and Warehouse":
			items.append(self.item_code)
		else:
			items = [d.item_code for d in get_items_to_be_repost(self.voucher_type, self.voucher_no)]
			# the voucher's stock ledger entries may be the ones to recreate, so they can be missing
			items += frappe.get_all(
				"Serial and Batch Bundle",
				filters={
					"voucher_type": self.voucher_type,
					"voucher_no": self.voucher_no,
					"docstatus": 1,
					"is_cancelled": 0,
				},
				pluck="item_code",
			)
			items = list(set(items))

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

		# Closing Stock Balance
		closing_stock = self.get_closing_stock_balance()
		if closing_stock and closing_stock[0].name:
			name = get_link_to_form("Closing Stock Balance", closing_stock[0].name)
			to_date = frappe.format(closing_stock[0].to_date, "Date")
			msg = f"Due to closing stock balance {name}, you cannot repost item valuation before {to_date}"
			frappe.throw(_(msg))

	def validate_later_vouchers_in_closed_period(self):
		if not cint(erpnext.is_perpetual_inventory_enabled(self.company)):
			return

		item_warehouses = self.get_item_warehouses_to_repost()
		if not item_warehouses:
			return

		if voucher := self.get_later_voucher_in_closed_period(item_warehouses):
			frappe.throw(
				_(
					"Cannot repost item valuation from {0} because {1} {2} falls in the closed Accounting Period {3}"
				).format(
					frappe.bold(frappe.format(self.posting_date, "Date")),
					voucher.voucher_type,
					get_link_to_form(voucher.voucher_type, voucher.voucher_no),
					frappe.bold(voucher.accounting_period),
				),
				ClosedAccountingPeriod,
			)

	def get_item_warehouses_to_repost(self):
		if self.based_on == "Transaction":
			rows = get_items_to_be_repost(self.voucher_type, self.voucher_no)
			return list({(row.item_code, row.warehouse) for row in rows})

		if self.item_code and self.warehouse:
			return [(self.item_code, self.warehouse)]

		return []

	def get_later_voucher_in_closed_period(self, item_warehouses):
		sle = frappe.qb.DocType("Stock Ledger Entry")
		period = frappe.qb.DocType("Accounting Period")
		closed_document = frappe.qb.DocType("Closed Document")

		query = (
			frappe.qb.from_(sle)
			.inner_join(period)
			.on(
				(period.company == sle.company)
				& (sle.posting_date.between(period.start_date, period.end_date))
			)
			.inner_join(closed_document)
			.on((closed_document.parent == period.name) & (closed_document.document_type == sle.voucher_type))
			.select(sle.voucher_type, sle.voucher_no, period.name.as_("accounting_period"))
			.where(
				(sle.is_cancelled == 0)
				& (sle.company == self.company)
				& (sle.posting_datetime >= get_combine_datetime(self.posting_date, self.posting_time))
				& (Tuple(sle.item_code, sle.warehouse).isin(item_warehouses))
				& (closed_document.closed == 1)
			)
			.limit(1)
		)

		if self.voucher_no:
			query = query.where(sle.voucher_no != self.voucher_no)

		result = query.run(as_dict=True)
		return result[0] if result else None

	def reset_recreate_stock_ledgers(self):
		if self.recreate_stock_ledgers and self.based_on != "Transaction":
			self.recreate_stock_ledgers = 0

	def get_closing_stock_balance(self):
		filters = {
			"company": self.company,
			"status": "Completed",
			"docstatus": 1,
			"to_date": (">=", self.posting_date),
		}

		for field in ["warehouse", "item_code"]:
			if self.get(field):
				filters.update({field: ("in", ["", self.get(field)])})

		return frappe.get_all("Closing Stock Balance", fields=["name", "to_date"], filters=filters)

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
		acc_settings = frappe.db.get_value(
			"Accounts Settings",
			"Accounts Settings",
			["acc_frozen_upto", "frozen_accounts_modifier"],
			as_dict=1,
		)
		if not acc_settings.acc_frozen_upto:
			return
		if getdate(self.posting_date) <= getdate(acc_settings.acc_frozen_upto):
			if acc_settings.frozen_accounts_modifier and frappe.session.user in get_users_with_role(
				acc_settings.frozen_accounts_modifier
			):
				frappe.msgprint(_("Caution: This might alter frozen accounts."))
				return
			frappe.throw(_("You cannot repost item valuation before {}").format(acc_settings.acc_frozen_upto))

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
		self.check_permission("write")

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

		if not frappe.flags.in_test:
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

	@frappe.whitelist(methods=["POST"])
	def restart_reposting(self):
		self.load_from_db()
		self.check_permission("write")
		if self.docstatus != 1 or self.status != "Failed":
			frappe.throw(_("Only a submitted Repost Item Valuation with status Failed can be restarted"))

		self.set_status("Queued", write=False)
		self.current_index = 0
		self.distinct_item_and_warehouse = None
		self.items_to_be_repost = None
		self.gl_reposting_index = 0
		self.total_reposting_count = 0
		self.total_vouchers = 0
		self.vouchers_posted = 0
		self.clear_attachment()
		self.db_update()

	def deduplicate_similar_repost(self):
		"""Deduplicate similar reposts based on item-warehouse-posting combination."""
		if self.based_on != "Item and Warehouse":
			return

		filters = {
			"item_code": self.item_code,
			"warehouse": self.warehouse,
			"name": self.name,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			"repost_started_at": self.get_repost_started_at(),
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
				and creation <= %(repost_started_at)s
				""",
			filters,
		)

	def get_repost_started_at(self):
		return self.flags.repost_started_at or now()

	def get_saved_repost_started_at(self):
		if self.reposting_data_file:
			return get_reposting_data(self.reposting_data_file).get("repost_started_at")

	def merge_queued_item_reposts(self):
		"""Carry later queued Item and Warehouse reposts of the company in this repost's walk.

		Reposts that start from different items often walk the same dependants, so one pass
		reposts each shared entry once instead of once per repost.
		"""
		if not self.can_merge_queued_item_reposts():
			return

		merged = get_mergeable_item_reposts(self)
		if not merged:
			return

		items = [get_repost_item(row) for row in [self, *merged]]
		self.db_set("items_to_be_repost", frappe.as_json(items))

	def can_merge_queued_item_reposts(self):
		return (
			self.based_on == "Item and Warehouse"
			and not self.items_to_be_repost
			and not self.reposting_data_file
			and not self.via_landed_cost_voucher
			and not has_failed_merged_repost(self.company)
		)

	def get_item_reposts(self):
		"""This repost's item-warehouse, followed by those of the reposts merged into it."""
		items = json.loads(self.items_to_be_repost or "[]")
		if len(items) > 1:
			return [frappe._dict(row) for row in items]

		return [get_repost_item(self)]

	def skip_merged_reposts(self):
		merged = [row.repost_item_valuation for row in self.get_item_reposts()[1:]]
		if self.based_on != "Item and Warehouse" or not merged:
			return

		riv = frappe.qb.DocType("Repost Item Valuation")
		(
			frappe.qb.update(riv)
			.set(riv.status, "Skipped")
			.where(riv.name.isin(merged) & (riv.status == "Queued"))
		).run()

	def _recalculate_valuation_rate(self):
		doc = frappe.get_doc(self.voucher_type, self.voucher_no)
		if doc.get("is_internal_supplier"):
			doc.set_sales_incoming_rate_for_internal_transfer()

		doc.update_valuation_rate()
		for item in doc.items:
			item.db_set("valuation_rate", item.valuation_rate)

	def recreate_stock_ledger_entries(self):
		"""Recreate Stock Ledger Entries for the transaction."""
		if self.based_on == "Transaction" and self.recreate_stock_ledgers:
			doc = frappe.get_doc(self.voucher_type, self.voucher_no)
			doc.db_set("docstatus", 2)
			doc.update_stock_ledger(allow_negative_stock=True)

			doc.db_set("docstatus", 1)
			doc.update_stock_ledger(allow_negative_stock=True)


def has_failed_merged_repost(company):
	failed = frappe.get_all(
		"Repost Item Valuation",
		filters={
			"company": company,
			"based_on": "Item and Warehouse",
			"status": "Failed",
			"docstatus": 1,
			"items_to_be_repost": ("is", "set"),
		},
		pluck="items_to_be_repost",
	)
	return any(len(json.loads(items)) > 1 for items in failed)


def get_mergeable_item_reposts(doc):
	riv = frappe.qb.DocType("Repost Item Valuation")
	return (
		frappe.qb.from_(riv)
		.select(riv.name, riv.item_code, riv.warehouse, riv.posting_date, riv.posting_time)
		.where(
			(riv.name != doc.name)
			# the walk starts this item-warehouse at doc's date, so an earlier repost of it would be lost
			& ((riv.item_code != doc.item_code) | (riv.warehouse != doc.warehouse))
			& (riv.based_on == "Item and Warehouse")
			& (riv.status == "Queued")
			& (riv.docstatus == 1)
			& (riv.company == doc.company)
			& (riv.creation <= doc.get_repost_started_at())
			& (riv.allow_negative_stock == doc.allow_negative_stock)
			& (riv.allow_zero_rate == doc.allow_zero_rate)
			& (riv.via_landed_cost_voucher == 0)
			& (riv.recalculate_valuation_rate == 0)
			& (riv.recreate_stock_ledgers == 0)
		)
		.orderby(CombineDatetime(riv.posting_date, riv.posting_time))
		.orderby(riv.creation)
		.limit(MERGED_REPOST_LIMIT)
	).run(as_dict=True)


def get_repost_item(row):
	return frappe._dict(
		item_code=row.item_code,
		warehouse=row.warehouse,
		posting_date=row.posting_date,
		posting_time=row.posting_time,
		posting_datetime=get_combine_datetime(row.posting_date, row.posting_time),
		repost_item_valuation=row.name,
	)


def on_doctype_update():
	frappe.db.add_index("Repost Item Valuation", ["warehouse", "item_code"], "item_warehouse")


def repost(doc):
	try:
		frappe.flags.through_repost_item_valuation = True
		if not frappe.db.exists("Repost Item Valuation", doc.name):
			return

		# This is to avoid TooManyWritesError in case of large reposts
		frappe.db.MAX_WRITES_PER_TRANSACTION *= 4

		doc.flags.repost_started_at = doc.get_saved_repost_started_at() or now()
		doc.set_status("In Progress")
		doc.merge_queued_item_reposts()
		if not frappe.flags.in_test:
			# nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit -- background job saves progress or failure status
			frappe.db.commit()

		if (
			doc.voucher_type in ["Purchase Receipt", "Purchase Invoice", "Stock Entry"]
			and doc.recalculate_valuation_rate
		):
			doc._recalculate_valuation_rate()

		if doc.recreate_stock_ledgers:
			doc.recreate_stock_ledger_entries()

		repost_sl_entries(doc)
		vouchers = get_reposted_vouchers(doc)
		repost_gl_entries(doc, vouchers)
		update_consumed_material_cost_for_vouchers(vouchers)

		doc.skip_merged_reposts()

		doc.set_status("Completed")
		doc.db_set("reposting_data_file", None)
		remove_attached_file(doc.name)

	except Exception as e:
		if frappe.flags.in_test:
			# Don't silently fail in tests,
			# there is no reason for reposts to fail in CI
			raise

		frappe.db.rollback()
		traceback = frappe.get_traceback()
		doc.log_error("Unable to repost item valuation")

		message = frappe.message_log.pop() if frappe.message_log else ""
		if isinstance(message, dict):
			message = message.get("message")

		status = "Failed"
		# If failed because of a recoverable error (timeout, deadlock), set status to In Progress
		# so the scheduler automatically retries instead of leaving it permanently failed.
		# NOTE: isinstance check comes first because the traceback string matching is unreliable
		# when SIGALRM kills the process mid-C-extension (JobTimeoutException may not appear
		# in the traceback if the exception handler itself was interrupted).
		traceback_lower = traceback.lower() if traceback else ""
		if isinstance(e, RecoverableErrors) or (
			traceback_lower and ("timeout" in traceback_lower or "deadlock found" in traceback_lower)
		):
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

		if isinstance(e, JobTimeoutException):
			# Job's time is up; stop the caller from starting the next entry
			raise

		if status == "Failed":
			outgoing_email_account = frappe.get_cached_value(
				"Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "name"
			)

			if outgoing_email_account and not isinstance(e, RecoverableErrors):
				notify_error_to_stock_managers(doc, message)
				doc.set_status("Failed")
	finally:
		if not frappe.flags.in_test:
			# nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit -- background job saves progress or failure status
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
			allow_zero_rate=doc.allow_zero_rate,
		)
	else:
		repost_future_sle(
			items_to_be_repost=doc.get_item_reposts(),
			allow_negative_stock=doc.allow_negative_stock,
			via_landed_cost_voucher=doc.via_landed_cost_voucher,
			doc=doc,
			allow_zero_rate=doc.allow_zero_rate,
		)


def repost_gl_entries(doc, transactions: list):
	if not cint(erpnext.is_perpetual_inventory_enabled(doc.company)):
		return

	repost_gle_for_stock_vouchers(
		transactions,
		doc.posting_date,
		doc.company,
		repost_doc=doc,
	)


def get_reposted_vouchers(doc):
	return _get_directly_dependent_vouchers(doc) + list(get_affected_transactions(doc))


def _get_directly_dependent_vouchers(doc):
	"""Get stock vouchers that are directly affected by reposting
	i.e. any one item-warehouse is present in the stock transaction"""

	items = set()
	warehouses = set()

	if doc.based_on == "Transaction":
		ref_doc = frappe.get_doc(doc.voucher_type, doc.voucher_no)
		doc_items, doc_warehouses = ref_doc.get_items_and_warehouses()
		items.update(doc_items)
		warehouses.update(doc_warehouses)

		sles = get_items_to_be_repost(doc.voucher_type, doc.voucher_no)
		sle_items = {sle.item_code for sle in sles}
		sle_warehouses = {sle.warehouse for sle in sles}
		items.update(sle_items)
		warehouses.update(sle_warehouses)
	else:
		for row in doc.get_item_reposts():
			items.add(row.item_code)
			warehouses.add(row.warehouse)

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
		if doc.status in ("Queued", "In Progress"):
			repost(doc)
			doc.deduplicate_similar_repost()

	riv_entries = get_repost_item_valuation_entries()
	if riv_entries:
		return


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

	start_time = to_timedelta(repost_settings.start_time)
	end_time = to_timedelta(repost_settings.end_time)

	now_time = to_timedelta(current_time or nowtime())

	if start_time < end_time:
		return end_time >= now_time >= start_time
	else:
		return now_time >= start_time or now_time <= end_time


@frappe.whitelist(methods=["POST"])
def execute_repost_item_valuation():
	"""Execute repost item valuation via scheduler."""
	# Force-enqueues the site-wide reposting job, so it needs write on Repost Item Valuation.
	frappe.has_permission("Repost Item Valuation", "write", throw=True)

	if not in_configured_timeslot():
		frappe.msgprint(
			_("Reposting will start within the timeslot configured in {0}").format(
				get_link_to_form("Stock Reposting Settings", "Stock Reposting Settings")
			)
		)
		return False

	frappe.get_doc("Scheduled Job Type", "repost_item_valuation.repost_entries").enqueue(force=True)

	return True
