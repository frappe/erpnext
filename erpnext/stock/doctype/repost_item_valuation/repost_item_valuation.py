# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.form.load import get_attachments
from frappe.exceptions import QueryDeadlockError, QueryTimeoutError
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.query_builder.functions import CombineDatetime, Max
from frappe.utils import (
	add_days,
	cint,
	get_datetime,
	get_link_to_form,
	get_weekday,
	getdate,
	now,
	nowtime,
)
from frappe.utils.user import get_users_with_role
from rq.timeouts import JobTimeoutException

import erpnext
from erpnext.accounts.services.gl_validator import validate_accounting_period
from erpnext.accounts.utils import get_future_stock_vouchers, repost_gle_for_stock_vouchers
from erpnext.stock.stock_ledger import (
	get_affected_transactions,
	get_item_wh_first_reposted_from_reposting_data,
	get_items_to_be_repost,
	repost_future_sle,
)
from erpnext.stock.utils import get_combine_datetime
from erpnext.utilities import clear_logs_with_references

RecoverableErrors = (JobTimeoutException, QueryDeadlockError, QueryTimeoutError)


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
		repost_only_accounting_ledgers: DF.Check
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
				"creation": ("<", add_days(now(), -days)),
				"status": ("in", ["Completed", "Skipped"]),
			},
		)

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def repost_now(self):
		repost(self)

	def validate(self):
		self.set_default_posting_time()
		self.reset_repost_only_accounting_ledgers()
		self.set_company()
		self.validate_update_stock()
		self.validate_period_closing_voucher()
		self.set_status(write=False)
		self.reset_field_values()
		self.validate_accounts_freeze()
		self.reset_recreate_stock_ledgers()
		self.validate_recreate_stock_ledgers()

	def set_default_posting_time(self):
		if self.posting_time is None:
			self.posting_time = nowtime()

		if not self.posting_date:
			frappe.throw(_("Posting date is required"))

	def reset_repost_only_accounting_ledgers(self):
		if self.repost_only_accounting_ledgers and self.based_on != "Transaction":
			self.repost_only_accounting_ledgers = 0

	def validate_update_stock(self):
		if (
			self.voucher_type in ["Sales Invoice", "Purchase Invoice"]
			and not self.repost_only_accounting_ledgers
		):
			update_stock = frappe.get_value(self.voucher_type, self.voucher_no, "update_stock")
			if not update_stock:
				msg = _(
					"Since {0} has 'Update Stock' disabled, you cannot create repost item valuation against it"
				).format(get_link_to_form(self.voucher_type, self.voucher_no))
				frappe.throw(msg)

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
			frappe.throw(_("You cannot repost item valuation before {0}").format(acc_frozen_till_date))

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
			frappe.delete_doc("File", attachment.name, ignore_permissions=True, force=True)

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
		self.total_vouchers = 0
		self.vouchers_posted = 0
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
			# If against same voucher there are multiple RIVs for accounting ledgers only, skip them
			self.skipped_similar_reposts()
			return

		if self.based_on != "Item and Warehouse":
			return

		riv = frappe.qb.DocType("Repost Item Valuation")
		(
			frappe.qb.update(riv)
			.set(riv.status, "Skipped")
			.where(
				(riv.item_code == self.item_code)
				& (riv.warehouse == self.warehouse)
				& (riv.name != self.name)
				# CombineDatetime on the column is portable (TIMESTAMP() is MySQL-only) and keeps the
				# original NULL semantics (rows with NULL posting_time stay excluded); the RHS is this
				# doc's own (always-set) posting datetime, computed in Python.
				& (
					CombineDatetime(riv.posting_date, riv.posting_time)
					> get_combine_datetime(self.posting_date, self.posting_time)
				)
				& (riv.docstatus == 1)
				& (riv.status == "Queued")
				& (riv.based_on == "Item and Warehouse")
			)
		).run()

	def skip_reposts_covered_by_dependents(self):
		if self.repost_only_accounting_ledgers:
			return

		coverage = get_item_wh_first_reposted_from_reposting_data(self)
		if not coverage:
			return

		source_datetime = get_combine_datetime(self.posting_date, self.posting_time)
		mark_covered_item_reposts(self.name, coverage, source_datetime)

		affected = get_affected_transactions(self)
		if affected:
			mark_covered_transaction_reposts(self, coverage, affected)

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


@frappe.whitelist()
def bulk_restart_reposting(names: str | list):
	names = frappe.parse_json(names)
	for name in names:
		doc = frappe.get_doc("Repost Item Valuation", name)
		if doc.status != "Failed":
			continue

		doc.restart_reposting()

	frappe.msgprint(_("Repost Item Valuation restarted for selected failed records."))


def repost_coverage_cache_key(name):
	return f"riv_dependent_coverage::{name}"


def get_queued_item_reposts(source_name, item_codes):
	return frappe.get_all(
		"Repost Item Valuation",
		filters={
			"name": ("!=", source_name),
			"based_on": "Item and Warehouse",
			"status": "Queued",
			"docstatus": 1,
			"recalculate_valuation_rate": 0,
			"recreate_stock_ledgers": 0,
			"via_landed_cost_voucher": 0,
			"item_code": ("in", item_codes),
		},
		fields=["name", "item_code", "warehouse", "posting_date", "posting_time"],
	)


def mark_covered_item_reposts(source_name, coverage, source_datetime):
	item_codes = {item_code for item_code, _ in coverage}

	for row in get_queued_item_reposts(source_name, list(item_codes)):
		from_datetime = coverage.get((row.item_code, row.warehouse))
		if not from_datetime:
			continue

		row_datetime = get_combine_datetime(row.posting_date, row.posting_time)
		if get_datetime(row_datetime) < get_datetime(source_datetime):
			continue

		if get_datetime(from_datetime) <= get_datetime(row_datetime):
			frappe.db.set_value("Repost Item Valuation", row.name, "status", "Skipped")


def get_queued_transaction_reposts(source_name, voucher_nos):
	return frappe.get_all(
		"Repost Item Valuation",
		filters={
			"name": ("!=", source_name),
			"based_on": "Transaction",
			"status": "Queued",
			"docstatus": 1,
			"repost_only_accounting_ledgers": 0,
			"recalculate_valuation_rate": 0,
			"recreate_stock_ledgers": 0,
			"via_landed_cost_voucher": 0,
			"voucher_no": ("in", list(voucher_nos)),
		},
		fields=["name", "voucher_type", "voucher_no", "posting_date", "posting_time"],
	)


def accumulate_repost_coverage(row_name, coverage, row_datetime):
	cache_key = repost_coverage_cache_key(row_name)
	acc = frappe.cache().get_value(cache_key) or {}

	for key, from_datetime in coverage.items():
		if get_datetime(from_datetime) > get_datetime(row_datetime):
			continue

		existing = acc.get(key)
		if not existing or get_datetime(from_datetime) < get_datetime(existing):
			acc[key] = from_datetime

	frappe.cache().set_value(cache_key, acc, expires_in_sec=86400)
	return acc


def get_repost_items_by_voucher(rows):
	voucher_nos = {row.voucher_no for row in rows}
	if not voucher_nos:
		return {}

	items_by_voucher = {}
	for sle in frappe.get_all(
		"Stock Ledger Entry",
		filters={"voucher_no": ("in", list(voucher_nos))},
		fields=["voucher_type", "voucher_no", "item_code", "warehouse"],
		distinct=True,
	):
		items_by_voucher.setdefault((sle.voucher_type, sle.voucher_no), set()).add(
			(sle.item_code, sle.warehouse)
		)

	return items_by_voucher


def is_transaction_repost_covered(items, acc, row_datetime):
	if not items:
		return False

	for key in items:
		covered = acc.get(key)
		if not covered or get_datetime(covered) > get_datetime(row_datetime):
			return False

	return True


def mark_covered_transaction_reposts(source, coverage, affected):
	source_datetime = get_combine_datetime(source.posting_date, source.posting_time)
	voucher_nos = {voucher_no for _, voucher_no in affected}

	rows = get_queued_transaction_reposts(source.name, voucher_nos)
	items_by_voucher = get_repost_items_by_voucher(rows)

	for row in rows:
		if (row.voucher_type, row.voucher_no) not in affected:
			continue

		row_datetime = get_combine_datetime(row.posting_date, row.posting_time)
		if get_datetime(row_datetime) < get_datetime(source_datetime):
			continue

		acc = accumulate_repost_coverage(row.name, coverage, row_datetime)
		items = items_by_voucher.get((row.voucher_type, row.voucher_no))
		if is_transaction_repost_covered(items, acc, row_datetime):
			frappe.db.set_value("Repost Item Valuation", row.name, "status", "Skipped")
			frappe.cache().delete_value(repost_coverage_cache_key(row.name))


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

		if (
			doc.voucher_type in ["Purchase Receipt", "Purchase Invoice", "Stock Entry"]
			and doc.recalculate_valuation_rate
		):
			doc._recalculate_valuation_rate()

		if doc.recreate_stock_ledgers:
			doc.recreate_stock_ledger_entries()

		if not doc.repost_only_accounting_ledgers:
			repost_sl_entries(doc)

		repost_gl_entries(doc)

		doc.skip_reposts_covered_by_dependents()

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

		# Recoverable errors (deadlock, lock/query timeout, job timeout) re-queue as In Progress.
		# Classify by type: the old traceback string-match only knew MariaDB's "Deadlock found" and
		# missed Postgres deadlocks ("deadlock detected"), failing them permanently.
		status = "In Progress" if isinstance(e, RecoverableErrors) else "Failed"

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

			# status == "Failed" already implies e is not recoverable, so no need to re-check here.
			if outgoing_email_account:
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
			items_to_be_repost=[
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

	# handle stock delivered but not billed ledger entries
	if frappe.get_cached_value("Company", doc.company, "enable_stock_delivered_but_not_billed"):
		_update_post_delivery_billed_vouchers(transactions)

	enable_separate_reposting_for_gl = frappe.db.get_single_value(
		"Stock Reposting Settings", "enable_separate_reposting_for_gl"
	)

	if (
		enable_separate_reposting_for_gl
		and doc.based_on == "Item and Warehouse"
		and not doc.repost_only_accounting_ledgers
	):
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


def _update_post_delivery_billed_vouchers(transactions: list) -> None:
	"""
	Fetch the delivery notes from dependant transactions,
	and repost the Sales Invoice vouchers created post delivery note.
	To match the Stock Delivered But Not Billed ledger entries.
	"""
	dn_vouchers = set()

	for voucher_type, voucher_no in transactions:
		if voucher_type == "Delivery Note":
			dn_vouchers.add(voucher_no)

	if not dn_vouchers:
		return

	sii = DocType("Sales Invoice Item")
	si = DocType("Sales Invoice")
	dni = DocType("Delivery Note Item")

	query = (
		frappe.qb.from_(sii)
		.inner_join(si)
		.on(si.name == sii.parent)
		.left_join(dni)
		.on(dni.name == sii.dn_detail)
		.select(sii.parenttype, sii.parent)
		.where((sii.delivery_note.isin(dn_vouchers) | dni.parent.isin(dn_vouchers)) & (si.docstatus == 1))
		.groupby(sii.parenttype, sii.parent)
	)

	result = query.run(as_dict=True)

	si_vouchers = {(d.parenttype, d.parent) for d in result}
	existing = set(transactions)

	transactions.extend(list(si_vouchers - existing))


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


REPOSTING_JOB_ID_PREFIX = "repost_item_valuation_entry_"


def run_parallel_reposting():
	# This function is called every 15 minutes via hooks.py as a recovery net;
	# each reposting job re-triggers it on completion to pick the next queued
	# entry, so the queue drains continuously without waiting for the cron

	if not frappe.db.get_single_value("Stock Reposting Settings", "enable_parallel_reposting"):
		return

	if not in_configured_timeslot():
		return

	no_of_parallel_reposting = (
		frappe.db.get_single_value("Stock Reposting Settings", "no_of_parallel_reposting") or 4
	)

	riv_entries = get_repost_item_valuation_entries(limit=no_of_parallel_reposting * 100)
	entries_in_progress = get_entries_with_active_jobs()
	items = get_items_with_active_reposting(entries_in_progress)

	for row in riv_entries:
		if row.name in entries_in_progress:
			continue

		if row.based_on != "Item and Warehouse" or row.repost_only_accounting_ledgers:
			execute_reposting_entry(row.name)
			continue

		if row.item_code in items:
			continue

		items.add(row.item_code)
		if len(items) > no_of_parallel_reposting:
			break

		enqueue_reposting_entry(row.name)


def enqueue_reposting_entry(name):
	frappe.enqueue(
		execute_reposting_entry,
		name=name,
		continue_reposting=True,
		queue="long",
		timeout=1800,
		job_id=f"{REPOSTING_JOB_ID_PREFIX}{name}",
		deduplicate=True,
	)


def enqueue_parallel_reposting():
	frappe.enqueue(
		run_parallel_reposting,
		queue="long",
		timeout=1800,
		job_id="run_parallel_reposting",
		deduplicate=True,
	)


def get_entries_with_active_jobs() -> set:
	from frappe.utils.background_jobs import get_queue

	queue = get_queue("long")
	job_ids = list(queue.get_job_ids()) + list(queue.started_job_registry.get_job_ids())

	prefix = f"{frappe.local.site}||{REPOSTING_JOB_ID_PREFIX}"
	return {job_id[len(prefix) :] for job_id in job_ids if job_id.startswith(prefix)}


def get_items_with_active_reposting(entries_in_progress) -> set:
	if not entries_in_progress:
		return set()

	items = frappe.get_all(
		"Repost Item Valuation",
		filters={"name": ("in", list(entries_in_progress))},
		pluck="item_code",
	)

	return {item_code for item_code in items if item_code}


def repost_entries():
	# This function is called every hour via hooks.py

	if frappe.db.get_single_value("Stock Reposting Settings", "enable_parallel_reposting"):
		return

	if not in_configured_timeslot():
		return

	riv_entries = get_repost_item_valuation_entries()

	for row in riv_entries:
		execute_reposting_entry(row.name)


def execute_reposting_entry(name, continue_reposting=False):
	try:
		_execute_reposting_entry(name)
	finally:
		if continue_reposting:
			enqueue_parallel_reposting()


def _execute_reposting_entry(name):
	doc = frappe.get_doc("Repost Item Valuation", name)
	if (
		doc.repost_only_accounting_ledgers
		and doc.reposting_reference
		and frappe.db.get_value("Repost Item Valuation", doc.reposting_reference, "status")
		not in ["Completed", "Skipped"]
	):
		return

	if doc.status in ("Queued", "In Progress"):
		repost(doc)
		doc.deduplicate_similar_repost()


def get_repost_item_valuation_entries(limit=None):
	doctype = frappe.qb.DocType("Repost Item Valuation")

	query = (
		frappe.qb.from_(doctype)
		.select(doctype.name, doctype.based_on, doctype.item_code, doctype.repost_only_accounting_ledgers)
		.where(
			(doctype.status.isin(["Queued", "In Progress"]))
			& (doctype.creation <= now())
			& (doctype.docstatus == 1)
		)
		.orderby(CombineDatetime(doctype.posting_date, doctype.posting_time), order=frappe.qb.asc)
		.orderby(doctype.creation, order=frappe.qb.asc)
		.orderby(doctype.status, order=frappe.qb.asc)
	)

	if limit:
		query = query.limit(cint(limit))

	return query.run(as_dict=True)


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

	method = "erpnext.stock.doctype.repost_item_valuation.repost_item_valuation.repost_entries"
	if frappe.db.get_single_value("Stock Reposting Settings", "enable_parallel_reposting"):
		method = "erpnext.stock.doctype.repost_item_valuation.repost_item_valuation.run_parallel_reposting"

	if name := frappe.db.get_value(
		"Scheduled Job Type",
		{"method": method},
		"name",
	):
		frappe.get_doc("Scheduled Job Type", name).enqueue(force=True)


def make_reposting_for_accounting_ledgers(transactions, company, repost_doc):
	reposting_map = get_existing_reposting_only_gl_entries(repost_doc.name)

	for voucher_type, voucher_no in transactions:
		if reposting_map.get((voucher_type, voucher_no)):
			continue

		frappe.db.savepoint("repost_accounting_ledger")
		try:
			new_repost_doc = frappe.new_doc("Repost Item Valuation")
			new_repost_doc.company = company
			new_repost_doc.voucher_type = voucher_type
			new_repost_doc.voucher_no = voucher_no
			new_repost_doc.repost_only_accounting_ledgers = 1
			new_repost_doc.reposting_reference = repost_doc.name
			new_repost_doc.flags.ignore_permissions = True
			new_repost_doc.submit()
		except Exception:
			frappe.db.rollback(save_point="repost_accounting_ledger")


def get_existing_reposting_only_gl_entries(reposting_reference):
	existing_reposting = frappe.get_all(
		"Repost Item Valuation",
		filters={
			"reposting_reference": reposting_reference,
			"docstatus": 1,
			"status": "Queued",
			"repost_only_accounting_ledgers": 1,
		},
		fields=["reposting_reference", "voucher_type", "voucher_no"],
	)

	if not existing_reposting:
		return frappe._dict()

	reposting_map = {}
	for d in existing_reposting:
		key = (d.voucher_type, d.voucher_no)
		reposting_map[key] = d.reposting_reference

	return reposting_map
