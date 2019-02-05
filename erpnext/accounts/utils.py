# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, erpnext
import frappe.defaults
from frappe.utils import nowdate, cstr, flt, cint, now, getdate
from frappe import throw, _
from frappe.utils import formatdate, get_number_format_info
from six import iteritems
# imported to enable erpnext.accounts.utils.get_account_currency
from erpnext.accounts.doctype.account.account import get_account_currency

class FiscalYearError(frappe.ValidationError): pass

@frappe.whitelist()
def get_fiscal_year(date=None, fiscal_year=None, label="Date", verbose=1, company=None, as_dict=False):
	return get_fiscal_years(date, fiscal_year, label, verbose, company, as_dict=as_dict)[0]

def get_fiscal_years(transaction_date=None, fiscal_year=None, label="Date", verbose=1, company=None, as_dict=False):
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

		fiscal_years = frappe.db.sql("""
			select
				fy.name, fy.year_start_date, fy.year_end_date
			from
				`tabFiscal Year` fy
			where
				disabled = 0 {0}
			order by
				fy.year_start_date desc""".format(cond), {
				"company": company
			}, as_dict=True)

		frappe.cache().hset("fiscal_years", company, fiscal_years)

	if transaction_date:
		transaction_date = getdate(transaction_date)

	for fy in fiscal_years:
		matched = False
		if fiscal_year and fy.name == fiscal_year:
			matched = True

		if (transaction_date and getdate(fy.year_start_date) <= transaction_date
			and getdate(fy.year_end_date) >= transaction_date):
			matched = True

		if matched:
			if as_dict:
				return (fy,)
			else:
				return ((fy.name, fy.year_start_date, fy.year_end_date),)

	error_msg = _("""{0} {1} not in any active Fiscal Year.""").format(label, formatdate(transaction_date))
	if verbose==1: frappe.msgprint(error_msg)
	raise FiscalYearError(error_msg)

def validate_fiscal_year(date, fiscal_year, company, label="Date", doc=None):
	years = [f[0] for f in get_fiscal_years(date, label=_(label), company=company)]
	if fiscal_year not in years:
		if doc:
			doc.fiscal_year = years[0]
		else:
			throw(_("{0} '{1}' not in Fiscal Year {2}").format(label, formatdate(date), fiscal_year))

@frappe.whitelist()
def get_balance_on(account=None, date=None, party_type=None, party=None, company=None, in_account_currency=True, cost_center=None):
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


	cond = []
	if date:
		cond.append("posting_date <= '%s'" % frappe.db.escape(cstr(date)))
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

	allow_cost_center_in_entry_of_bs_account = get_allow_cost_center_in_entry_of_bs_account()

	if cost_center and allow_cost_center_in_entry_of_bs_account:
		cc = frappe.get_doc("Cost Center", cost_center)
		if cc.is_group:
			cond.append(""" exists (
				select 1 from `tabCost Center` cc where cc.name = gle.cost_center
				and cc.lft >= %s and cc.rgt <= %s
			)""" % (cc.lft, cc.rgt))

		else:
			cond.append("""gle.cost_center = "%s" """ % (frappe.db.escape(cost_center, percent=False), ))


	if account:

		acc = frappe.get_doc("Account", account)

		if not frappe.flags.ignore_account_permission:
			acc.check_permission("read")


		if not allow_cost_center_in_entry_of_bs_account and acc.report_type == 'Profit and Loss':
			# for pl accounts, get balance within a fiscal year
			cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" \
				% year_start_date)
		elif allow_cost_center_in_entry_of_bs_account:
			# for all accounts, get balance within a fiscal year if maintain cost center in balance account is checked
			cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" \
				% year_start_date)
		# different filter for group and ledger - improved performance
		if acc.is_group:
			cond.append("""exists (
				select name from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= %s and ac.rgt <= %s
			)""" % (acc.lft, acc.rgt))

			# If group and currency same as company,
			# always return balance based on debit and credit in company currency
			if acc.account_currency == frappe.get_cached_value('Company',  acc.company,  "default_currency"):
				in_account_currency = False
		else:
			cond.append("""gle.account = "%s" """ % (frappe.db.escape(account, percent=False), ))

	if party_type and party:
		cond.append("""gle.party_type = "%s" and gle.party = "%s" """ %
			(frappe.db.escape(party_type), frappe.db.escape(party, percent=False)))

	if company:
		cond.append("""gle.company = "%s" """ % (frappe.db.escape(company, percent=False)))

	if account or (party_type and party):
		if in_account_currency:
			select_field = "sum(debit_in_account_currency) - sum(credit_in_account_currency)"
		else:
			select_field = "sum(debit) - sum(credit)"
		bal = frappe.db.sql("""
			SELECT {0}
			FROM `tabGL Entry` gle
			WHERE {1}""".format(select_field, " and ".join(cond)))[0][0]

		# if bal is None, return 0
		return flt(bal)

def get_balance_on_voucher(voucher_type, voucher_no, party_type, party, account, dr_or_cr=None):
	if not dr_or_cr:
		if erpnext.get_party_account_type(party_type) == 'Receivable':
			dr_or_cr = "debit_in_account_currency - credit_in_account_currency"
		else:
			dr_or_cr = "credit_in_account_currency - debit_in_account_currency"

	res = frappe.db.sql("""
		select ifnull(sum({dr_or_cr}), 0)
		from `tabGL Entry`
		where party_type=%(party_type)s and party=%(party)s and account=%(account)s
			and ((voucher_type=%(voucher_type)s and voucher_no=%(voucher_no)s and (against_voucher is null or against_voucher=''))
				or (against_voucher_type=%(voucher_type)s and against_voucher=%(voucher_no)s))
	""".format(dr_or_cr=dr_or_cr),
	{"voucher_type": voucher_type, "voucher_no": voucher_no, "party_type": party_type, "party": party, "account": account})

	return flt(res[0][0]) if res else 0.0

def get_count_on(account, fieldname, date):
	cond = []
	if date:
		cond.append("posting_date <= '%s'" % frappe.db.escape(cstr(date)))
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
		if acc.report_type == 'Profit and Loss':
			cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" \
				% year_start_date)

		# different filter for group and ledger - improved performance
		if acc.is_group:
			cond.append("""exists (
				select name from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= %s and ac.rgt <= %s
			)""" % (acc.lft, acc.rgt))
		else:
			cond.append("""gle.account = "%s" """ % (frappe.db.escape(account, percent=False), ))

		entries = frappe.db.sql("""
			SELECT name, posting_date, account, party_type, party,debit,credit,
				voucher_type, voucher_no, against_voucher_type, against_voucher
			FROM `tabGL Entry` gle
			WHERE {0}""".format(" and ".join(cond)), as_dict=True)

		count = 0
		for gle in entries:
			if fieldname not in ('invoiced_amount','payables'):
				count += 1
			else:
				dr_or_cr = "debit" if fieldname == "invoiced_amount" else "credit"
				cr_or_dr = "credit" if fieldname == "invoiced_amount" else "debit"
				select_fields = "ifnull(sum(credit-debit),0)" \
					if fieldname == "invoiced_amount" else "ifnull(sum(debit-credit),0)"

				if ((not gle.against_voucher) or (gle.against_voucher_type in ["Sales Order", "Purchase Order"]) or
				(gle.against_voucher==gle.voucher_no and gle.get(dr_or_cr) > 0)):
					payment_amount = frappe.db.sql("""
						SELECT {0}
						FROM `tabGL Entry` gle
						WHERE docstatus < 2 and posting_date <= %(date)s and against_voucher = %(voucher_no)s
						and party = %(party)s and name != %(name)s"""
						.format(select_fields),
						{"date": date, "voucher_no": gle.voucher_no,
							"party": gle.party, "name": gle.name})[0][0]

					outstanding_amount = flt(gle.get(dr_or_cr)) - flt(gle.get(cr_or_dr)) - payment_amount
					currency_precision = get_currency_precision() or 2
					if abs(flt(outstanding_amount)) > 0.1/10**currency_precision:
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
		args.parent_cost_center = "{0} - {1}".format(args.parent_cost_center,
			frappe.get_cached_value('Company',  args.company,  'abbr'))

	cc = frappe.new_doc("Cost Center")
	cc.update(args)

	if not cc.parent_cost_center:
		cc.parent_cost_center = args.get("parent")

	cc.old_parent = ""
	cc.insert()
	return cc.name

def reconcile_against_document(args):
	"""
		Cancel JV, Update aginst document, split if required and resubmit jv
	"""
	for d in args:

		check_if_advance_entry_modified(d)
		validate_allocated_amount(d)

		# cancel advance entry
		doc = frappe.get_doc(d.voucher_type, d.voucher_no)

		doc.make_gl_entries(cancel=1, adv_adj=1)

		# update ref in advance entry
		if d.voucher_type == "Journal Entry":
			update_reference_in_journal_entry(d, doc)
		else:
			update_reference_in_payment_entry(d, doc)

		# re-submit advance entry
		doc = frappe.get_doc(d.voucher_type, d.voucher_no)
		doc.make_gl_entries(cancel = 0, adv_adj =1)

def check_if_advance_entry_modified(args):
	"""
		check if there is already a voucher reference
		check if amount is same
		check if jv is submitted
	"""
	ret = None
	if args.voucher_type == "Journal Entry":
		if args.voucher_detail_no:
			ret = frappe.db.sql("""select je.name
				from `tabJournal Entry` je, `tabJournal Entry Account` jea
				where
					je.name = jea.parent and jea.account = %(account)s and je.docstatus=1
					and je.name = %(voucher_no)s and jea.name = %(voucher_detail_no)s
					and jea.party_type = %(party_type)s and jea.party = %(party)s
					and ifnull(jea.reference_type, '') in ('', 'Sales Order', 'Purchase Order')
					and jea.{dr_or_cr} = %(unadjusted_amount)s""".format(dr_or_cr=args.dr_or_cr), args)
		else:
			if erpnext.get_party_account_type(args.party_type) == 'Receivable':
				dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
			else:
				dr_or_cr = "debit_in_account_currency - credit_in_account_currency"

			ret = frappe.db.sql("""
				select sum({dr_or_cr}) as outstanding_amount
				from `tabGL Entry`
				where
				((voucher_type='Journal Entry' and voucher_no=%(voucher_no)s and (against_voucher is null or against_voucher=''))
					or (against_voucher_type='Journal Entry' and against_voucher=%(voucher_no)s))
				and party_type=%(party_type)s and party=%(party)s and account=%(account)s
				having outstanding_amount=%(unadjusted_amount)s""".format(dr_or_cr=dr_or_cr), args)
	else:
		party_account_field = ("paid_from"
			if erpnext.get_party_account_type(args.party_type) == 'Receivable' else "paid_to")

		if args.voucher_detail_no:
			ret = frappe.db.sql("""select pe.name
				from `tabPayment Entry` pe, `tabPayment Entry Reference` pref
				where
					pe.name = pref.parent and pe.docstatus = 1
					and pe.name = %(voucher_no)s and pref.name = %(voucher_detail_no)s
					and pe.party_type = %(party_type)s and pe.party = %(party)s and pe.{0} = %(account)s
					and pref.reference_doctype in ('Sales Order', 'Purchase Order')
					and pref.allocated_amount = %(unadjusted_amount)s
			""".format(party_account_field), args)
		else:
			ret = frappe.db.sql("""select name from `tabPayment Entry`
				where
					name = %(voucher_no)s and docstatus = 1
					and party_type = %(party_type)s and party = %(party)s and {0} = %(account)s
					and unallocated_amount = %(unadjusted_amount)s
			""".format(party_account_field), args)

	if not ret:
		throw(_("""Payment Entry has been modified after you pulled it. Please pull it again."""))

def validate_allocated_amount(args):
	if args.get("allocated_amount") < 0:
		throw(_("Allocated amount can not be negative"))
	elif args.get("allocated_amount") > args.get("unadjusted_amount"):
		throw(_("Allocated amount can not greater than unadjusted amount"))

def update_reference_in_journal_entry(d, jv_doc):
	"""
		Updates against document, if partial amount splits into rows
	"""
	rows_to_reconcile = []
	if d.get("voucher_detail_no"):
		rows_to_reconcile.append(jv_doc.get("accounts", {"name": d["voucher_detail_no"]})[0])
	else:
		rows_to_reconcile += jv_doc.get("accounts", {
			"reference_type": None,
			"reference_name": None,
			"party_type": d["party_type"],
			"party": d["party"],
			"account": d["account"]
		})

	to_update_advance_amount = []
	amt_allocated = 0.0
	for jv_detail in rows_to_reconcile:
		amt_allocatable = min(jv_detail.get(d["dr_or_cr"]), d["allocated_amount"] - amt_allocated)
		original_dr_or_cr = jv_detail.get(d["dr_or_cr"])
		original_reference_type = jv_detail.reference_type
		original_reference_name = jv_detail.reference_name

		if original_reference_type in ("Sales Order", "Purchase Order", "Employee Advance"):
			to_update_advance_amount.append((original_reference_type, original_reference_name))

		jv_detail.set(d["dr_or_cr"], amt_allocatable)
		jv_detail.set('debit' if d['dr_or_cr']=='debit_in_account_currency' else 'credit',
			amt_allocatable*flt(jv_detail.exchange_rate))

		jv_detail.set("reference_type", d["against_voucher_type"])
		jv_detail.set("reference_name", d["against_voucher"])

		if amt_allocatable < original_dr_or_cr:
			jvd = frappe.db.sql("""
				select cost_center, balance, against_account, account_type, exchange_rate, account_currency
				from `tabJournal Entry Account` where name = %s
			""", jv_detail.name, as_dict=True)

			amount_in_account_currency = flt(original_dr_or_cr) - flt(amt_allocatable)
			amount_in_company_currency = amount_in_account_currency * flt(jvd[0]['exchange_rate'])

			# new entry with balance amount
			ch = jv_doc.append("accounts")
			ch.account = d['account']
			ch.account_type = jvd[0]['account_type']
			ch.account_currency = jvd[0]['account_currency']
			ch.exchange_rate = jvd[0]['exchange_rate']
			ch.party_type = d["party_type"]
			ch.party = d["party"]
			ch.cost_center = cstr(jvd[0]["cost_center"])
			ch.balance = flt(jvd[0]["balance"])

			ch.set(d['dr_or_cr'], amount_in_account_currency)
			ch.set('debit' if d['dr_or_cr']=='debit_in_account_currency' else 'credit', amount_in_company_currency)

			ch.set('credit_in_account_currency' if d['dr_or_cr']== 'debit_in_account_currency'
				else 'debit_in_account_currency', 0)
			ch.set('credit' if d['dr_or_cr']== 'debit_in_account_currency' else 'debit', 0)

			ch.against_account = cstr(jvd[0]["against_account"])
			ch.reference_type = original_reference_type
			ch.reference_name = original_reference_name
			ch.docstatus = 1

		amt_allocated += amt_allocatable
		if abs(amt_allocated - d["allocated_amount"]) < (1.0 / (10**(jv_detail.precision(d['dr_or_cr'])))):
			break

	# will work as update after submit
	jv_doc.flags.ignore_validate_update_after_submit = True
	jv_doc.save(ignore_permissions=True)

	for dn, dt in set(to_update_advance_amount):
		frappe.get_doc(dn, dt).set_total_advance_paid()

def update_reference_in_payment_entry(d, payment_entry):
	reference_details = {
		"reference_doctype": d.against_voucher_type,
		"reference_name": d.against_voucher,
		"total_amount": d.grand_total,
		"outstanding_amount": d.outstanding_amount,
		"allocated_amount": d.allocated_amount,
		"exchange_rate": d.exchange_rate
	}

	to_update_advance_amount = []

	if d.voucher_detail_no:
		existing_row = payment_entry.get("references", {"name": d["voucher_detail_no"]})[0]
		original_row = existing_row.as_dict().copy()
		existing_row.update(reference_details)

		if original_row.reference_doctype in ("Sales Order", "Purchase Order", "Employee Advance"):
			to_update_advance_amount.append((original_row.reference_doctype, original_row.reference_name))

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
	payment_entry.save(ignore_permissions=True)

	for dn, dt in set(to_update_advance_amount):
		frappe.get_doc(dn, dt).set_total_advance_paid()

def unlink_ref_doc_from_payment_entries(ref_doc):
	remove_ref_doc_link_from_jv(ref_doc.doctype, ref_doc.name)
	remove_ref_doc_link_from_pe(ref_doc.doctype, ref_doc.name)

	frappe.db.sql("""update `tabGL Entry`
		set against_voucher_type=null, against_voucher=null,
		modified=%s, modified_by=%s
		where against_voucher_type=%s and against_voucher=%s
		and voucher_no != ifnull(against_voucher, '')""",
		(now(), frappe.session.user, ref_doc.doctype, ref_doc.name))

	if ref_doc.doctype in ("Sales Invoice", "Purchase Invoice"):
		ref_doc.set("advances", [])

		frappe.db.sql("""delete from `tab{0} Advance` where parent = %s"""
			.format(ref_doc.doctype), ref_doc.name)

def remove_ref_doc_link_from_jv(ref_type, ref_no):
	linked_jv = frappe.db.sql_list("""select parent from `tabJournal Entry Account`
		where reference_type=%s and reference_name=%s and docstatus < 2""", (ref_type, ref_no))

	if linked_jv:
		frappe.db.sql("""update `tabJournal Entry Account`
			set reference_type=null, reference_name = null,
			modified=%s, modified_by=%s
			where reference_type=%s and reference_name=%s
			and docstatus < 2""", (now(), frappe.session.user, ref_type, ref_no))

		msg_jv_list = ["<a href='#Form/Journal Entry/{0}'>{0}</a>".format(jv) for jv in list(set(linked_jv))]
		frappe.msgprint(_("Journal Entries {0} are un-linked").format(", ".join(msg_jv_list)))

def remove_ref_doc_link_from_pe(ref_type, ref_no):
	linked_pe = frappe.db.sql_list("""select parent from `tabPayment Entry Reference`
		where reference_doctype=%s and reference_name=%s and docstatus < 2""", (ref_type, ref_no))

	if linked_pe:
		frappe.db.sql("""update `tabPayment Entry Reference`
			set allocated_amount=0, modified=%s, modified_by=%s
			where reference_doctype=%s and reference_name=%s
			and docstatus < 2""", (now(), frappe.session.user, ref_type, ref_no))

		for pe in linked_pe:
			pe_doc = frappe.get_doc("Payment Entry", pe)
			pe_doc.set_total_allocated_amount()
			pe_doc.set_unallocated_amount()
			pe_doc.clear_unallocated_reference_document_rows()

			frappe.db.sql("""update `tabPayment Entry` set total_allocated_amount=%s,
				base_total_allocated_amount=%s, unallocated_amount=%s, modified=%s, modified_by=%s
				where name=%s""", (pe_doc.total_allocated_amount, pe_doc.base_total_allocated_amount,
					pe_doc.unallocated_amount, now(), frappe.session.user, pe))

		msg_pe_list = ["<a href='#Form/Payment Entry/{0}'>{0}</a>".format(jv) for jv in list(set(linked_pe))]
		frappe.msgprint(_("Payment Entries {0} are un-linked").format(", ".join(msg_pe_list)))

@frappe.whitelist()
def get_company_default(company, fieldname):
	value = frappe.get_cached_value('Company',  company,  fieldname)

	if not value:
		throw(_("Please set default {0} in Company {1}")
			.format(frappe.get_meta("Company").get_label(fieldname), company))

	return value

def fix_total_debit_credit():
	vouchers = frappe.db.sql("""select voucher_type, voucher_no,
		sum(debit) - sum(credit) as diff
		from `tabGL Entry`
		group by voucher_type, voucher_no
		having sum(debit) != sum(credit)""", as_dict=1)

	for d in vouchers:
		if abs(d.diff) > 0:
			dr_or_cr = d.voucher_type == "Sales Invoice" and "credit" or "debit"

			frappe.db.sql("""update `tabGL Entry` set %s = %s + %s
				where voucher_type = %s and voucher_no = %s and %s > 0 limit 1""" %
				(dr_or_cr, dr_or_cr, '%s', '%s', '%s', dr_or_cr),
				(d.diff, d.voucher_type, d.voucher_no))

def get_stock_and_account_difference(account_list=None, posting_date=None):
	from erpnext.stock.utils import get_stock_value_on
	from erpnext.stock import get_warehouse_account_map

	if not posting_date: posting_date = nowdate()

	difference = {}
	warehouse_account = get_warehouse_account_map()

	for warehouse, account_data in iteritems(warehouse_account):
		if account_data.get('account') in account_list:
			account_balance = get_balance_on(account_data.get('account'), posting_date, in_account_currency=False)
			stock_value = get_stock_value_on(warehouse, posting_date)
			if abs(flt(stock_value) - flt(account_balance)) > 0.005:
				difference.setdefault(account_data.get('account'), flt(stock_value) - flt(account_balance))

	return difference

def get_currency_precision():
	precision = cint(frappe.db.get_default("currency_precision"))
	if not precision:
		number_format = frappe.db.get_default("number_format") or "#,###.##"
		precision = get_number_format_info(number_format)[2]

	return precision

def get_stock_rbnb_difference(posting_date, company):
	stock_items = frappe.db.sql_list("""select distinct item_code
		from `tabStock Ledger Entry` where company=%s""", company)

	pr_valuation_amount = frappe.db.sql("""
		select sum(pr_item.valuation_rate * pr_item.qty * pr_item.conversion_factor)
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
		where pr.name = pr_item.parent and pr.docstatus=1 and pr.company=%s
		and pr.posting_date <= %s and pr_item.item_code in (%s)""" %
		('%s', '%s', ', '.join(['%s']*len(stock_items))), tuple([company, posting_date] + stock_items))[0][0]

	pi_valuation_amount = frappe.db.sql("""
		select sum(pi_item.valuation_rate * pi_item.qty * pi_item.conversion_factor)
		from `tabPurchase Invoice Item` pi_item, `tabPurchase Invoice` pi
		where pi.name = pi_item.parent and pi.docstatus=1 and pi.company=%s
		and pi.posting_date <= %s and pi_item.item_code in (%s)""" %
		('%s', '%s', ', '.join(['%s']*len(stock_items))), tuple([company, posting_date] + stock_items))[0][0]

	# Balance should be
	stock_rbnb = flt(pr_valuation_amount, 2) - flt(pi_valuation_amount, 2)

	# Balance as per system
	stock_rbnb_account = "Stock Received But Not Billed - " + frappe.get_cached_value('Company',  company,  "abbr")
	sys_bal = get_balance_on(stock_rbnb_account, posting_date, in_account_currency=False)

	# Amount should be credited
	return flt(stock_rbnb) + flt(sys_bal)


def get_held_invoices(party_type, party):
	"""
	Returns a list of names Purchase Invoices for the given party that are on hold
	"""
	held_invoices = []

	if party_type == 'Supplier':
		held_invoices = frappe.db.sql(
			'select name from `tabPurchase Invoice` where release_date IS NOT NULL and release_date > CURDATE()',
			as_dict=1
		)
		held_invoices = [d['name'] for d in held_invoices]

	return held_invoices


def get_outstanding_invoices(party_type, party, account, condition=None, negative_invoices=False, limit=1000):
	outstanding_invoices = []
	precision = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2

	if erpnext.get_party_account_type(party_type) == 'Receivable':
		dr_or_cr = "debit_in_account_currency - credit_in_account_currency"
		payment_dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
	else:
		dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
		payment_dr_or_cr = "debit_in_account_currency - credit_in_account_currency"

	held_invoices = get_held_invoices(party_type, party)

	invoice_list = frappe.db.sql("""
		select
			voucher_no, voucher_type, posting_date, ifnull(sum({dr_or_cr}), 0) as invoice_amount
		from
			`tabGL Entry`
		where
			party_type = %(party_type)s and party = %(party)s and account = %(account)s
			and (against_voucher = '' or against_voucher is null) and voucher_type != 'Payment Entry'
			{condition}
		group by voucher_type, voucher_no
		order by posting_date, name
		limit %(limit)s
	""".format(dr_or_cr=dr_or_cr, condition=condition or ""), {
		"party_type": party_type,
		"party": party,
		"account": account,
		"limit": limit or 1000
	}, as_dict=True)

	payment_entries = frappe.db.sql("""
		select
			against_voucher_type, against_voucher, ifnull(sum({payment_dr_or_cr}), 0) as payment_amount
		from
			`tabGL Entry`
		where
			party_type = %(party_type)s and party = %(party)s and account = %(account)s
			and against_voucher is not null and against_voucher != ''
		group by against_voucher_type, against_voucher
	""".format(payment_dr_or_cr=payment_dr_or_cr), {
		"party_type": party_type,
		"party": party,
		"account": account,
	}, as_dict=True)

	pe_map = frappe._dict()
	for d in payment_entries:
		pe_map.setdefault((d.against_voucher_type, d.against_voucher), d.payment_amount)

	for d in invoice_list:
		payment_amount = pe_map.get((d.voucher_type, d.voucher_no), 0)
		outstanding_amount = flt(d.invoice_amount - payment_amount, precision)
		diff = -outstanding_amount if negative_invoices else outstanding_amount
		if diff > 0.5 / (10**precision):
			if not d.voucher_type == "Purchase Invoice" or d.voucher_no not in held_invoices:
				due_date = frappe.db.get_value(
					d.voucher_type, d.voucher_no, "posting_date" if party_type == "Employee" else "due_date")

				outstanding_invoices.append(
					frappe._dict({
						'voucher_no': d.voucher_no,
						'voucher_type': d.voucher_type,
						'posting_date': d.posting_date,
						'invoice_amount': flt(d.invoice_amount),
						'payment_amount': payment_amount,
						'outstanding_amount': outstanding_amount,
						'due_date': due_date
					})
				)

	outstanding_invoices = sorted(outstanding_invoices, key=lambda k: k['due_date'] or getdate(nowdate()))
	return outstanding_invoices


def get_account_name(account_type=None, root_type=None, is_group=None, account_currency=None, company=None):
	"""return account based on matching conditions"""
	return frappe.db.get_value("Account", {
		"account_type": account_type or '',
		"root_type": root_type or '',
		"is_group": is_group or 0,
		"account_currency": account_currency or frappe.defaults.get_defaults().currency,
		"company": company or frappe.defaults.get_defaults().company
	}, "name")

@frappe.whitelist()
def get_companies():
	"""get a list of companies based on permission"""
	return [d.name for d in frappe.get_list("Company", fields=["name"],
		order_by="name")]

@frappe.whitelist()
def get_children(doctype, parent, company, is_root=False):
	from erpnext.accounts.report.financial_statements import sort_accounts

	parent_fieldname = 'parent_' + doctype.lower().replace(' ', '_')
	fields = [
		'name as value',
		'is_group as expandable'
	]
	filters = [['docstatus', '<', 2]]

	filters.append(['ifnull(`{0}`,"")'.format(parent_fieldname), '=', '' if is_root else parent])

	if is_root:
		fields += ['root_type', 'report_type', 'account_currency'] if doctype == 'Account' else []
		filters.append(['company', '=', company])

	else:
		fields += ['account_currency'] if doctype == 'Account' else []
		fields += [parent_fieldname + ' as parent']

	acc = frappe.get_list(doctype, fields=fields, filters=filters)

	if doctype == 'Account':
		sort_accounts(acc, is_root, key="value")
		company_currency = frappe.get_cached_value('Company',  company,  "default_currency")
		for each in acc:
			each["company_currency"] = company_currency
			each["balance"] = flt(get_balance_on(each.get("value"), in_account_currency=False))

			if each.account_currency != company_currency:
				each["balance_in_account_currency"] = flt(get_balance_on(each.get("value")))

	return acc

def create_payment_gateway_account(gateway):
	from erpnext.setup.setup_wizard.operations.company_setup import create_bank_account

	company = frappe.db.get_value("Global Defaults", None, "default_company")
	if not company:
		return

	# NOTE: we translate Payment Gateway account name because that is going to be used by the end user
	bank_account = frappe.db.get_value("Account", {"account_name": _(gateway), "company": company},
		["name", 'account_currency'], as_dict=1)

	if not bank_account:
		# check for untranslated one
		bank_account = frappe.db.get_value("Account", {"account_name": gateway, "company": company},
			["name", 'account_currency'], as_dict=1)

	if not bank_account:
		# try creating one
		bank_account = create_bank_account({"company_name": company, "bank_account": _(gateway)})

	if not bank_account:
		frappe.msgprint(_("Payment Gateway Account not created, please create one manually."))
		return

	# if payment gateway account exists, return
	if frappe.db.exists("Payment Gateway Account",
		{"payment_gateway": gateway, "currency": bank_account.account_currency}):
		return

	try:
		frappe.get_doc({
			"doctype": "Payment Gateway Account",
			"is_default": 1,
			"payment_gateway": gateway,
			"payment_account": bank_account.name,
			"currency": bank_account.account_currency
		}).insert(ignore_permissions=True)

	except frappe.DuplicateEntryError:
		# already exists, due to a reinstall?
		pass

@frappe.whitelist()
def update_number_field(doctype_name, name, field_name, number_value, company):
	'''
		doctype_name = Name of the DocType
		name = Docname being referred
		field_name = Name of the field thats holding the 'number' attribute
		number_value = Numeric value entered in field_name

		Stores the number entered in the dialog to the DocType's field.

		Renames the document by adding the number as a prefix to the current name and updates
		all transaction where it was present.
	'''
	doc_title = frappe.db.get_value(doctype_name, name, frappe.scrub(doctype_name)+"_name")

	validate_field_number(doctype_name, name, number_value, company, field_name)

	frappe.db.set_value(doctype_name, name, field_name, number_value)

	if doc_title[0].isdigit():
		separator = " - " if " - " in doc_title else " "
		doc_title = doc_title.split(separator, 1)[1]

	frappe.db.set_value(doctype_name, name, frappe.scrub(doctype_name)+"_name", doc_title)

	new_name = get_autoname_with_number(number_value, doc_title, name, company)

	if name != new_name:
		frappe.rename_doc(doctype_name, name, new_name)
		return new_name

def validate_field_number(doctype_name, name, number_value, company, field_name):
	''' Validate if the number entered isn't already assigned to some other document. '''
	if number_value:
		if company:
			doctype_with_same_number = frappe.db.get_value(doctype_name,
				{field_name: number_value, "company": company, "name": ["!=", name]})
		else:
			doctype_with_same_number = frappe.db.get_value(doctype_name,
				{field_name: number_value, "name": ["!=", name]})
		if doctype_with_same_number:
			frappe.throw(_("{0} Number {1} already used in account {2}")
				.format(doctype_name, number_value, doctype_with_same_number))

def get_autoname_with_number(number_value, doc_title, name, company):
	''' append title with prefix as number and suffix as company's abbreviation separated by '-' '''
	if name:
		name_split=name.split("-")
		parts = [doc_title.strip(), name_split[len(name_split)-1].strip()]
	else:
		abbr = frappe.get_cached_value('Company',  company,  ["abbr"], as_dict=True)
		parts = [doc_title.strip(), abbr.abbr]
	if cstr(number_value).strip():
		parts.insert(0, cstr(number_value).strip())
	return ' - '.join(parts)

@frappe.whitelist()
def get_coa(doctype, parent, is_root, chart=None):
	from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import build_tree_from_json

	# add chart to flags to retrieve when called from expand all function
	chart = chart if chart else frappe.flags.chart
	frappe.flags.chart = chart

	parent = None if parent==_('All Accounts') else parent
	accounts = build_tree_from_json(chart) # returns alist of dict in a tree render-able form

	# filter out to show data for the selected node only
	accounts = [d for d in accounts if d['parent_account']==parent]

	return accounts

def get_allow_cost_center_in_entry_of_bs_account():
	def generator():
		return cint(frappe.db.get_value('Accounts Settings', None, 'allow_cost_center_in_entry_of_bs_account'))
	return frappe.local_cache("get_allow_cost_center_in_entry_of_bs_account", (), generator, regenerate_if_none=True)
