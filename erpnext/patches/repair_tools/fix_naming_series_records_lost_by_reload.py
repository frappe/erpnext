# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
import re
from frappe.model.naming import make_autoname
from frappe.utils import cint
from frappe.email import sendmail_to_system_managers

doctype_series_map = {
	'Attendance': 'ATT-',
	'C-Form': 'C-FORM-',
	'Customer': 'CUST-',
	'Warranty Claim': 'CI-',
	'Delivery Note': 'DN-',
	'Installation Note': 'IN-',
	'Item': 'ITEM-',
	'Journal Entry': 'JV-',
	'Lead': 'LEAD-',
	'Opportunity': 'OPTY-',
	'Packing Slip': 'PS-',
	'Production Order': 'PRO-',
	'Purchase Invoice': 'PINV-',
	'Purchase Order': 'PO-',
	'Purchase Receipt': 'PREC-',
	'Quality Inspection': 'QI-',
	'Quotation': 'QTN-',
	'Sales Invoice': 'SINV-',
	'Sales Order': 'SO-',
	'Stock Entry': 'STE-',
	'Supplier': 'SUPP-',
	'Supplier Quotation': 'SQTN-',
	'Issue': 'SUP-'
}

def check_docs_to_rename():
	if "erpnext" not in frappe.get_installed_apps():
		return

	docs_to_rename = get_docs_to_rename()
	if docs_to_rename:
		print "To Rename"
		print json.dumps(docs_to_rename, indent=1, sort_keys=True)

	frappe.db.rollback()

def check_gl_sl_entries_to_fix():
	if "erpnext" not in frappe.get_installed_apps():
		return

	gl_entries_to_fix = get_gl_entries_to_fix()
	if gl_entries_to_fix:
		print "General Ledger Entries to Fix"
		print json.dumps(gl_entries_to_fix, indent=1, sort_keys=True)

	sl_entries_to_fix = get_sl_entries_to_fix()
	if sl_entries_to_fix:
		print "Stock Ledger Entries to Fix"
		print json.dumps(sl_entries_to_fix, indent=1, sort_keys=True)

	frappe.db.rollback()

def guess_reference_date():
	return (frappe.db.get_value("Patch Log", {"patch": "erpnext.patches.v4_0.validate_v3_patch"}, "creation")
		or "2014-05-06")

def get_docs_to_rename():
	reference_date = guess_reference_date()

	docs_to_rename = {}
	for doctype, new_series in doctype_series_map.items():
		if doctype in ("Item", "Customer", "Lead", "Supplier"):
			if not frappe.db.sql("""select name from `tab{doctype}`
				where ifnull(naming_series, '')!=''
				and name like concat(naming_series, '%%') limit 1""".format(doctype=doctype)):
				continue

		# fix newly formed records using old series!
		records_with_new_series = frappe.db.sql_list("""select name from `tab{doctype}`
			where date(creation) >= date(%s) and naming_series=%s
			and exists (select name from `tab{doctype}` where ifnull(naming_series, '') not in ('', %s) limit 1)
			order by name asc""".format(doctype=doctype), (reference_date, new_series, new_series))

		if records_with_new_series:
			docs_to_rename[doctype] = records_with_new_series

	return docs_to_rename

def get_gl_entries_to_fix():
	bad_gl_entries = {}

	for dt in frappe.db.sql_list("""select distinct voucher_type from `tabGL Entry`
		where ifnull(voucher_type, '')!=''"""):

		if dt not in doctype_series_map:
			continue

		out = frappe.db.sql("""select gl.name, gl.voucher_no from `tabGL Entry` gl
			where ifnull(voucher_type, '')=%s and voucher_no like %s and
			not exists (select name from `tab{voucher_type}` vt where vt.name=gl.voucher_no)""".format(voucher_type=dt),
			(dt, doctype_series_map[dt] + "%%"), as_dict=True)

		if out:
			bad_gl_entries.setdefault(dt, []).extend(out)

	for dt in frappe.db.sql_list("""select distinct against_voucher_type
		from `tabGL Entry` where ifnull(against_voucher_type, '')!=''"""):

		if dt not in doctype_series_map:
			continue

		out = frappe.db.sql("""select gl.name, gl.against_voucher from `tabGL Entry` gl
			where ifnull(against_voucher_type, '')=%s and against_voucher like %s and
			not exists (select name from `tab{against_voucher_type}` vt
				where vt.name=gl.against_voucher)""".format(against_voucher_type=dt),
			(dt, doctype_series_map[dt] + "%%"), as_dict=True)

		if out:
			bad_gl_entries.setdefault(dt, []).extend(out)

	return bad_gl_entries

def get_sl_entries_to_fix():
	bad_sl_entries = {}

	for dt in frappe.db.sql_list("""select distinct voucher_type from `tabStock Ledger Entry`
		where ifnull(voucher_type, '')!=''"""):

		if dt not in doctype_series_map:
			continue

		out = frappe.db.sql("""select sl.name, sl.voucher_no from `tabStock Ledger Entry` sl
			where voucher_type=%s and voucher_no like %s and
			not exists (select name from `tab{voucher_type}` vt where vt.name=sl.voucher_no)""".format(voucher_type=dt),
			(dt, doctype_series_map[dt] + "%%"), as_dict=True)
		if out:
			bad_sl_entries.setdefault(dt, []).extend(out)

	return bad_sl_entries

def add_comment(doctype, old_name, new_name):
	frappe.get_doc({
		"doctype":"Comment",
		"comment_by": frappe.session.user,
		"comment_doctype": doctype,
		"comment_docname": new_name,
		"comment": """Renamed from **{old_name}** to {new_name}""".format(old_name=old_name, new_name=new_name)
	}).insert(ignore_permissions=True)

def _rename_doc(doctype, name, naming_series):
	if frappe.get_meta(doctype).get_field("amended_from"):
		amended_from = frappe.db.get_value(doctype, name, "amended_from")
	else:
		amended_from = None

	if amended_from:
		am_id = 1
		am_prefix = amended_from
		if frappe.db.get_value(doctype, amended_from, "amended_from"):
			am_id = cint(amended_from.split('-')[-1]) + 1
			am_prefix = '-'.join(amended_from.split('-')[:-1]) # except the last hyphen

		fixed_name = am_prefix + '-' + str(am_id)
	else:
		fixed_name = make_autoname(naming_series+'.#####')

	frappe.db.set_value(doctype, name, "naming_series", naming_series)
	frappe.rename_doc(doctype, name, fixed_name, force=True)
	add_comment(doctype, name, fixed_name)

	return fixed_name

def rename_docs():
	_log = []
	def log(msg):
		_log.append(msg)
		print msg

	commit = False
	docs_to_rename = get_docs_to_rename()
	for doctype, list_of_names in docs_to_rename.items():
		naming_series_field = frappe.get_meta(doctype).get_field("naming_series")
		default_series = naming_series_field.default or filter(None, (naming_series_field.options or "").split("\n"))[0]

		print
		print "Rename", doctype, list_of_names, "using series", default_series
		confirm = raw_input("do it? (yes / anything else): ")

		if confirm == "yes":
			commit = True
			for name in list_of_names:
				fixed_name = _rename_doc(doctype, name, default_series)
				log("Renamed {doctype} {name} --> {fixed_name}".format(doctype=doctype, name=name, fixed_name=fixed_name))

	if commit:
		content = """These documents have been renamed in your ERPNext instance: {site}\n\n{_log}""".format(site=frappe.local.site, _log="\n".join(_log))

		print content

		frappe.db.commit()

		sendmail_to_system_managers("[Important] [ERPNext] Renamed Documents via Patch", content)

def fix_comments():
	renamed_docs_comments = frappe.db.sql("""select name, comment, comment_doctype, comment_docname
		from `tabComment` where comment like 'Renamed from **%** to %'
		order by comment_doctype, comment_docname""", as_dict=True)

	# { "comment_doctype": [("old_comment_docname", "new_comment_docname", ['comment1', 'comment2', ...])] }
	comments_to_rename = {}

	for comment in renamed_docs_comments:
		old_comment_docname, new_comment_docname = re.findall("""Renamed from \*\*([^\*]*)\*\* to (.*)""", comment.comment)[0]
		if not frappe.db.exists(comment.comment_doctype, old_comment_docname):
			orphaned_comments = frappe.db.sql_list("""select comment from `tabComment`
				where comment_doctype=%s and comment_docname=%s""", (comment.comment_doctype, old_comment_docname))
			if orphaned_comments:
				to_rename = (old_comment_docname, new_comment_docname, orphaned_comments)
				comments_to_rename.setdefault(comment.comment_doctype, []).append(to_rename)

	for doctype in comments_to_rename:
		if not comments_to_rename[doctype]:
			continue

		print
		print "Fix comments for", doctype, ":"
		for (old_comment_docname, new_comment_docname, comments) in comments_to_rename[doctype]:
			print
			print old_comment_docname, "-->", new_comment_docname
			print "\n".join(comments)

		print
		confirm = raw_input("do it? (yes / anything else): ")
		if confirm=="yes":
			for (old_comment_docname, new_comment_docname, comments) in comments_to_rename[doctype]:
				fix_comment(doctype, old_comment_docname, new_comment_docname)
			print "Fixed"

	frappe.db.commit()

def fix_comment(comment_doctype, old_comment_docname, new_comment_docname):
	frappe.db.sql("""update `tabComment` set comment_docname=%s
		where comment_doctype=%s and comment_docname=%s""",
		(new_comment_docname, comment_doctype, old_comment_docname))

