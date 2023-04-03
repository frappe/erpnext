# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from json import loads
from typing import TYPE_CHECKING, List, Optional, Tuple

import frappe
import frappe.defaults
from frappe import _, throw
from frappe.model.meta import get_field_precision
from frappe.utils import (
	cint,
	create_batch,
	cstr,
	flt,
	formatdate,
	get_number_format_info,
	getdate,
	now,
	nowdate,
)
from six import string_types

import erpnext

# imported to enable erpnext.accounts.utils.get_account_currency
from erpnext.accounts.doctype.account.account import get_account_currency  # noqa
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
	date=None, fiscal_year=None, label="Date", verbose=1, company=None, as_dict=False
):
	return get_fiscal_years(date, fiscal_year, label, verbose, company, as_dict=as_dict)[0]


def get_fiscal_years(
	transaction_date=None, fiscal_year=None, label="Date", verbose=1, company=None, as_dict=False
):
	fiscal_years = frappe.cache().hget("fiscal_years", company) or []

	if not fiscal_years:
		# if year start date is 2012-04-01, year end date should be 2013-03-31 (hence subdate)
		cond = ""
		if fiscal_year:
			cond += " and fy.name = {0}".format(frappe.db.escape(fiscal_year))
		if company:
			cond += """
				and (not exists (select name
					from `tabFiscal Year Company` fyc
					where fyc.parent = fy.name)
				or exists(select company
					from `tabFiscal Year Company` fyc
					where fyc.parent = fy.name
					and fyc.company=%(company)s)
				)
			"""

		fiscal_years = frappe.db.sql(
			"""
			select
				fy.name, fy.year_start_date, fy.year_end_date
			from
				`tabFiscal Year` fy
			where
				disabled = 0 {0}
			order by
				fy.year_start_date desc""".format(
				cond
			),
			{"company": company},
			as_dict=True,
		)

		frappe.cache().hset("fiscal_years", company, fiscal_years)

	if not transaction_date and not fiscal_year:
		return fiscal_years

	if transaction_date:
		transaction_date = getdate(transaction_date)

	for fy in fiscal_years:
		matched = False
		if fiscal_year and fy.name == fiscal_year:
			matched = True

		if (
			transaction_date
			and getdate(fy.year_start_date) <= transaction_date
			and getdate(fy.year_end_date) >= transaction_date
		):
			matched = True

		if matched:
			if as_dict:
				return (fy,)
			else:
				return ((fy.name, fy.year_start_date, fy.year_end_date),)

	error_msg = _("""{0} {1} is not in any active Fiscal Year""").format(
		label, formatdate(transaction_date)
	)
	if company:
		error_msg = _("""{0} for {1}""").format(error_msg, frappe.bold(company))

	if verbose == 1:
		frappe.msgprint(error_msg)
	raise FiscalYearError(error_msg)


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
	if date:
		cond.append("posting_date <= %s" % frappe.db.escape(cstr(date)))
	else:
		# get balance of all entries that exist
		date = nowdate()

	if account:
		acc = frappe.get_doc("Account", account)

	try:
		year_start_date = get_fiscal_year(date, company=company, verbose=0)[1]
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
		report_type = acc.report_type
	else:
		report_type = ""

	if cost_center and report_type == "Profit and Loss":
		cc = frappe.get_doc("Cost Center", cost_center)
		if cc.is_group:
			cond.append(
				""" exists (
				select 1 from `tabCost Center` cc where cc.name = gle.cost_center
				and cc.lft >= %s and cc.rgt <= %s
			)"""
				% (cc.lft, cc.rgt)
			)

		else:
			cond.append("""gle.cost_center = %s """ % (frappe.db.escape(cost_center, percent=False),))

	if account:

		if not (frappe.flags.ignore_account_permission or ignore_account_permission):
			acc.check_permission("read")

		if report_type == "Profit and Loss":
			# for pl accounts, get balance within a fiscal year
			cond.append(
				"posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" % year_start_date
			)
		# different filter for group and ledger - improved performance
		if acc.is_group:
			cond.append(
				"""exists (
				select name from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= %s and ac.rgt <= %s
			)"""
				% (acc.lft, acc.rgt)
			)

			# If group and currency same as company,
			# always return balance based on debit and credit in company currency
			if acc.account_currency == frappe.get_cached_value("Company", acc.company, "default_currency"):
				in_account_currency = False
		else:
			cond.append("""gle.account = %s """ % (frappe.db.escape(account, percent=False),))

	if party_type and party:
		cond.append(
			"""gle.party_type = %s and gle.party = %s """
			% (frappe.db.escape(party_type), frappe.db.escape(party, percent=False))
		)

	if company:
		cond.append("""gle.company = %s """ % (frappe.db.escape(company, percent=False)))

	if account or (party_type and party):
		if in_account_currency:
			select_field = "sum(debit_in_account_currency) - sum(credit_in_account_currency)"
		else:
			select_field = "sum(debit) - sum(credit)"
		bal = frappe.db.sql(
			"""
			SELECT {0}
			FROM `tabGL Entry` gle
			WHERE {1}""".format(
				select_field, " and ".join(cond)
			)
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
			cond.append(
				"posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" % year_start_date
			)

		# different filter for group and ledger - improved performance
		if acc.is_group:
			cond.append(
				"""exists (
				select name from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= %s and ac.rgt <= %s
			)"""
				% (acc.lft, acc.rgt)
			)
		else:
			cond.append("""gle.account = %s """ % (frappe.db.escape(account, percent=False),))

		entries = frappe.db.sql(
			"""
			SELECT name, posting_date, account, party_type, party,debit,credit,
				voucher_type, voucher_no, against_voucher_type, against_voucher
			FROM `tabGL Entry` gle
			WHERE {0}""".format(
				" and ".join(cond)
			),
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
						"""
						SELECT {0}
						FROM `tabGL Entry` gle
						WHERE docstatus < 2 and posting_date <= %(date)s and against_voucher = %(voucher_no)s
						and party = %(party)s and name != %(name)s""".format(
							select_fields
						),
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
		args.parent_cost_center = "{0} - {1}".format(
			args.parent_cost_center, frappe.get_cached_value("Company", args.company, "abbr")
		)

	cc = frappe.new_doc("Cost Center")
	cc.update(args)

	if not cc.parent_cost_center:
		cc.parent_cost_center = args.get("parent")

	cc.old_parent = ""
	cc.insert()
	return cc.name


def reconcile_against_document(args):
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
		doc.make_gl_entries(cancel=1, adv_adj=1)

		for entry in entries:
			check_if_advance_entry_modified(entry)
			validate_allocated_amount(entry)

			# update ref in advance entry
			if voucher_type == "Journal Entry":
				update_reference_in_journal_entry(entry, doc, do_not_save=True)
			else:
				update_reference_in_payment_entry(entry, doc, do_not_save=True)

		doc.save(ignore_permissions=True)
		# re-submit advance entry
		doc = frappe.get_doc(entry.voucher_type, entry.voucher_no)
		doc.make_gl_entries(cancel=0, adv_adj=1)
		frappe.flags.ignore_party_validation = False

		if entry.voucher_type in ("Payment Entry", "Journal Entry"):
			doc.update_expense_claim()


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
		ret = frappe.db.sql(
			"""
			select t2.{dr_or_cr} from `tabJournal Entry` t1, `tabJournal Entry Account` t2
			where t1.name = t2.parent and t2.account = %(account)s
			and t2.party_type = %(party_type)s and t2.party = %(party)s
			and (t2.reference_type is null or t2.reference_type in ("", "Sales Order", "Purchase Order"))
			and t1.name = %(voucher_no)s and t2.name = %(voucher_detail_no)s
			and t1.docstatus=1 """.format(
				dr_or_cr=args.get("dr_or_cr")
			),
			args,
		)
	else:
		party_account_field = (
			"paid_from" if erpnext.get_party_account_type(args.party_type) == "Receivable" else "paid_to"
		)

		if args.voucher_detail_no:
			ret = frappe.db.sql(
				"""select t1.name
				from `tabPayment Entry` t1, `tabPayment Entry Reference` t2
				where
					t1.name = t2.parent and t1.docstatus = 1
					and t1.name = %(voucher_no)s and t2.name = %(voucher_detail_no)s
					and t1.party_type = %(party_type)s and t1.party = %(party)s and t1.{0} = %(account)s
					and t2.reference_doctype in ("", "Sales Order", "Purchase Order")
					and t2.allocated_amount = %(unreconciled_amount)s
			""".format(
					party_account_field
				),
				args,
			)
		else:
			ret = frappe.db.sql(
				"""select name from `tabPayment Entry`
				where
					name = %(voucher_no)s and docstatus = 1
					and party_type = %(party_type)s and party = %(party)s and {0} = %(account)s
					and unallocated_amount = %(unreconciled_amount)s
			""".format(
					party_account_field
				),
				args,
			)

	if not ret:
		throw(_("""Payment Entry has been modified after you pulled it. Please pull it again."""))


def validate_allocated_amount(args):
	precision = args.get("precision") or frappe.db.get_single_value(
		"System Settings", "currency_precision"
	)
	if args.get("allocated_amount") < 0:
		throw(_("Allocated amount cannot be negative"))
	elif flt(args.get("allocated_amount"), precision) > flt(args.get("unadjusted_amount"), precision):
		throw(_("Allocated amount cannot be greater than unadjusted amount"))


def update_reference_in_journal_entry(d, journal_entry, do_not_save=False):
	"""
	Updates against document, if partial amount splits into rows
	"""
	jv_detail = journal_entry.get("accounts", {"name": d["voucher_detail_no"]})[0]

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

	new_row.update((frappe.copy_doc(jv_detail)).as_dict())

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
	if not do_not_save:
		journal_entry.save(ignore_permissions=True)


def update_reference_in_payment_entry(d, payment_entry, do_not_save=False):
	reference_details = {
		"reference_doctype": d.against_voucher_type,
		"reference_name": d.against_voucher,
		"total_amount": d.grand_total,
		"outstanding_amount": d.outstanding_amount,
		"allocated_amount": d.allocated_amount,
		"exchange_rate": d.exchange_rate
		if not d.exchange_gain_loss
		else payment_entry.get_exchange_rate(),
		"exchange_gain_loss": d.exchange_gain_loss,  # only populated from invoice in case of advance allocation
	}

	if d.voucher_detail_no:
		existing_row = payment_entry.get("references", {"name": d["voucher_detail_no"]})[0]
		original_row = existing_row.as_dict().copy()
		existing_row.update(reference_details)

		if d.allocated_amount < original_row.allocated_amount:
			new_row = payment_entry.append("references")
			new_row.docstatus = 1
			for field in list(reference_details):
				new_row.set(field, original_row[field])

			new_row.allocated_amount = original_row.allocated_amount - d.allocated_amount
	else:
		new_row = payment_entry.append("references")
		new_row.docstatus = 1
		new_row.update(reference_details)

	payment_entry.flags.ignore_validate_update_after_submit = True
	payment_entry.setup_party_account_field()
	payment_entry.set_missing_values()
	payment_entry.set_amounts()

	if d.difference_amount and d.difference_account:
		account_details = {
			"account": d.difference_account,
			"cost_center": payment_entry.cost_center
			or frappe.get_cached_value("Company", payment_entry.company, "cost_center"),
		}
		if d.difference_amount:
			account_details["amount"] = d.difference_amount

		payment_entry.set_gain_or_loss(account_details=account_details)

	if not do_not_save:
		payment_entry.save(ignore_permissions=True)


def unlink_ref_doc_from_payment_entries(ref_doc):
	remove_ref_doc_link_from_jv(ref_doc.doctype, ref_doc.name)
	remove_ref_doc_link_from_pe(ref_doc.doctype, ref_doc.name)

	frappe.db.sql(
		"""update `tabGL Entry`
		set against_voucher_type=null, against_voucher=null,
		modified=%s, modified_by=%s
		where against_voucher_type=%s and against_voucher=%s
		and voucher_no != ifnull(against_voucher, '')""",
		(now(), frappe.session.user, ref_doc.doctype, ref_doc.name),
	)

	if ref_doc.doctype in ("Sales Invoice", "Purchase Invoice"):
		ref_doc.set("advances", [])

		frappe.db.sql(
			"""delete from `tab{0} Advance` where parent = %s""".format(ref_doc.doctype), ref_doc.name
		)


def remove_ref_doc_link_from_jv(ref_type, ref_no):
	linked_jv = frappe.db.sql_list(
		"""select parent from `tabJournal Entry Account`
		where reference_type=%s and reference_name=%s and docstatus < 2""",
		(ref_type, ref_no),
	)

	if linked_jv:
		frappe.db.sql(
			"""update `tabJournal Entry Account`
			set reference_type=null, reference_name = null,
			modified=%s, modified_by=%s
			where reference_type=%s and reference_name=%s
			and docstatus < 2""",
			(now(), frappe.session.user, ref_type, ref_no),
		)

		frappe.msgprint(_("Journal Entries {0} are un-linked").format("\n".join(linked_jv)))


def remove_ref_doc_link_from_pe(ref_type, ref_no):
	linked_pe = frappe.db.sql_list(
		"""select parent from `tabPayment Entry Reference`
		where reference_doctype=%s and reference_name=%s and docstatus < 2""",
		(ref_type, ref_no),
	)

	if linked_pe:
		frappe.db.sql(
			"""update `tabPayment Entry Reference`
			set allocated_amount=0, modified=%s, modified_by=%s
			where reference_doctype=%s and reference_name=%s
			and docstatus < 2""",
			(now(), frappe.session.user, ref_type, ref_no),
		)

		for pe in linked_pe:
			try:
				pe_doc = frappe.get_doc("Payment Entry", pe)
				pe_doc.set_amounts()
				pe_doc.clear_unallocated_reference_document_rows()
				pe_doc.validate_payment_type_with_outstanding()
			except Exception as e:
				msg = _("There were issues unlinking payment entry {0}.").format(pe_doc.name)
				msg += "<br>"
				msg += _("Please cancel payment entry manually first")
				frappe.throw(msg, exc=PaymentEntryUnlinkError, title=_("Payment Unlink Error"))

			frappe.db.sql(
				"""update `tabPayment Entry` set total_allocated_amount=%s,
				base_total_allocated_amount=%s, unallocated_amount=%s, modified=%s, modified_by=%s
				where name=%s""",
				(
					pe_doc.total_allocated_amount,
					pe_doc.base_total_allocated_amount,
					pe_doc.unallocated_amount,
					now(),
					frappe.session.user,
					pe,
				),
			)

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
				"""update `tabGL Entry` set %s = %s + %s
				where voucher_type = %s and voucher_no = %s and %s > 0 limit 1"""
				% (dr_or_cr, dr_or_cr, "%s", "%s", "%s", dr_or_cr),
				(d.diff, d.voucher_type, d.voucher_no),
			)


def get_currency_precision():
	precision = cint(frappe.db.get_default("currency_precision"))
	if not precision:
		number_format = frappe.db.get_default("number_format") or "#,###.##"
		precision = get_number_format_info(number_format)[2]

	return precision


def get_stock_rbnb_difference(posting_date, company):
	stock_items = frappe.db.sql_list(
		"""select distinct item_code
		from `tabStock Ledger Entry` where company=%s""",
		company,
	)

	pr_valuation_amount = frappe.db.sql(
		"""
		select sum(pr_item.valuation_rate * pr_item.qty * pr_item.conversion_factor)
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
		where pr.name = pr_item.parent and pr.docstatus=1 and pr.company=%s
		and pr.posting_date <= %s and pr_item.item_code in (%s)"""
		% ("%s", "%s", ", ".join(["%s"] * len(stock_items))),
		tuple([company, posting_date] + stock_items),
	)[0][0]

	pi_valuation_amount = frappe.db.sql(
		"""
		select sum(pi_item.valuation_rate * pi_item.qty * pi_item.conversion_factor)
		from `tabPurchase Invoice Item` pi_item, `tabPurchase Invoice` pi
		where pi.name = pi_item.parent and pi.docstatus=1 and pi.company=%s
		and pi.posting_date <= %s and pi_item.item_code in (%s)"""
		% ("%s", "%s", ", ".join(["%s"] * len(stock_items))),
		tuple([company, posting_date] + stock_items),
	)[0][0]

	# Balance should be
	stock_rbnb = flt(pr_valuation_amount, 2) - flt(pi_valuation_amount, 2)

	# Balance as per system
	stock_rbnb_account = "Stock Received But Not Billed - " + frappe.get_cached_value(
		"Company", company, "abbr"
	)
	sys_bal = get_balance_on(stock_rbnb_account, posting_date, in_account_currency=False)

	# Amount should be credited
	return flt(stock_rbnb) + flt(sys_bal)


def get_held_invoices(party_type, party):
	"""
	Returns a list of names Purchase Invoices for the given party that are on hold
	"""
	held_invoices = None

	if party_type == "Supplier":
		held_invoices = frappe.db.sql(
			"select name from `tabPurchase Invoice` where release_date IS NOT NULL and release_date > CURDATE()",
			as_dict=1,
		)
		held_invoices = set(d["name"] for d in held_invoices)

	return held_invoices


def remove_return_pos_invoices(party_type, party, invoice_list):
	if invoice_list:

		if party_type == "Customer":
			sinv = frappe.qb.DocType("Sales Invoice")
			return_pos = (
				frappe.qb.from_(sinv)
				.select(sinv.name)
				.where((sinv.is_pos == 1) & (sinv.docstatus == 1) & (sinv.is_return == 1))
				.run()
			)

			if return_pos:
				return_pos = [x[0] for x in return_pos]
			else:
				return invoice_list

			invoice_list = [x for x in invoice_list if x.voucher_no not in return_pos]

	return invoice_list


def get_outstanding_invoices(party_type, party, account, company, condition=None, filters=None):
	outstanding_invoices = []
	precision = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2

	if account:
		root_type, account_type = frappe.get_cached_value(
			"Account", account, ["root_type", "account_type"]
		)
		party_account_type = "Receivable" if root_type == "Asset" else "Payable"
		party_account_type = account_type or party_account_type
	else:
		party_account_type = erpnext.get_party_account_type(party_type)

	if party_account_type == "Receivable":
		dr_or_cr = "debit_in_account_currency - credit_in_account_currency"
		payment_dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
	else:
		dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
		payment_dr_or_cr = "debit_in_account_currency - credit_in_account_currency"

	held_invoices = get_held_invoices(party_type, party)

	invoice_list = frappe.db.sql(
		"""
		select
			voucher_no, voucher_type, posting_date, due_date,
			ifnull(sum({dr_or_cr}), 0) as invoice_amount,
			account_currency as currency
		from
			`tabGL Entry`
		where
			party_type = %(party_type)s and party = %(party)s
			and account = %(account)s and {dr_or_cr} > 0
			and is_cancelled=0
			{condition}
			and ((voucher_type = 'Journal Entry'
					and (against_voucher = '' or against_voucher is null))
				or (voucher_type not in ('Journal Entry', 'Payment Entry')))
		group by voucher_type, voucher_no
		order by posting_date, name""".format(
			dr_or_cr=dr_or_cr, condition=condition or ""
		),
		{
			"party_type": party_type,
			"party": party,
			"account": account,
		},
		as_dict=True,
	)

	invoice_list = remove_return_pos_invoices(party_type, party, invoice_list)

	if invoice_list:
		invoices = [d.voucher_no for d in invoice_list]
		payment_entries = frappe.db.sql(
			"""
			select against_voucher_type, against_voucher,
				ifnull(sum({payment_dr_or_cr}), 0) as payment_amount
			from `tabGL Entry`
			where
				company = %(company)s
				and party_type = %(party_type)s and party = %(party)s
				and account = %(account)s
				and {payment_dr_or_cr} > 0
				and ifnull(against_voucher, '') != ''
				and is_cancelled=0
				and against_voucher in %(invoices)s
			group by against_voucher_type, against_voucher
		""".format(
				payment_dr_or_cr=payment_dr_or_cr,
			),
			{
				"company": company,
				"party_type": party_type,
				"party": party,
				"account": account,
				"invoices": invoices,
			},
			as_dict=True,
		)

		pe_map = frappe._dict()
		for d in payment_entries:
			pe_map.setdefault((d.against_voucher_type, d.against_voucher), d.payment_amount)

		for d in invoice_list:
			payment_amount = pe_map.get((d.voucher_type, d.voucher_no), 0)
			outstanding_amount = flt(d.invoice_amount - payment_amount, precision)
			if outstanding_amount > 0.5 / (10**precision):
				if (
					filters
					and filters.get("outstanding_amt_greater_than")
					and not (
						outstanding_amount >= filters.get("outstanding_amt_greater_than")
						and outstanding_amount <= filters.get("outstanding_amt_less_than")
					)
				):
					continue

				if not d.voucher_type == "Purchase Invoice" or d.voucher_no not in held_invoices:
					outstanding_invoices.append(
						frappe._dict(
							{
								"voucher_no": d.voucher_no,
								"voucher_type": d.voucher_type,
								"posting_date": d.posting_date,
								"invoice_amount": flt(d.invoice_amount),
								"payment_amount": payment_amount,
								"outstanding_amount": outstanding_amount,
								"due_date": d.due_date,
								"currency": d.currency,
							}
						)
					)

		outstanding_invoices = sorted(
			outstanding_invoices, key=lambda k: k["due_date"] or getdate(nowdate())
		)

	return outstanding_invoices


def get_account_name(
	account_type=None, root_type=None, is_group=None, account_currency=None, company=None
):
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
def get_children(doctype, parent, company, is_root=False):
	from erpnext.accounts.report.financial_statements import sort_accounts

	parent_fieldname = "parent_" + doctype.lower().replace(" ", "_")
	fields = ["name as value", "is_group as expandable"]
	filters = [["docstatus", "<", 2]]

	filters.append(['ifnull(`{0}`,"")'.format(parent_fieldname), "=", "" if is_root else parent])

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

	if isinstance(accounts, string_types):
		accounts = loads(accounts)

	if not accounts:
		return []

	company_currency = frappe.get_cached_value("Company", company, "default_currency")

	for account in accounts:
		account["company_currency"] = company_currency
		account["balance"] = flt(
			get_balance_on(account["value"], in_account_currency=False, company=company)
		)
		if account["account_currency"] and account["account_currency"] != company_currency:
			account["balance_in_account_currency"] = flt(get_balance_on(account["value"], company=company))

	return accounts


def create_payment_gateway_account(gateway, payment_channel="Email"):
	from erpnext.setup.setup_wizard.operations.install_fixtures import create_bank_account

	company = frappe.db.get_value("Global Defaults", None, "default_company")
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
		).insert(ignore_permissions=True)

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

	new_name = get_autoname_with_number(cost_center_number, cost_center_name, docname, company)
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


def get_autoname_with_number(number_value, doc_title, name, company):
	"""append title with prefix as number and suffix as company's abbreviation separated by '-'"""
	if name:
		name_split = name.split("-")
		parts = [doc_title.strip(), name_split[len(name_split) - 1].strip()]
	else:
		abbr = frappe.get_cached_value("Company", company, ["abbr"], as_dict=True)
		parts = [doc_title.strip(), abbr.abbr]
	if cstr(number_value).strip():
		parts.insert(0, cstr(number_value).strip())
	return " - ".join(parts)


@frappe.whitelist()
def get_coa(doctype, parent, is_root, chart=None):
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
	stock_vouchers = get_future_stock_vouchers(
		posting_date, posting_time, for_warehouses, for_items, company
	)
	repost_gle_for_stock_vouchers(stock_vouchers, posting_date, company, warehouse_account)


def repost_gle_for_stock_vouchers(
	stock_vouchers: List[Tuple[str, str]],
	posting_date: str,
	company: Optional[str] = None,
	warehouse_account=None,
	repost_doc: Optional["RepostItemValuation"] = None,
):
	if not stock_vouchers:
		return

	if not warehouse_account:
		warehouse_account = get_warehouse_account_map(company)

	precision = get_field_precision(frappe.get_meta("GL Entry").get_field("debit")) or 2

	stock_vouchers = sort_stock_vouchers_by_posting_date(stock_vouchers)
	if repost_doc and repost_doc.gl_reposting_index:
		# Restore progress
		stock_vouchers = stock_vouchers[cint(repost_doc.gl_reposting_index) :]

	for stock_vouchers_chunk in create_batch(stock_vouchers, GL_REPOSTING_CHUNK):
		gle = get_voucherwise_gl_entries(stock_vouchers_chunk, posting_date)
		for voucher_type, voucher_no in stock_vouchers_chunk:
			existing_gle = gle.get((voucher_type, voucher_no), [])
			voucher_obj = frappe.get_doc(voucher_type, voucher_no)
			expected_gle = voucher_obj.get_gl_entries(warehouse_account)
			if expected_gle:
				if not existing_gle or not compare_existing_and_expected_gle(
					existing_gle, expected_gle, precision
				):
					_delete_gl_entries(voucher_type, voucher_no)
					voucher_obj.make_gl_entries(gl_entries=expected_gle, from_repost=True)
			else:
				_delete_gl_entries(voucher_type, voucher_no)

		if not frappe.flags.in_test:
			frappe.db.commit()

		if repost_doc:
			repost_doc.db_set(
				"gl_reposting_index", cint(repost_doc.gl_reposting_index) + len(stock_vouchers_chunk)
			)


def _delete_gl_entries(voucher_type, voucher_no):
	frappe.db.sql(
		"""delete from `tabGL Entry`
		where voucher_type=%s and voucher_no=%s""",
		(voucher_type, voucher_no),
	)


def sort_stock_vouchers_by_posting_date(
	stock_vouchers: List[Tuple[str, str]]
) -> List[Tuple[str, str]]:
	sle = frappe.qb.DocType("Stock Ledger Entry")
	voucher_nos = [v[1] for v in stock_vouchers]

	sles = (
		frappe.qb.from_(sle)
		.select(sle.voucher_type, sle.voucher_no, sle.posting_date, sle.posting_time, sle.creation)
		.where((sle.is_cancelled == 0) & (sle.voucher_no.isin(voucher_nos)))
		.groupby(sle.voucher_type, sle.voucher_no)
		.orderby(sle.posting_date)
		.orderby(sle.posting_time)
		.orderby(sle.creation)
	).run(as_dict=True)
	sorted_vouchers = [(sle.voucher_type, sle.voucher_no) for sle in sles]

	unknown_vouchers = set(stock_vouchers) - set(sorted_vouchers)
	if unknown_vouchers:
		sorted_vouchers.extend(unknown_vouchers)

	return sorted_vouchers


def get_future_stock_vouchers(
	posting_date, posting_time, for_warehouses=None, for_items=None, company=None
):

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
		"""select distinct sle.voucher_type, sle.voucher_no
		from `tabStock Ledger Entry` sle
		where
			timestamp(sle.posting_date, sle.posting_time) >= timestamp(%s, %s)
			and is_cancelled = 0
			{condition}
		order by timestamp(sle.posting_date, sle.posting_time) asc, creation asc for update""".format(
			condition=condition
		),
		tuple([posting_date, posting_time] + values),
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
			posting_date >= %s and voucher_no in (%s)"""
		% ("%s", ", ".join(["%s"] * len(voucher_nos))),
		tuple([posting_date] + voucher_nos),
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


def get_stock_accounts(company, voucher_type=None, voucher_no=None):
	stock_accounts = [
		d.name
		for d in frappe.db.get_all(
			"Account", {"account_type": "Stock", "company": company, "is_group": 0}
		)
	]
	if voucher_type and voucher_no:
		if voucher_type == "Journal Entry":
			stock_accounts = [
				d.account
				for d in frappe.db.get_all(
					"Journal Entry Account", {"parent": voucher_no, "account": ["in", stock_accounts]}, "account"
				)
			]

		else:
			stock_accounts = [
				d.account
				for d in frappe.db.get_all(
					"GL Entry",
					{"voucher_type": voucher_type, "voucher_no": voucher_no, "account": ["in", stock_accounts]},
					"account",
				)
			]

	return stock_accounts


def get_stock_and_account_balance(account=None, posting_date=None, company=None):
	if not posting_date:
		posting_date = nowdate()

	warehouse_account = get_warehouse_account_map(company)

	account_balance = get_balance_on(
		account, posting_date, in_account_currency=False, ignore_account_permission=True
	)

	related_warehouses = [
		wh
		for wh, wh_details in warehouse_account.items()
		if wh_details.account == account and not wh_details.is_group
	]

	total_stock_value = 0.0
	for warehouse in related_warehouses:
		value = get_stock_value_on(warehouse, posting_date)
		total_stock_value += value

	precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
	return flt(account_balance, precision), flt(total_stock_value, precision), related_warehouses


def get_journal_entry(account, stock_adjustment_account, amount):
	db_or_cr_warehouse_account = (
		"credit_in_account_currency" if amount < 0 else "debit_in_account_currency"
	)
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
