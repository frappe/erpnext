# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from json import loads
from typing import TYPE_CHECKING, Optional

import frappe
import frappe.defaults
from frappe import _, qb, throw
from frappe.model.meta import get_field_precision
from frappe.query_builder import AliasedQuery, Criterion, Table
from frappe.query_builder.functions import Count, Round, Sum
from frappe.query_builder.utils import DocType
from frappe.utils import (
	add_days,
	cint,
	create_batch,
	cstr,
	flt,
	formatdate,
	get_datetime,
	get_number_format_info,
	getdate,
	now,
	nowdate,
)
from pypika import Order
from pypika.terms import ExistsCriterion

import erpnext

# imported to enable erpnext.accounts.utils.get_account_currency
from erpnext.accounts.doctype.account.account import get_account_currency
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.stock import get_warehouse_account_map
from erpnext.stock.utils import get_stock_value_on

if TYPE_CHECKING:
	from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import RepostItemValuation


class FiscalYearError(frappe.ValidationError):
	pass


class PaymentEntryUnlinkError(frappe.ValidationError):
	pass


GL_REPOSTING_CHUNK = 100


@frappe.whitelist()
def get_fiscal_year(
	date=None,
	fiscal_year=None,
	label="Date",
	verbose=1,
	company=None,
	as_dict=False,
	boolean=None,
	raise_on_missing=True,
):
	if isinstance(raise_on_missing, str):
		raise_on_missing = loads(raise_on_missing)

	# backwards compat
	if isinstance(boolean, str):
		boolean = loads(boolean)
	if boolean is not None:
		raise_on_missing = not boolean

	fiscal_years = get_fiscal_years(
		date, fiscal_year, label, verbose, company, as_dict=as_dict, raise_on_missing=raise_on_missing
	)
	return False if not fiscal_years else fiscal_years[0]


def get_fiscal_years(
	transaction_date=None,
	fiscal_year=None,
	label="Date",
	verbose=1,
	company=None,
	as_dict=False,
	boolean=None,
	raise_on_missing=True,
):
	if transaction_date:
		transaction_date = getdate(transaction_date)
	# backwards compat
	if boolean is not None:
		raise_on_missing = not boolean

	all_fiscal_years = _get_fiscal_years(company=company)

	# No restricting selectors
	if not transaction_date and not fiscal_year:
		return all_fiscal_years

	for fy in all_fiscal_years:
		if (fiscal_year and fy.name == fiscal_year) or (
			transaction_date
			and getdate(fy.year_start_date) <= transaction_date
			and getdate(fy.year_end_date) >= transaction_date
		):
			if as_dict:
				return (fy,)
			else:
				return ((fy.name, fy.year_start_date, fy.year_end_date),)

	# No match for restricting selectors
	if raise_on_missing:
		error_msg = _("""{0} {1} is not in any active Fiscal Year""").format(
			label, formatdate(transaction_date)
		)
		if company:
			error_msg = _("""{0} for {1}""").format(error_msg, frappe.bold(company))

		if verbose == 1:
			frappe.msgprint(error_msg)

		raise FiscalYearError(error_msg)
	return []


def _get_fiscal_years(company=None):
	fiscal_years = frappe.cache().hget("fiscal_years", company) or []

	if not fiscal_years:
		# if year start date is 2012-04-01, year end date should be 2013-03-31 (hence subdate)
		FY = DocType("Fiscal Year")

		query = (
			frappe.qb.from_(FY).select(FY.name, FY.year_start_date, FY.year_end_date).where(FY.disabled == 0)
		)

		if company:
			FYC = DocType("Fiscal Year Company")
			query = query.where(
				ExistsCriterion(frappe.qb.from_(FYC).select(FYC.name).where(FYC.parent == FY.name)).negate()
				| ExistsCriterion(
					frappe.qb.from_(FYC)
					.select(FYC.company)
					.where(FYC.parent == FY.name)
					.where(FYC.company == company)
				)
			)

		query = query.orderby(FY.year_start_date, order=Order.desc)
		fiscal_years = query.run(as_dict=True)

		frappe.cache().hset("fiscal_years", company, fiscal_years)
	return fiscal_years


@frappe.whitelist()
def get_fiscal_year_filter_field(company=None):
	field = {"fieldtype": "Select", "options": [], "operator": "Between", "query_value": True}
	fiscal_years = get_fiscal_years(company=company)
	for fiscal_year in fiscal_years:
		field["options"].append(
			{
				"label": fiscal_year.name,
				"value": fiscal_year.name,
				"query_value": [
					fiscal_year.year_start_date.strftime("%Y-%m-%d"),
					fiscal_year.year_end_date.strftime("%Y-%m-%d"),
				],
			}
		)
	return field


def validate_fiscal_year(date, fiscal_year, company, label="Date", doc=None):
	years = [f[0] for f in get_fiscal_years(date, label=_(label), company=company)]
	if fiscal_year not in years:
		if doc:
			doc.fiscal_year = years[0]
		else:
			throw(_("{0} '{1}' not in Fiscal Year {2}").format(label, formatdate(date), fiscal_year))


@frappe.whitelist()
def get_balance_on(
	account=None,
	date=None,
	party_type=None,
	party=None,
	company=None,
	in_account_currency=True,
	cost_center=None,
	ignore_account_permission=False,
	account_type=None,
	start_date=None,
):
	if not account and frappe.form_dict.get("account"):
		account = frappe.form_dict.get("account")
	if not date and frappe.form_dict.get("date"):
		date = frappe.form_dict.get("date")
	if not party_type and frappe.form_dict.get("party_type"):
		party_type = frappe.form_dict.get("party_type")
	if not party and frappe.form_dict.get("party"):
		party = frappe.form_dict.get("party")
	if not cost_center and frappe.form_dict.get("cost_center"):
		cost_center = frappe.form_dict.get("cost_center")

	cond = ["is_cancelled=0"]
	if start_date:
		cond.append("posting_date >= %s" % frappe.db.escape(cstr(start_date)))
	if date:
		cond.append("posting_date <= %s" % frappe.db.escape(cstr(date)))
	else:
		# get balance of all entries that exist
		date = nowdate()

	if account:
		acc = frappe.get_doc("Account", account)

	try:
		get_fiscal_year(date, company=company, verbose=0)[1]
	except FiscalYearError:
		if getdate(date) > getdate(nowdate()):
			# if fiscal year not found and the date is greater than today
			# get fiscal year for today's date and its corresponding year start date
			get_fiscal_year(nowdate(), verbose=1)[1]
		else:
			# this indicates that it is a date older than any existing fiscal year.
			# hence, assuming balance as 0.0
			return 0.0

	if account:
		report_type = acc.report_type
	else:
		report_type = ""

	if cost_center and report_type == "Profit and Loss":
		cc = frappe.get_doc("Cost Center", cost_center)
		if cc.is_group:
			cond.append(
				f""" exists (
				select 1 from `tabCost Center` cc where cc.name = gle.cost_center
				and cc.lft >= {cc.lft} and cc.rgt <= {cc.rgt}
			)"""
			)

		else:
			cond.append(f"""gle.cost_center = {frappe.db.escape(cost_center)} """)

	if account:
		if not (frappe.flags.ignore_account_permission or ignore_account_permission):
			acc.check_permission("read")

		# different filter for group and ledger - improved performance
		if acc.is_group:
			cond.append(
				f"""exists (
				select name from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= {acc.lft} and ac.rgt <= {acc.rgt}
			)"""
			)

			# If group and currency same as company,
			# always return balance based on debit and credit in company currency
			if acc.account_currency == frappe.get_cached_value("Company", acc.company, "default_currency"):
				in_account_currency = False
		else:
			cond.append(f"""gle.account = {frappe.db.escape(account)} """)

	if account_type:
		accounts = frappe.db.get_all(
			"Account",
			filters={"company": company, "account_type": account_type, "is_group": 0},
			pluck="name",
			order_by="lft",
		)

		cond.append(
			"""
			gle.account in (%s)
		"""
			% (", ".join([frappe.db.escape(account) for account in accounts]))
		)

	if party_type and party:
		cond.append(
			f"""gle.party_type = {frappe.db.escape(party_type)} and gle.party = {frappe.db.escape(party)} """
		)

	if company:
		cond.append("""gle.company = %s """ % (frappe.db.escape(company)))

	if account or (party_type and party) or account_type:
		precision = get_currency_precision()
		if in_account_currency:
			select_field = (
				"sum(round(debit_in_account_currency, %s)) - sum(round(credit_in_account_currency, %s))"
			)
		else:
			select_field = "sum(round(debit, %s)) - sum(round(credit, %s))"

		bal = frappe.db.sql(
			"""
			SELECT {}
			FROM `tabGL Entry` gle
			WHERE {}""".format(select_field, " and ".join(cond)),
			(precision, precision),
		)[0][0]
		# if bal is None, return 0
		return flt(bal)


def get_count_on(account, fieldname, date):
	cond = ["is_cancelled=0"]
	if date:
		cond.append("posting_date <= %s" % frappe.db.escape(cstr(date)))
	else:
		# get balance of all entries that exist
		date = nowdate()

	try:
		year_start_date = get_fiscal_year(date, verbose=0)[1]
	except FiscalYearError:
		if getdate(date) > getdate(nowdate()):
			# if fiscal year not found and the date is greater than today
			# get fiscal year for today's date and its corresponding year start date
			year_start_date = get_fiscal_year(nowdate(), verbose=1)[1]
		else:
			# this indicates that it is a date older than any existing fiscal year.
			# hence, assuming balance as 0.0
			return 0.0

	if account:
		acc = frappe.get_doc("Account", account)

		if not frappe.flags.ignore_account_permission:
			acc.check_permission("read")

		# for pl accounts, get balance within a fiscal year
		if acc.report_type == "Profit and Loss":
			cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" % year_start_date)

		# different filter for group and ledger - improved performance
		if acc.is_group:
			cond.append(
				f"""exists (
				select name from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= {acc.lft} and ac.rgt <= {acc.rgt}
			)"""
			)
		else:
			cond.append(f"""gle.account = {frappe.db.escape(account)} """)

		entries = frappe.db.sql(
			"""
			SELECT name, posting_date, account, party_type, party,debit,credit,
				voucher_type, voucher_no, against_voucher_type, against_voucher
			FROM `tabGL Entry` gle
			WHERE {}""".format(" and ".join(cond)),
			as_dict=True,
		)

		count = 0
		for gle in entries:
			if fieldname not in ("invoiced_amount", "payables"):
				count += 1
			else:
				dr_or_cr = "debit" if fieldname == "invoiced_amount" else "credit"
				cr_or_dr = "credit" if fieldname == "invoiced_amount" else "debit"
				select_fields = (
					"ifnull(sum(credit-debit),0)"
					if fieldname == "invoiced_amount"
					else "ifnull(sum(debit-credit),0)"
				)

				if (
					(not gle.against_voucher)
					or (gle.against_voucher_type in ["Sales Order", "Purchase Order"])
					or (gle.against_voucher == gle.voucher_no and gle.get(dr_or_cr) > 0)
				):
					payment_amount = frappe.db.sql(
						f"""
						SELECT {select_fields}
						FROM `tabGL Entry` gle
						WHERE docstatus < 2 and posting_date <= %(date)s and against_voucher = %(voucher_no)s
						and party = %(party)s and name != %(name)s""",
						{"date": date, "voucher_no": gle.voucher_no, "party": gle.party, "name": gle.name},
					)[0][0]

					outstanding_amount = flt(gle.get(dr_or_cr)) - flt(gle.get(cr_or_dr)) - payment_amount
					currency_precision = get_currency_precision() or 2
					if abs(flt(outstanding_amount)) > 0.1 / 10**currency_precision:
						count += 1

		return count


@frappe.whitelist()
def add_ac(args=None):
	from frappe.desk.treeview import make_tree_args

	if not args:
		args = frappe.local.form_dict

	args.doctype = "Account"
	args = make_tree_args(**args)

	ac = frappe.new_doc("Account")

	if args.get("ignore_permissions"):
		ac.flags.ignore_permissions = True
		args.pop("ignore_permissions")

	ac.update(args)

	if not ac.parent_account:
		ac.parent_account = args.get("parent")

	ac.old_parent = ""
	ac.freeze_account = "No"
	if cint(ac.get("is_root")):
		ac.parent_account = None
		ac.flags.ignore_mandatory = True

	ac.insert()

	return ac.name


@frappe.whitelist()
def add_cc(args=None):
	from frappe.desk.treeview import make_tree_args

	if not args:
		args = frappe.local.form_dict

	args.doctype = "Cost Center"
	args = make_tree_args(**args)

	if args.parent_cost_center == args.company:
		args.parent_cost_center = "{} - {}".format(
			args.parent_cost_center, frappe.get_cached_value("Company", args.company, "abbr")
		)

	cc = frappe.new_doc("Cost Center")
	cc.update(args)

	if not cc.parent_cost_center:
		cc.parent_cost_center = args.get("parent")

	cc.old_parent = ""
	cc.insert()
	return cc.name


def _build_dimensions_dict_for_exc_gain_loss(
	entry: dict | object = None, active_dimensions: list | None = None
):
	dimensions_dict = frappe._dict()
	if entry and active_dimensions:
		for dim in active_dimensions:
			dimensions_dict[dim.fieldname] = entry.get(dim.fieldname)
	return dimensions_dict


def reconcile_against_document(
	args, skip_ref_details_update_for_pe=False, active_dimensions=None
):  # nosemgrep
	"""
	Cancel PE or JV, Update against document, split if required and resubmit
	"""
	# To optimize making GL Entry for PE or JV with multiple references
	reconciled_entries = {}
	for row in args:
		if not reconciled_entries.get((row.voucher_type, row.voucher_no)):
			reconciled_entries[(row.voucher_type, row.voucher_no)] = []

		reconciled_entries[(row.voucher_type, row.voucher_no)].append(row)

	for key, entries in reconciled_entries.items():
		voucher_type = key[0]
		voucher_no = key[1]

		# cancel advance entry
		doc = frappe.get_doc(voucher_type, voucher_no)
		frappe.flags.ignore_party_validation = True

		# When Advance is allocated from an Order to an Invoice
		# whole ledger must be reposted
		repost_whole_ledger = any([x.voucher_detail_no for x in entries])
		if voucher_type == "Payment Entry" and doc.book_advance_payments_in_separate_party_account:
			if repost_whole_ledger:
				doc.make_gl_entries(cancel=1)
			else:
				doc.make_advance_gl_entries(cancel=1)
		else:
			_delete_pl_entries(voucher_type, voucher_no)

		for entry in entries:
			check_if_advance_entry_modified(entry)
			validate_allocated_amount(entry)

			dimensions_dict = _build_dimensions_dict_for_exc_gain_loss(entry, active_dimensions)

			# update ref in advance entry
			if voucher_type == "Journal Entry":
				referenced_row, update_advance_paid = update_reference_in_journal_entry(
					entry, doc, do_not_save=False
				)
				# advance section in sales/purchase invoice and reconciliation tool,both pass on exchange gain/loss
				# amount and account in args
				# referenced_row is used to deduplicate gain/loss journal
				entry.update({"referenced_row": referenced_row})
				doc.make_exchange_gain_loss_journal([entry], dimensions_dict)
			else:
				referenced_row, update_advance_paid = update_reference_in_payment_entry(
					entry,
					doc,
					do_not_save=True,
					skip_ref_details_update_for_pe=skip_ref_details_update_for_pe,
					dimensions_dict=dimensions_dict,
				)

		doc.save(ignore_permissions=True)
		# re-submit advance entry
		doc = frappe.get_doc(entry.voucher_type, entry.voucher_no)

		if voucher_type == "Payment Entry" and doc.book_advance_payments_in_separate_party_account:
			# When Advance is allocated from an Order to an Invoice
			# whole ledger must be reposted
			if repost_whole_ledger:
				doc.make_gl_entries()
			else:
				# both ledgers must be posted to for `Advance` in separate account feature
				# TODO: find a more efficient way post only for the new linked vouchers
				doc.make_advance_gl_entries()
		else:
			gl_map = doc.build_gl_map()
			# Make sure there is no overallocation
			from erpnext.accounts.general_ledger import process_debit_credit_difference

			process_debit_credit_difference(gl_map)
			create_payment_ledger_entry(gl_map, update_outstanding="No", cancel=0, adv_adj=1)

		# Only update outstanding for newly linked vouchers
		for entry in entries:
			update_voucher_outstanding(
				entry.against_voucher_type,
				entry.against_voucher,
				entry.account,
				entry.party_type,
				entry.party,
			)
		# update advance paid in Advance Receivable/Payable doctypes
		if update_advance_paid:
			for t, n in update_advance_paid:
				frappe.get_doc(t, n).set_total_advance_paid()

		frappe.flags.ignore_party_validation = False


def check_if_advance_entry_modified(args):
	"""
	check if there is already a voucher reference
	check if amount is same
	check if jv is submitted
	"""
	if not args.get("unreconciled_amount"):
		args.update({"unreconciled_amount": args.get("unadjusted_amount")})

	ret = None
	if args.voucher_type == "Journal Entry":
		journal_entry = frappe.qb.DocType("Journal Entry")
		journal_acc = frappe.qb.DocType("Journal Entry Account")

		q = (
			frappe.qb.from_(journal_entry)
			.inner_join(journal_acc)
			.on(journal_entry.name == journal_acc.parent)
			.select(journal_acc[args.get("dr_or_cr")])
			.where(
				(journal_acc.account == args.get("account"))
				& (journal_acc.party_type == args.get("party_type"))
				& (journal_acc.party == args.get("party"))
				& (
					(journal_acc.reference_type.isnull())
					| (journal_acc.reference_type.isin(["", "Sales Order", "Purchase Order"]))
				)
				& (journal_entry.name == args.get("voucher_no"))
				& (journal_acc.name == args.get("voucher_detail_no"))
				& (journal_entry.docstatus == 1)
			)
		)

	else:
		precision = frappe.get_precision("Payment Entry", "unallocated_amount")

		payment_entry = frappe.qb.DocType("Payment Entry")
		payment_ref = frappe.qb.DocType("Payment Entry Reference")

		q = (
			frappe.qb.from_(payment_entry)
			.select(payment_entry.name)
			.where(payment_entry.name == args.get("voucher_no"))
			.where(payment_entry.docstatus == 1)
			.where(payment_entry.party_type == args.get("party_type"))
			.where(payment_entry.party == args.get("party"))
		)

		if args.voucher_detail_no:
			q = (
				q.inner_join(payment_ref)
				.on(payment_entry.name == payment_ref.parent)
				.where(payment_ref.name == args.get("voucher_detail_no"))
				.where(payment_ref.reference_doctype.isin(("", "Sales Order", "Purchase Order")))
				.where(payment_ref.allocated_amount == args.get("unreconciled_amount"))
			)
		else:
			q = q.where(
				Round(payment_entry.unallocated_amount, precision)
				== Round(args.get("unreconciled_amount"), precision)
			)

	ret = q.run(as_dict=True)

	if not ret:
		throw(_("""Payment Entry has been modified after you pulled it. Please pull it again."""))


def validate_allocated_amount(args):
	precision = args.get("precision") or frappe.db.get_single_value("System Settings", "currency_precision")
	if args.get("allocated_amount") < 0:
		throw(_("Allocated amount cannot be negative"))
	elif flt(args.get("allocated_amount"), precision) > flt(args.get("unadjusted_amount"), precision):
		throw(_("Allocated amount cannot be greater than unadjusted amount"))


def update_reference_in_journal_entry(d, journal_entry, do_not_save=False):
	"""
	Updates against document, if partial amount splits into rows
	"""
	jv_detail = journal_entry.get("accounts", {"name": d["voucher_detail_no"]})[0]

	# Update Advance Paid in SO/PO since they might be getting unlinked
	update_advance_paid = []
	advance_payment_doctypes = frappe.get_hooks("advance_payment_receivable_doctypes") + frappe.get_hooks(
		"advance_payment_payable_doctypes"
	)
	if jv_detail.get("reference_type") in advance_payment_doctypes:
		update_advance_paid.append((jv_detail.reference_type, jv_detail.reference_name))

	if flt(d["unadjusted_amount"]) - flt(d["allocated_amount"]) != 0:
		# adjust the unreconciled balance
		amount_in_account_currency = flt(d["unadjusted_amount"]) - flt(d["allocated_amount"])
		amount_in_company_currency = amount_in_account_currency * flt(jv_detail.exchange_rate)
		jv_detail.set(d["dr_or_cr"], amount_in_account_currency)
		jv_detail.set(
			"debit" if d["dr_or_cr"] == "debit_in_account_currency" else "credit",
			amount_in_company_currency,
		)
	else:
		journal_entry.remove(jv_detail)

	# new row with references
	new_row = journal_entry.append("accounts")

	# Copy field values into new row
	[
		new_row.set(field, jv_detail.get(field))
		for field in frappe.get_meta("Journal Entry Account").get_fieldnames_with_value()
	]

	new_row.set(d["dr_or_cr"], d["allocated_amount"])
	new_row.set(
		"debit" if d["dr_or_cr"] == "debit_in_account_currency" else "credit",
		d["allocated_amount"] * flt(jv_detail.exchange_rate),
	)

	new_row.set(
		"credit_in_account_currency"
		if d["dr_or_cr"] == "debit_in_account_currency"
		else "debit_in_account_currency",
		0,
	)
	new_row.set("credit" if d["dr_or_cr"] == "debit_in_account_currency" else "debit", 0)

	new_row.set("reference_type", d["against_voucher_type"])
	new_row.set("reference_name", d["against_voucher"])

	new_row.against_account = cstr(jv_detail.against_account)
	new_row.is_advance = cstr(jv_detail.is_advance)
	new_row.docstatus = 1

	# will work as update after submit
	journal_entry.flags.ignore_validate_update_after_submit = True
	# Ledgers will be reposted by Reconciliation tool
	journal_entry.flags.ignore_reposting_on_reconciliation = True
	if not do_not_save:
		journal_entry.save(ignore_permissions=True)

	return new_row.name, update_advance_paid


def update_reference_in_payment_entry(
	d, payment_entry, do_not_save=False, skip_ref_details_update_for_pe=False, dimensions_dict=None
):
	reference_details = {
		"reference_doctype": d.against_voucher_type,
		"reference_name": d.against_voucher,
		"total_amount": d.grand_total,
		"outstanding_amount": d.outstanding_amount,
		"allocated_amount": d.allocated_amount,
		"exchange_rate": d.exchange_rate
		if d.difference_amount is not None
		else payment_entry.get_exchange_rate(),
		"exchange_gain_loss": d.difference_amount,
		"account": d.account,
		"dimensions": d.dimensions,
	}
	update_advance_paid = []

	if d.voucher_detail_no:
		existing_row = payment_entry.get("references", {"name": d["voucher_detail_no"]})[0]

		# Update Advance Paid in SO/PO since they are getting unlinked
		advance_payment_doctypes = frappe.get_hooks("advance_payment_receivable_doctypes") + frappe.get_hooks(
			"advance_payment_payable_doctypes"
		)
		if existing_row.get("reference_doctype") in advance_payment_doctypes:
			update_advance_paid.append((existing_row.reference_doctype, existing_row.reference_name))

		if d.allocated_amount <= existing_row.allocated_amount:
			existing_row.allocated_amount -= d.allocated_amount

			new_row = payment_entry.append("references")
			new_row.docstatus = 1
			for field in list(reference_details):
				new_row.set(field, reference_details[field])
			row = new_row
	else:
		new_row = payment_entry.append("references")
		new_row.docstatus = 1
		new_row.update(reference_details)
		row = new_row

	payment_entry.flags.ignore_validate_update_after_submit = True
	payment_entry.clear_unallocated_reference_document_rows()
	payment_entry.setup_party_account_field()
	payment_entry.set_missing_values()
	if not skip_ref_details_update_for_pe:
		reference_exchange_details = frappe._dict()
		if d.against_voucher_type == "Journal Entry" and d.exchange_rate:
			reference_exchange_details.update(
				{
					"reference_doctype": d.against_voucher_type,
					"reference_name": d.against_voucher,
					"exchange_rate": d.exchange_rate,
				}
			)
		payment_entry.set_missing_ref_details(
			update_ref_details_only_for=[(d.against_voucher_type, d.against_voucher)],
			reference_exchange_details=reference_exchange_details,
		)
	payment_entry.set_amounts()

	payment_entry.make_exchange_gain_loss_journal(
		frappe._dict({"difference_posting_date": d.difference_posting_date}), dimensions_dict
	)

	if not do_not_save:
		payment_entry.save(ignore_permissions=True)
	return row, update_advance_paid


def cancel_exchange_gain_loss_journal(
	parent_doc: dict | object, referenced_dt: str | None = None, referenced_dn: str | None = None
) -> None:
	"""
	Cancel Exchange Gain/Loss for Sales/Purchase Invoice, if they have any.
	"""
	if parent_doc.doctype in ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"]:
		gain_loss_journals = get_linked_exchange_gain_loss_journal(
			referenced_dt=parent_doc.doctype, referenced_dn=parent_doc.name, je_docstatus=1
		)
		for doc in gain_loss_journals:
			gain_loss_je = frappe.get_doc("Journal Entry", doc)
			if referenced_dt and referenced_dn:
				references = [(x.reference_type, x.reference_name) for x in gain_loss_je.accounts]
				if (
					len(references) == 2
					and (referenced_dt, referenced_dn) in references
					and (parent_doc.doctype, parent_doc.name) in references
				):
					# only cancel JE generated against parent_doc and referenced_dn
					gain_loss_je.cancel()
			else:
				gain_loss_je.cancel()


def delete_exchange_gain_loss_journal(
	parent_doc: dict | object, referenced_dt: str | None = None, referenced_dn: str | None = None
) -> None:
	"""
	Delete Exchange Gain/Loss for Sales/Purchase Invoice, if they have any.
	"""
	if parent_doc.doctype in ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"]:
		gain_loss_journals = get_linked_exchange_gain_loss_journal(
			referenced_dt=parent_doc.doctype, referenced_dn=parent_doc.name, je_docstatus=2
		)
		for doc in gain_loss_journals:
			gain_loss_je = frappe.get_doc("Journal Entry", doc)
			if referenced_dt and referenced_dn:
				references = [(x.reference_type, x.reference_name) for x in gain_loss_je.accounts]
				if (
					len(references) == 2
					and (referenced_dt, referenced_dn) in references
					and (parent_doc.doctype, parent_doc.name) in references
				):
					# only delete JE generated against parent_doc and referenced_dn
					gain_loss_je.delete()
			else:
				gain_loss_je.delete()


def get_linked_exchange_gain_loss_journal(referenced_dt: str, referenced_dn: str, je_docstatus: int) -> list:
	"""
	Get all the linked exchange gain/loss journal entries for a given document.
	"""
	gain_loss_journals = []
	if journals := frappe.db.get_all(
		"Journal Entry Account",
		{
			"reference_type": referenced_dt,
			"reference_name": referenced_dn,
			"docstatus": je_docstatus,
		},
		pluck="parent",
	):
		gain_loss_journals = frappe.db.get_all(
			"Journal Entry",
			{
				"name": ["in", journals],
				"voucher_type": "Exchange Gain Or Loss",
				"is_system_generated": 1,
				"docstatus": je_docstatus,
			},
			pluck="name",
		)
	return gain_loss_journals


def cancel_common_party_journal(self):
	if self.doctype not in ["Sales Invoice", "Purchase Invoice"]:
		return

	if not frappe.db.get_single_value("Accounts Settings", "enable_common_party_accounting"):
		return

	party_link = self.get_common_party_link()
	if not party_link:
		return

	journal_entry = frappe.db.get_value(
		"Journal Entry Account",
		filters={
			"reference_type": self.doctype,
			"reference_name": self.name,
			"docstatus": 1,
		},
		fieldname="parent",
	)

	if not journal_entry:
		return

	common_party_journal = frappe.db.get_value(
		"Journal Entry",
		filters={
			"name": journal_entry,
			"is_system_generated": True,
			"docstatus": 1,
		},
	)

	if not common_party_journal:
		return

	common_party_je = frappe.get_doc("Journal Entry", common_party_journal)
	common_party_je.cancel()


def update_accounting_ledgers_after_reference_removal(
	ref_type: str | None = None, ref_no: str | None = None, payment_name: str | None = None
):
	# General Ledger
	gle = qb.DocType("GL Entry")
	gle_update_query = (
		qb.update(gle)
		.set(gle.against_voucher_type, None)
		.set(gle.against_voucher, None)
		.set(gle.modified, now())
		.set(gle.modified_by, frappe.session.user)
		.where((gle.against_voucher_type == ref_type) & (gle.against_voucher == ref_no))
	)

	if payment_name:
		gle_update_query = gle_update_query.where(gle.voucher_no == payment_name)
	gle_update_query.run()

	# Payment Ledger
	ple = qb.DocType("Payment Ledger Entry")
	ple_update_query = (
		qb.update(ple)
		.set(ple.against_voucher_type, ple.voucher_type)
		.set(ple.against_voucher_no, ple.voucher_no)
		.set(ple.modified, now())
		.set(ple.modified_by, frappe.session.user)
		.where(
			(ple.against_voucher_type == ref_type) & (ple.against_voucher_no == ref_no) & (ple.delinked == 0)
		)
	)

	if payment_name:
		ple_update_query = ple_update_query.where(ple.voucher_no == payment_name)
	ple_update_query.run()


def remove_ref_from_advance_section(ref_doc: object = None):
	# TODO: this might need some testing
	if ref_doc.doctype in ("Sales Invoice", "Purchase Invoice"):
		ref_doc.set("advances", [])
		adv_type = qb.DocType(f"{ref_doc.doctype} Advance")
		qb.from_(adv_type).delete().where(adv_type.parent == ref_doc.name).run()


def unlink_ref_doc_from_payment_entries(ref_doc: object = None, payment_name: str | None = None):
	remove_ref_doc_link_from_jv(ref_doc.doctype, ref_doc.name, payment_name)
	remove_ref_doc_link_from_pe(ref_doc.doctype, ref_doc.name, payment_name)
	update_accounting_ledgers_after_reference_removal(ref_doc.doctype, ref_doc.name, payment_name)
	remove_ref_from_advance_section(ref_doc)


def remove_ref_doc_link_from_jv(
	ref_type: str | None = None, ref_no: str | None = None, payment_name: str | None = None
):
	jea = qb.DocType("Journal Entry Account")

	linked_jv = (
		qb.from_(jea)
		.select(jea.parent)
		.where((jea.reference_type == ref_type) & (jea.reference_name == ref_no) & (jea.docstatus.lt(2)))
		.run(as_list=1)
	)
	linked_jv = convert_to_list(linked_jv)
	# remove reference only from specified payment
	linked_jv = [x for x in linked_jv if x == payment_name] if payment_name else linked_jv

	if linked_jv:
		update_query = (
			qb.update(jea)
			.set(jea.reference_type, None)
			.set(jea.reference_name, None)
			.set(jea.modified, now())
			.set(jea.modified_by, frappe.session.user)
			.where((jea.reference_type == ref_type) & (jea.reference_name == ref_no))
		)

		if payment_name:
			update_query = update_query.where(jea.parent == payment_name)

		update_query.run()

		frappe.msgprint(_("Journal Entries {0} are un-linked").format("\n".join(linked_jv)))


def convert_to_list(result):
	"""
	Convert tuple to list
	"""
	return [x[0] for x in result]


def remove_ref_doc_link_from_pe(
	ref_type: str | None = None, ref_no: str | None = None, payment_name: str | None = None
):
	per = qb.DocType("Payment Entry Reference")
	pay = qb.DocType("Payment Entry")

	linked_pe = (
		qb.from_(per)
		.select(per.parent)
		.where((per.reference_doctype == ref_type) & (per.reference_name == ref_no) & (per.docstatus.lt(2)))
		.run(as_list=1)
	)
	linked_pe = convert_to_list(linked_pe)
	# remove reference only from specified payment
	linked_pe = [x for x in linked_pe if x == payment_name] if payment_name else linked_pe

	if linked_pe:
		update_query = (
			qb.update(per)
			.set(per.allocated_amount, 0)
			.set(per.modified, now())
			.set(per.modified_by, frappe.session.user)
			.where(per.docstatus.lt(2) & (per.reference_doctype == ref_type) & (per.reference_name == ref_no))
		)

		if payment_name:
			update_query = update_query.where(per.parent == payment_name)

		update_query.run()

		for pe in linked_pe:
			try:
				pe_doc = frappe.get_doc("Payment Entry", pe)
				pe_doc.set_amounts()

				# Call cancel on only removed reference
				references = [
					x
					for x in pe_doc.references
					if x.reference_doctype == ref_type and x.reference_name == ref_no
				]
				[pe_doc.make_advance_gl_entries(x, cancel=1) for x in references]

				pe_doc.clear_unallocated_reference_document_rows()
				pe_doc.validate_payment_type_with_outstanding()
			except Exception:
				msg = _("There were issues unlinking payment entry {0}.").format(pe_doc.name)
				msg += "<br>"
				msg += _("Please cancel payment entry manually first")
				frappe.throw(msg, exc=PaymentEntryUnlinkError, title=_("Payment Unlink Error"))

			qb.update(pay).set(pay.total_allocated_amount, pe_doc.total_allocated_amount).set(
				pay.base_total_allocated_amount, pe_doc.base_total_allocated_amount
			).set(pay.unallocated_amount, pe_doc.unallocated_amount).set(pay.modified, now()).set(
				pay.modified_by, frappe.session.user
			).where(pay.name == pe).run()

		frappe.msgprint(_("Payment Entries {0} are un-linked").format("\n".join(linked_pe)))


@frappe.whitelist()
def get_company_default(company, fieldname, ignore_validation=False):
	value = frappe.get_cached_value("Company", company, fieldname)

	if not ignore_validation and not value:
		throw(
			_("Please set default {0} in Company {1}").format(
				frappe.get_meta("Company").get_label(fieldname), company
			)
		)

	return value


def fix_total_debit_credit():
	vouchers = frappe.db.sql(
		"""select voucher_type, voucher_no,
		sum(debit) - sum(credit) as diff
		from `tabGL Entry`
		group by voucher_type, voucher_no
		having sum(debit) != sum(credit)""",
		as_dict=1,
	)

	for d in vouchers:
		if abs(d.diff) > 0:
			dr_or_cr = d.voucher_type == "Sales Invoice" and "credit" or "debit"

			frappe.db.sql(
				"""update `tabGL Entry` set {} = {} + {}
				where voucher_type = {} and voucher_no = {} and {} > 0 limit 1""".format(
					dr_or_cr, dr_or_cr, "%s", "%s", "%s", dr_or_cr
				),
				(d.diff, d.voucher_type, d.voucher_no),
			)


def get_currency_precision():
	precision = cint(frappe.db.get_default("currency_precision"))
	if not precision:
		number_format = frappe.db.get_default("number_format") or "#,###.##"
		precision = get_number_format_info(number_format)[2]

	return precision


def get_held_invoices(party_type, party):
	"""
	Returns a list of names Purchase Invoices for the given party that are on hold
	"""
	held_invoices = None

	if party_type == "Supplier":
		held_invoices = frappe.db.sql(
			"select name from `tabPurchase Invoice` where on_hold = 1 and release_date IS NOT NULL and release_date > CURDATE()",
			as_dict=1,
		)
		held_invoices = set(d["name"] for d in held_invoices)

	return held_invoices


def get_outstanding_invoices(
	party_type,
	party,
	account,
	common_filter=None,
	posting_date=None,
	min_outstanding=None,
	max_outstanding=None,
	accounting_dimensions=None,
	vouchers=None,  # list of dicts [{'voucher_type': '', 'voucher_no': ''}] for filtering
	limit=None,  # passed by reconciliation tool
	voucher_no=None,  # filter passed by reconciliation tool
):
	ple = qb.DocType("Payment Ledger Entry")
	outstanding_invoices = []
	precision = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2

	if account:
		root_type, account_type = frappe.get_cached_value(
			"Account", account[0], ["root_type", "account_type"]
		)
		party_account_type = "Receivable" if root_type == "Asset" else "Payable"
		party_account_type = account_type or party_account_type
	else:
		party_account_type = erpnext.get_party_account_type(party_type)

	held_invoices = get_held_invoices(party_type, party)

	common_filter = common_filter or []
	common_filter.append(ple.account_type == party_account_type)
	common_filter.append(ple.account.isin(account))
	common_filter.append(ple.party_type == party_type)
	common_filter.append(ple.party == party)

	ple_query = QueryPaymentLedger()
	invoice_list = ple_query.get_voucher_outstandings(
		vouchers=vouchers,
		common_filter=common_filter,
		posting_date=posting_date,
		min_outstanding=min_outstanding,
		max_outstanding=max_outstanding,
		get_invoices=True,
		accounting_dimensions=accounting_dimensions or [],
		limit=limit,
		voucher_no=voucher_no,
	)

	for d in invoice_list:
		payment_amount = d.invoice_amount_in_account_currency - d.outstanding_in_account_currency
		outstanding_amount = d.outstanding_in_account_currency
		if outstanding_amount > 0.5 / (10**precision):
			if (
				min_outstanding
				and max_outstanding
				and (outstanding_amount < min_outstanding or outstanding_amount > max_outstanding)
			):
				continue

			if d.voucher_type != "Purchase Invoice" or d.voucher_no not in held_invoices:
				outstanding_invoices.append(
					frappe._dict(
						{
							"voucher_no": d.voucher_no,
							"voucher_type": d.voucher_type,
							"posting_date": d.posting_date,
							"invoice_amount": flt(d.invoice_amount_in_account_currency),
							"payment_amount": payment_amount,
							"outstanding_amount": outstanding_amount,
							"due_date": d.due_date,
							"currency": d.currency,
							"account": d.account,
						}
					)
				)

	outstanding_invoices = sorted(outstanding_invoices, key=lambda k: k["due_date"] or getdate(nowdate()))
	return outstanding_invoices


def get_account_name(account_type=None, root_type=None, is_group=None, account_currency=None, company=None):
	"""return account based on matching conditions"""
	return frappe.db.get_value(
		"Account",
		{
			"account_type": account_type or "",
			"root_type": root_type or "",
			"is_group": is_group or 0,
			"account_currency": account_currency or frappe.defaults.get_defaults().currency,
			"company": company or frappe.defaults.get_defaults().company,
		},
		"name",
	)


@frappe.whitelist()
def get_companies():
	"""get a list of companies based on permission"""
	return [d.name for d in frappe.get_list("Company", fields=["name"], order_by="name")]


@frappe.whitelist()
def get_children(doctype, parent, company, is_root=False, include_disabled=False):
	if isinstance(include_disabled, str):
		include_disabled = loads(include_disabled)
	from erpnext.accounts.report.financial_statements import sort_accounts

	parent_fieldname = "parent_" + doctype.lower().replace(" ", "_")
	fields = ["name as value", "is_group as expandable"]
	filters = [["docstatus", "<", 2]]
	if frappe.db.has_column(doctype, "disabled") and not include_disabled:
		filters.append(["disabled", "=", False])

	filters.append([f'ifnull(`{parent_fieldname}`,"")', "=", "" if is_root else parent])

	if is_root:
		fields += ["root_type", "report_type", "account_currency"] if doctype == "Account" else []
		filters.append(["company", "=", company])

	else:
		fields += ["root_type", "account_currency"] if doctype == "Account" else []
		fields += [parent_fieldname + " as parent"]

	acc = frappe.get_list(doctype, fields=fields, filters=filters)

	if doctype == "Account":
		sort_accounts(acc, is_root, key="value")

	return acc


@frappe.whitelist()
def get_account_balances(accounts, company):
	if isinstance(accounts, str):
		accounts = loads(accounts)

	if not accounts:
		return []

	company_currency = frappe.get_cached_value("Company", company, "default_currency")

	for account in accounts:
		account["company_currency"] = company_currency
		account["balance"] = flt(get_balance_on(account["value"], in_account_currency=False, company=company))
		if account["account_currency"] and account["account_currency"] != company_currency:
			account["balance_in_account_currency"] = flt(get_balance_on(account["value"], company=company))

	return accounts


def create_payment_gateway_account(gateway, payment_channel="Email"):
	from erpnext.setup.setup_wizard.operations.install_fixtures import create_bank_account

	company = frappe.get_cached_value("Global Defaults", "Global Defaults", "default_company")
	if not company:
		return

	# NOTE: we translate Payment Gateway account name because that is going to be used by the end user
	bank_account = frappe.db.get_value(
		"Account",
		{"account_name": _(gateway), "company": company},
		["name", "account_currency"],
		as_dict=1,
	)

	if not bank_account:
		# check for untranslated one
		bank_account = frappe.db.get_value(
			"Account",
			{"account_name": gateway, "company": company},
			["name", "account_currency"],
			as_dict=1,
		)

	if not bank_account:
		# try creating one
		bank_account = create_bank_account({"company_name": company, "bank_account": _(gateway)})

	if not bank_account:
		frappe.msgprint(_("Payment Gateway Account not created, please create one manually."))
		return

	# if payment gateway account exists, return
	if frappe.db.exists(
		"Payment Gateway Account",
		{"payment_gateway": gateway, "currency": bank_account.account_currency},
	):
		return

	try:
		frappe.get_doc(
			{
				"doctype": "Payment Gateway Account",
				"is_default": 1,
				"payment_gateway": gateway,
				"payment_account": bank_account.name,
				"currency": bank_account.account_currency,
				"payment_channel": payment_channel,
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

	except frappe.DuplicateEntryError:
		# already exists, due to a reinstall?
		pass


@frappe.whitelist()
def update_cost_center(docname, cost_center_name, cost_center_number, company, merge):
	"""
	Renames the document by adding the number as a prefix to the current name and updates
	all transaction where it was present.
	"""
	validate_field_number("Cost Center", docname, cost_center_number, company, "cost_center_number")

	if cost_center_number:
		frappe.db.set_value("Cost Center", docname, "cost_center_number", cost_center_number.strip())
	else:
		frappe.db.set_value("Cost Center", docname, "cost_center_number", "")

	frappe.db.set_value("Cost Center", docname, "cost_center_name", cost_center_name.strip())

	new_name = get_autoname_with_number(cost_center_number, cost_center_name, company)
	if docname != new_name:
		frappe.rename_doc("Cost Center", docname, new_name, force=1, merge=merge)
		return new_name


def validate_field_number(doctype_name, docname, number_value, company, field_name):
	"""Validate if the number entered isn't already assigned to some other document."""
	if number_value:
		filters = {field_name: number_value, "name": ["!=", docname]}
		if company:
			filters["company"] = company

		doctype_with_same_number = frappe.db.get_value(doctype_name, filters)

		if doctype_with_same_number:
			frappe.throw(
				_("{0} Number {1} is already used in {2} {3}").format(
					doctype_name, number_value, doctype_name.lower(), doctype_with_same_number
				)
			)


def get_autoname_with_number(number_value, doc_title, company):
	"""append title with prefix as number and suffix as company's abbreviation separated by '-'"""
	company_abbr = frappe.get_cached_value("Company", company, "abbr")
	parts = [doc_title.strip(), company_abbr]

	if cstr(number_value).strip():
		parts.insert(0, cstr(number_value).strip())

	return " - ".join(parts)


def parse_naming_series_variable(doc, variable):
	if variable == "FY":
		if doc:
			date = doc.get("posting_date") or doc.get("transaction_date") or getdate()
			company = doc.get("company")
		else:
			date = getdate()
			company = None
		return get_fiscal_year(date=date, company=company)[0]
	
	elif variable == "ABBR":
		if doc:
			company = doc.get("company") or frappe.db.get_default('company')
		else:
			company = frappe.db.get_default('company')

		return frappe.db.get_value("Company", company, "abbr") if company else ""


@frappe.whitelist()
def get_coa(doctype, parent, is_root=None, chart=None):
	from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import (
		build_tree_from_json,
	)

	# add chart to flags to retrieve when called from expand all function
	chart = chart if chart else frappe.flags.chart
	frappe.flags.chart = chart

	parent = None if parent == _("All Accounts") else parent
	accounts = build_tree_from_json(chart)  # returns alist of dict in a tree render-able form

	# filter out to show data for the selected node only
	accounts = [d for d in accounts if d["parent_account"] == parent]

	return accounts


def update_gl_entries_after(
	posting_date,
	posting_time,
	for_warehouses=None,
	for_items=None,
	warehouse_account=None,
	company=None,
):
	stock_vouchers = get_future_stock_vouchers(posting_date, posting_time, for_warehouses, for_items, company)
	repost_gle_for_stock_vouchers(stock_vouchers, posting_date, company, warehouse_account)


def repost_gle_for_stock_vouchers(
	stock_vouchers: list[tuple[str, str]],
	posting_date: str,
	company: str | None = None,
	warehouse_account=None,
	repost_doc: Optional["RepostItemValuation"] = None,
):
	from erpnext.accounts.general_ledger import toggle_debit_credit_if_negative

	if not stock_vouchers:
		return

	if not warehouse_account:
		warehouse_account = get_warehouse_account_map(company)

	stock_vouchers = sort_stock_vouchers_by_posting_date(stock_vouchers)
	if repost_doc and repost_doc.gl_reposting_index:
		# Restore progress
		stock_vouchers = stock_vouchers[cint(repost_doc.gl_reposting_index) :]

	precision = get_field_precision(frappe.get_meta("GL Entry").get_field("debit")) or 2

	for stock_vouchers_chunk in create_batch(stock_vouchers, GL_REPOSTING_CHUNK):
		gle = get_voucherwise_gl_entries(stock_vouchers_chunk, posting_date)

		for voucher_type, voucher_no in stock_vouchers_chunk:
			existing_gle = gle.get((voucher_type, voucher_no), [])
			voucher_obj = frappe.get_doc(voucher_type, voucher_no)
			# Some transactions post credit as negative debit, this is handled while posting GLE
			# but while comparing we need to make sure it's flipped so comparisons are accurate
			expected_gle = toggle_debit_credit_if_negative(voucher_obj.get_gl_entries(warehouse_account))
			if expected_gle:
				if not existing_gle or not compare_existing_and_expected_gle(
					existing_gle, expected_gle, precision
				):
					_delete_accounting_ledger_entries(voucher_type, voucher_no)
					voucher_obj.make_gl_entries(gl_entries=expected_gle, from_repost=True)
			else:
				_delete_accounting_ledger_entries(voucher_type, voucher_no)

		if not frappe.flags.in_test:
			frappe.db.commit()

		if repost_doc:
			repost_doc.db_set(
				"gl_reposting_index",
				cint(repost_doc.gl_reposting_index) + len(stock_vouchers_chunk),
			)


def _delete_pl_entries(voucher_type, voucher_no):
	ple = qb.DocType("Payment Ledger Entry")
	qb.from_(ple).delete().where((ple.voucher_type == voucher_type) & (ple.voucher_no == voucher_no)).run()


def _delete_gl_entries(voucher_type, voucher_no):
	gle = qb.DocType("GL Entry")
	qb.from_(gle).delete().where((gle.voucher_type == voucher_type) & (gle.voucher_no == voucher_no)).run()


def _delete_accounting_ledger_entries(voucher_type, voucher_no):
	"""
	Remove entries from both General and Payment Ledger for specified Voucher
	"""
	_delete_gl_entries(voucher_type, voucher_no)
	_delete_pl_entries(voucher_type, voucher_no)


def sort_stock_vouchers_by_posting_date(stock_vouchers: list[tuple[str, str]]) -> list[tuple[str, str]]:
	sle = frappe.qb.DocType("Stock Ledger Entry")
	voucher_nos = [v[1] for v in stock_vouchers]

	sles = (
		frappe.qb.from_(sle)
		.select(sle.voucher_type, sle.voucher_no, sle.posting_date, sle.posting_time, sle.creation)
		.where((sle.is_cancelled == 0) & (sle.voucher_no.isin(voucher_nos)))
		.groupby(sle.voucher_type, sle.voucher_no)
		.orderby(sle.posting_datetime)
		.orderby(sle.creation)
	).run(as_dict=True)
	sorted_vouchers = [(sle.voucher_type, sle.voucher_no) for sle in sles]

	unknown_vouchers = set(stock_vouchers) - set(sorted_vouchers)
	if unknown_vouchers:
		sorted_vouchers.extend(unknown_vouchers)

	return sorted_vouchers


def get_future_stock_vouchers(posting_date, posting_time, for_warehouses=None, for_items=None, company=None):
	values = []
	condition = ""
	if for_items:
		condition += " and item_code in ({})".format(", ".join(["%s"] * len(for_items)))
		values += for_items

	if for_warehouses:
		condition += " and warehouse in ({})".format(", ".join(["%s"] * len(for_warehouses)))
		values += for_warehouses

	if company:
		condition += " and company = %s"
		values.append(company)

	future_stock_vouchers = frappe.db.sql(
		f"""select distinct sle.voucher_type, sle.voucher_no
		from `tabStock Ledger Entry` sle
		where
			timestamp(sle.posting_date, sle.posting_time) >= timestamp(%s, %s)
			and is_cancelled = 0
			{condition}
		order by timestamp(sle.posting_date, sle.posting_time) asc, creation asc for update""",
		tuple([posting_date, posting_time, *values]),
		as_dict=True,
	)

	return [(d.voucher_type, d.voucher_no) for d in future_stock_vouchers]


def get_voucherwise_gl_entries(future_stock_vouchers, posting_date):
	"""Get voucherwise list of GL entries.

	Only fetches GLE fields required for comparing with new GLE.
	Check compare_existing_and_expected_gle function below.

	returns:
	        Dict[Tuple[voucher_type, voucher_no], List[GL Entries]]
	"""
	gl_entries = {}
	if not future_stock_vouchers:
		return gl_entries

	voucher_nos = [d[1] for d in future_stock_vouchers]

	gles = frappe.db.sql(
		"""
		select name, account, credit, debit, cost_center, project, voucher_type, voucher_no
			from `tabGL Entry`
		where
			posting_date >= {} and voucher_no in ({})""".format("%s", ", ".join(["%s"] * len(voucher_nos))),
		tuple([posting_date, *voucher_nos]),
		as_dict=1,
	)

	for d in gles:
		gl_entries.setdefault((d.voucher_type, d.voucher_no), []).append(d)

	return gl_entries


def compare_existing_and_expected_gle(existing_gle, expected_gle, precision):
	if len(existing_gle) != len(expected_gle):
		return False

	matched = True
	for entry in expected_gle:
		account_existed = False
		for e in existing_gle:
			if entry.account == e.account:
				account_existed = True
			if (
				entry.account == e.account
				and (not entry.cost_center or not e.cost_center or entry.cost_center == e.cost_center)
				and (
					flt(entry.debit, precision) != flt(e.debit, precision)
					or flt(entry.credit, precision) != flt(e.credit, precision)
				)
			):
				matched = False
				break
		if not account_existed:
			matched = False
			break
	return matched


def get_stock_accounts(company, voucher_type=None, voucher_no=None, accounts=None):
	stock_accounts = [
		d.name
		for d in frappe.db.get_all("Account", {"account_type": "Stock", "company": company, "is_group": 0})
	]

	if accounts:
		stock_accounts = [row.account for row in accounts if row.account in stock_accounts]

	elif voucher_type and voucher_no:
		if voucher_type == "Journal Entry":
			stock_accounts = [
				d.account
				for d in frappe.db.get_all(
					"Journal Entry Account",
					{"parent": voucher_no, "account": ["in", stock_accounts]},
					"account",
				)
			]

		else:
			stock_accounts = [
				d.account
				for d in frappe.db.get_all(
					"GL Entry",
					{
						"voucher_type": voucher_type,
						"voucher_no": voucher_no,
						"account": ["in", stock_accounts],
					},
					"account",
				)
			]

	return list(set(stock_accounts))


def get_stock_and_account_balance(account=None, posting_date=None, company=None):
	if not posting_date:
		posting_date = nowdate()

	account_balance = get_balance_on(
		account, posting_date, in_account_currency=False, ignore_account_permission=True
	)

	account_table = frappe.qb.DocType("Account")
	query = (
		frappe.qb.from_(account_table)
		.select(Count(account_table.name))
		.where(
			(account_table.account_type == "Stock")
			& (account_table.company == company)
			& (account_table.is_group == 0)
		)
	)

	no_of_stock_accounts = cint(query.run()[0][0])

	related_warehouses = []
	if no_of_stock_accounts > 1:
		warehouse_account = get_warehouse_account_map(company)

		related_warehouses = [
			wh
			for wh, wh_details in warehouse_account.items()
			if wh_details.account == account and not wh_details.is_group
		]

	total_stock_value = get_stock_value_on(related_warehouses, posting_date)

	precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
	return flt(account_balance, precision), flt(total_stock_value, precision), related_warehouses


def get_journal_entry(account, stock_adjustment_account, amount):
	db_or_cr_warehouse_account = "credit_in_account_currency" if amount < 0 else "debit_in_account_currency"
	db_or_cr_stock_adjustment_account = (
		"debit_in_account_currency" if amount < 0 else "credit_in_account_currency"
	)

	return {
		"accounts": [
			{"account": account, db_or_cr_warehouse_account: abs(amount)},
			{"account": stock_adjustment_account, db_or_cr_stock_adjustment_account: abs(amount)},
		]
	}


def check_and_delete_linked_reports(report):
	"""Check if reports are referenced in Desktop Icon"""
	icons = frappe.get_all("Desktop Icon", fields=["name"], filters={"_report": report})
	if icons:
		for icon in icons:
			frappe.delete_doc("Desktop Icon", icon)


def create_err_and_its_journals(companies: list | None = None) -> None:
	if companies:
		for company in companies:
			err = frappe.new_doc("Exchange Rate Revaluation")
			err.company = company.name
			err.posting_date = nowdate()
			err.rounding_loss_allowance = 0.0

			err.fetch_and_calculate_accounts_data()
			if err.accounts:
				err.save().submit()
				response = err.make_jv_entries()

				if company.submit_err_jv:
					jv = response.get("revaluation_jv", None)
					jv and frappe.get_doc("Journal Entry", jv).submit()
					jv = response.get("zero_balance_jv", None)
					jv and frappe.get_doc("Journal Entry", jv).submit()


def auto_create_exchange_rate_revaluation_daily() -> None:
	"""
	Executed by background job
	"""
	companies = frappe.db.get_all(
		"Company",
		filters={"auto_exchange_rate_revaluation": 1, "auto_err_frequency": "Daily"},
		fields=["name", "submit_err_jv"],
	)
	create_err_and_its_journals(companies)


def auto_create_exchange_rate_revaluation_weekly() -> None:
	"""
	Executed by background job
	"""
	companies = frappe.db.get_all(
		"Company",
		filters={"auto_exchange_rate_revaluation": 1, "auto_err_frequency": "Weekly"},
		fields=["name", "submit_err_jv"],
	)
	create_err_and_its_journals(companies)


def auto_create_exchange_rate_revaluation_monthly() -> None:
	"""
	Executed by background job
	"""
	companies = frappe.db.get_all(
		"Company",
		filters={"auto_exchange_rate_revaluation": 1, "auto_err_frequency": "Montly"},
		fields=["name", "submit_err_jv"],
	)
	create_err_and_its_journals(companies)


def get_payment_ledger_entries(gl_entries, cancel=0):
	ple_map = []
	if gl_entries:
		ple = None

		# companies
		account = qb.DocType("Account")
		companies = list(set([x.company for x in gl_entries]))

		# receivable/payable account
		accounts_with_types = (
			qb.from_(account)
			.select(account.name, account.account_type)
			.where(account.account_type.isin(["Receivable", "Payable"]) & (account.company.isin(companies)))
			.run(as_dict=True)
		)
		receivable_or_payable_accounts = [y.name for y in accounts_with_types]

		def get_account_type(account):
			for entry in accounts_with_types:
				if entry.name == account:
					return entry.account_type

		dr_or_cr = 0
		account_type = None
		for gle in gl_entries:
			if gle.account in receivable_or_payable_accounts:
				account_type = get_account_type(gle.account)
				if account_type == "Receivable":
					dr_or_cr = gle.debit - gle.credit
					dr_or_cr_account_currency = gle.debit_in_account_currency - gle.credit_in_account_currency
				elif account_type == "Payable":
					dr_or_cr = gle.credit - gle.debit
					dr_or_cr_account_currency = gle.credit_in_account_currency - gle.debit_in_account_currency

				if cancel:
					dr_or_cr *= -1
					dr_or_cr_account_currency *= -1

				ple = frappe._dict(
					doctype="Payment Ledger Entry",
					posting_date=gle.posting_date,
					company=gle.company,
					account_type=account_type,
					account=gle.account,
					party_type=gle.party_type,
					party=gle.party,
					cost_center=gle.cost_center,
					finance_book=gle.finance_book,
					due_date=gle.due_date,
					voucher_type=gle.voucher_type,
					voucher_no=gle.voucher_no,
					voucher_detail_no=gle.voucher_detail_no,
					against_voucher_type=gle.against_voucher_type
					if gle.against_voucher_type
					else gle.voucher_type,
					against_voucher_no=gle.against_voucher if gle.against_voucher else gle.voucher_no,
					account_currency=gle.account_currency,
					amount=dr_or_cr,
					amount_in_account_currency=dr_or_cr_account_currency,
					delinked=True if cancel else False,
					remarks=gle.remarks,
				)

				dimensions_and_defaults = get_dimensions()
				if dimensions_and_defaults:
					for dimension in dimensions_and_defaults[0]:
						ple[dimension.fieldname] = gle.get(dimension.fieldname)

				ple_map.append(ple)
	return ple_map


def create_payment_ledger_entry(
	gl_entries, cancel=0, adv_adj=0, update_outstanding="Yes", from_repost=0, partial_cancel=False
):
	if gl_entries:
		ple_map = get_payment_ledger_entries(gl_entries, cancel=cancel)

		for entry in ple_map:
			ple = frappe.get_doc(entry)

			if cancel:
				delink_original_entry(ple, partial_cancel=partial_cancel)

			ple.flags.ignore_permissions = 1
			ple.flags.adv_adj = adv_adj
			ple.flags.from_repost = from_repost
			ple.flags.update_outstanding = update_outstanding
			ple.submit()


def update_voucher_outstanding(voucher_type, voucher_no, account, party_type, party):
	ple = frappe.qb.DocType("Payment Ledger Entry")
	vouchers = [frappe._dict({"voucher_type": voucher_type, "voucher_no": voucher_no})]
	common_filter = []
	if account:
		common_filter.append(ple.account == account)

	if party_type:
		common_filter.append(ple.party_type == party_type)

	if party:
		common_filter.append(ple.party == party)

	ple_query = QueryPaymentLedger()

	# on cancellation outstanding can be an empty list
	voucher_outstanding = ple_query.get_voucher_outstandings(vouchers, common_filter=common_filter)
	if (
		voucher_type in ["Sales Invoice", "Purchase Invoice", "Fees"]
		and party_type
		and party
		and voucher_outstanding
	):
		outstanding = voucher_outstanding[0]
		ref_doc = frappe.get_doc(voucher_type, voucher_no)

		# Didn't use db_set for optimisation purpose
		ref_doc.outstanding_amount = outstanding["outstanding_in_account_currency"] or 0.0
		frappe.db.set_value(
			voucher_type,
			voucher_no,
			"outstanding_amount",
			outstanding["outstanding_in_account_currency"] or 0.0,
		)

		ref_doc.set_status(update=True)
		ref_doc.notify_update()


def delink_original_entry(pl_entry, partial_cancel=False):
	if pl_entry:
		ple = qb.DocType("Payment Ledger Entry")
		query = (
			qb.update(ple)
			.set(ple.delinked, True)
			.set(ple.modified, now())
			.set(ple.modified_by, frappe.session.user)
			.where(
				(ple.company == pl_entry.company)
				& (ple.account_type == pl_entry.account_type)
				& (ple.account == pl_entry.account)
				& (ple.party_type == pl_entry.party_type)
				& (ple.party == pl_entry.party)
				& (ple.voucher_type == pl_entry.voucher_type)
				& (ple.voucher_no == pl_entry.voucher_no)
				& (ple.against_voucher_type == pl_entry.against_voucher_type)
				& (ple.against_voucher_no == pl_entry.against_voucher_no)
			)
		)

		if partial_cancel:
			query = query.where(ple.voucher_detail_no == pl_entry.voucher_detail_no)

		query.run()


class QueryPaymentLedger:
	"""
	Helper Class for Querying Payment Ledger Entry
	"""

	def __init__(self):
		self.ple = qb.DocType("Payment Ledger Entry")

		# query result
		self.voucher_outstandings = []

		# query filters
		self.vouchers = []
		self.common_filter = []
		self.voucher_posting_date = []
		self.min_outstanding = None
		self.max_outstanding = None
		self.limit = self.voucher_no = None

	def reset(self):
		# clear filters
		self.vouchers.clear()
		self.common_filter.clear()
		self.min_outstanding = self.max_outstanding = self.limit = None

		# clear result
		self.voucher_outstandings.clear()

	def query_for_outstanding(self):
		"""
		Database query to fetch voucher amount and voucher outstanding using Common Table Expression
		"""

		ple = self.ple

		filter_on_voucher_no = []
		filter_on_against_voucher_no = []

		if self.vouchers:
			voucher_types = set([x.voucher_type for x in self.vouchers])
			voucher_nos = set([x.voucher_no for x in self.vouchers])

			filter_on_voucher_no.append(ple.voucher_type.isin(voucher_types))
			filter_on_voucher_no.append(ple.voucher_no.isin(voucher_nos))

			filter_on_against_voucher_no.append(ple.against_voucher_type.isin(voucher_types))
			filter_on_against_voucher_no.append(ple.against_voucher_no.isin(voucher_nos))

		if self.voucher_no:
			filter_on_voucher_no.append(ple.voucher_no.like(f"%{self.voucher_no}%"))
			filter_on_against_voucher_no.append(ple.against_voucher_no.like(f"%{self.voucher_no}%"))

		# build outstanding amount filter
		filter_on_outstanding_amount = []
		if self.min_outstanding:
			if self.min_outstanding > 0:
				filter_on_outstanding_amount.append(
					Table("outstanding").amount_in_account_currency >= self.min_outstanding
				)
			else:
				filter_on_outstanding_amount.append(
					Table("outstanding").amount_in_account_currency <= self.min_outstanding
				)
		if self.max_outstanding:
			if self.max_outstanding > 0:
				filter_on_outstanding_amount.append(
					Table("outstanding").amount_in_account_currency <= self.max_outstanding
				)
			else:
				filter_on_outstanding_amount.append(
					Table("outstanding").amount_in_account_currency >= self.max_outstanding
				)

		if self.limit and self.get_invoices:
			outstanding_vouchers = (
				qb.from_(ple)
				.select(
					ple.against_voucher_no.as_("voucher_no"),
					Sum(ple.amount_in_account_currency).as_("amount_in_account_currency"),
				)
				.where(ple.delinked == 0)
				.where(Criterion.all(filter_on_against_voucher_no))
				.where(Criterion.all(self.common_filter))
				.where(Criterion.all(self.dimensions_filter))
				.where(Criterion.all(self.voucher_posting_date))
				.groupby(ple.against_voucher_type, ple.against_voucher_no, ple.party_type, ple.party)
				.orderby(ple.posting_date, ple.voucher_no)
				.having(qb.Field("amount_in_account_currency") > 0)
				.limit(self.limit)
				.run()
			)
			if outstanding_vouchers:
				filter_on_voucher_no.append(ple.voucher_no.isin([x[0] for x in outstanding_vouchers]))
				filter_on_against_voucher_no.append(
					ple.against_voucher_no.isin([x[0] for x in outstanding_vouchers])
				)

		# build query for voucher amount
		query_voucher_amount = (
			qb.from_(ple)
			.select(
				ple.account,
				ple.voucher_type,
				ple.voucher_no,
				ple.party_type,
				ple.party,
				ple.posting_date,
				ple.due_date,
				ple.account_currency.as_("currency"),
				ple.cost_center.as_("cost_center"),
				Sum(ple.amount).as_("amount"),
				Sum(ple.amount_in_account_currency).as_("amount_in_account_currency"),
			)
			.where(ple.delinked == 0)
			.where(Criterion.all(filter_on_voucher_no))
			.where(Criterion.all(self.common_filter))
			.where(Criterion.all(self.dimensions_filter))
			.where(Criterion.all(self.voucher_posting_date))
			.groupby(ple.voucher_type, ple.voucher_no, ple.party_type, ple.party)
		)

		# build query for voucher outstanding
		query_voucher_outstanding = (
			qb.from_(ple)
			.select(
				ple.account,
				ple.against_voucher_type.as_("voucher_type"),
				ple.against_voucher_no.as_("voucher_no"),
				ple.party_type,
				ple.party,
				ple.posting_date,
				ple.due_date,
				ple.account_currency.as_("currency"),
				Sum(ple.amount).as_("amount"),
				Sum(ple.amount_in_account_currency).as_("amount_in_account_currency"),
			)
			.where(ple.delinked == 0)
			.where(Criterion.all(filter_on_against_voucher_no))
			.where(Criterion.all(self.common_filter))
			.groupby(ple.against_voucher_type, ple.against_voucher_no, ple.party_type, ple.party)
		)

		# build CTE for combining voucher amount and outstanding
		self.cte_query_voucher_amount_and_outstanding = (
			qb.with_(query_voucher_amount, "vouchers")
			.with_(query_voucher_outstanding, "outstanding")
			.from_(AliasedQuery("vouchers"))
			.left_join(AliasedQuery("outstanding"))
			.on(
				(AliasedQuery("vouchers").account == AliasedQuery("outstanding").account)
				& (AliasedQuery("vouchers").voucher_type == AliasedQuery("outstanding").voucher_type)
				& (AliasedQuery("vouchers").voucher_no == AliasedQuery("outstanding").voucher_no)
				& (AliasedQuery("vouchers").party_type == AliasedQuery("outstanding").party_type)
				& (AliasedQuery("vouchers").party == AliasedQuery("outstanding").party)
			)
			.select(
				Table("vouchers").account,
				Table("vouchers").voucher_type,
				Table("vouchers").voucher_no,
				Table("vouchers").party_type,
				Table("vouchers").party,
				Table("vouchers").posting_date,
				Table("vouchers").amount.as_("invoice_amount"),
				Table("vouchers").amount_in_account_currency.as_("invoice_amount_in_account_currency"),
				Table("outstanding").amount.as_("outstanding"),
				Table("outstanding").amount_in_account_currency.as_("outstanding_in_account_currency"),
				(Table("vouchers").amount - Table("outstanding").amount).as_("paid_amount"),
				(
					Table("vouchers").amount_in_account_currency
					- Table("outstanding").amount_in_account_currency
				).as_("paid_amount_in_account_currency"),
				Table("vouchers").due_date,
				Table("vouchers").currency,
				Table("vouchers").cost_center.as_("cost_center"),
			)
			.where(Criterion.all(filter_on_outstanding_amount))
		)

		# build CTE filter
		# only fetch invoices
		if self.get_invoices:
			self.cte_query_voucher_amount_and_outstanding = (
				self.cte_query_voucher_amount_and_outstanding.having(
					qb.Field("outstanding_in_account_currency") > 0
				)
			)
		# only fetch payments
		elif self.get_payments:
			self.cte_query_voucher_amount_and_outstanding = (
				self.cte_query_voucher_amount_and_outstanding.having(
					qb.Field("outstanding_in_account_currency") < 0
				)
			)

		if self.limit:
			self.cte_query_voucher_amount_and_outstanding = (
				self.cte_query_voucher_amount_and_outstanding.limit(self.limit)
			)

		# execute SQL
		self.voucher_outstandings = self.cte_query_voucher_amount_and_outstanding.run(as_dict=True)

	def get_voucher_outstandings(
		self,
		vouchers=None,
		common_filter=None,
		posting_date=None,
		min_outstanding=None,
		max_outstanding=None,
		get_payments=False,
		get_invoices=False,
		accounting_dimensions=None,
		limit=None,
		voucher_no=None,
	):
		"""
		Fetch voucher amount and outstanding amount from Payment Ledger using Database CTE

		vouchers - dict of vouchers to get
		common_filter - array of criterions
		min_outstanding - filter on minimum total outstanding amount
		max_outstanding - filter on maximum total  outstanding amount
		get_invoices - only fetch vouchers(ledger entries with +ve outstanding)
		get_payments - only fetch payments(ledger entries with -ve outstanding)
		"""

		self.reset()
		self.vouchers = vouchers
		self.common_filter = common_filter or []
		self.dimensions_filter = accounting_dimensions or []
		self.voucher_posting_date = posting_date or []
		self.min_outstanding = min_outstanding
		self.max_outstanding = max_outstanding
		self.get_payments = get_payments
		self.get_invoices = get_invoices
		self.limit = limit
		self.voucher_no = voucher_no
		self.query_for_outstanding()

		return self.voucher_outstandings


def create_gain_loss_journal(
	company,
	posting_date,
	party_type,
	party,
	party_account,
	gain_loss_account,
	exc_gain_loss,
	dr_or_cr,
	reverse_dr_or_cr,
	ref1_dt,
	ref1_dn,
	ref1_detail_no,
	ref2_dt,
	ref2_dn,
	ref2_detail_no,
	cost_center,
	dimensions,
) -> str:
	journal_entry = frappe.new_doc("Journal Entry")
	journal_entry.voucher_type = "Exchange Gain Or Loss"
	journal_entry.company = company
	journal_entry.posting_date = posting_date or nowdate()
	journal_entry.multi_currency = 1
	journal_entry.is_system_generated = True

	party_account_currency = frappe.get_cached_value("Account", party_account, "account_currency")

	if not gain_loss_account:
		frappe.throw(_("Please set default Exchange Gain/Loss Account in Company {}").format(company))
	gain_loss_account_currency = get_account_currency(gain_loss_account)
	company_currency = frappe.get_cached_value("Company", company, "default_currency")

	if gain_loss_account_currency != company_currency:
		frappe.throw(_("Currency for {0} must be {1}").format(gain_loss_account, company_currency))

	journal_account = frappe._dict(
		{
			"account": party_account,
			"party_type": party_type,
			"party": party,
			"account_currency": party_account_currency,
			"exchange_rate": 0,
			"cost_center": cost_center or erpnext.get_default_cost_center(company),
			"reference_type": ref1_dt,
			"reference_name": ref1_dn,
			"reference_detail_no": ref1_detail_no,
			dr_or_cr: abs(exc_gain_loss),
			dr_or_cr + "_in_account_currency": 0,
		}
	)
	if dimensions:
		journal_account.update(dimensions)
	journal_entry.append("accounts", journal_account)

	journal_account = frappe._dict(
		{
			"account": gain_loss_account,
			"account_currency": gain_loss_account_currency,
			"exchange_rate": 1,
			"cost_center": cost_center or erpnext.get_default_cost_center(company),
			"reference_type": ref2_dt,
			"reference_name": ref2_dn,
			"reference_detail_no": ref2_detail_no,
			reverse_dr_or_cr + "_in_account_currency": 0,
			reverse_dr_or_cr: abs(exc_gain_loss),
		}
	)
	if dimensions:
		journal_account.update(dimensions)
	journal_entry.append("accounts", journal_account)

	journal_entry.save()
	journal_entry.submit()
	return journal_entry.name


def get_party_types_from_account_type(account_type):
	return frappe.db.get_all("Party Type", {"account_type": account_type}, pluck="name")


def run_ledger_health_checks():
	health_monitor_settings = frappe.get_doc("Ledger Health Monitor")
	if health_monitor_settings.enable_health_monitor:
		period_end = getdate()
		period_start = add_days(period_end, -abs(health_monitor_settings.monitor_for_last_x_days))

		run_date = get_datetime()

		# Debit-Credit mismatch report
		if health_monitor_settings.debit_credit_mismatch:
			for x in health_monitor_settings.companies:
				filters = {"company": x.company, "from_date": period_start, "to_date": period_end}
				voucher_wise = frappe.get_doc("Report", "Voucher-wise Balance")
				res = voucher_wise.execute_script_report(filters=filters)
				for x in res[1]:
					doc = frappe.new_doc("Ledger Health")
					doc.voucher_type = x.voucher_type
					doc.voucher_no = x.voucher_no
					doc.debit_credit_mismatch = True
					doc.checked_on = run_date
					doc.save()

		# General Ledger and Payment Ledger discrepancy
		if health_monitor_settings.general_and_payment_ledger_mismatch:
			for x in health_monitor_settings.companies:
				filters = {
					"company": x.company,
					"period_start_date": period_start,
					"period_end_date": period_end,
				}
				gl_pl_comparison = frappe.get_doc("Report", "General and Payment Ledger Comparison")
				res = gl_pl_comparison.execute_script_report(filters=filters)
				for x in res[1]:
					doc = frappe.new_doc("Ledger Health")
					doc.voucher_type = x.voucher_type
					doc.voucher_no = x.voucher_no
					doc.general_and_payment_ledger_mismatch = True
					doc.checked_on = run_date
					doc.save()
