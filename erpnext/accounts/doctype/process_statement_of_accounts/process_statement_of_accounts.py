# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import copy

import frappe
from frappe import _
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe.utils import add_days, add_months, format_date, getdate, today
from frappe.utils.jinja import validate_template
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_print_style

from erpnext import get_company_currency
from erpnext.accounts.party import get_party_account_currency
from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as get_ar_soa
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
	execute as get_ageing,
)
from erpnext.accounts.report.general_ledger.general_ledger import execute as get_soa


class ProcessStatementOfAccounts(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.process_statement_of_accounts_customer.process_statement_of_accounts_customer import (
			ProcessStatementOfAccountsCustomer,
		)
		from erpnext.accounts.doctype.psoa_cost_center.psoa_cost_center import PSOACostCenter
		from erpnext.accounts.doctype.psoa_project.psoa_project import PSOAProject

		account: DF.Link | None
		ageing_based_on: DF.Literal["Due Date", "Posting Date"]
		based_on_payment_terms: DF.Check
		body: DF.TextEditor | None
		cc_to: DF.Link | None
		collection_name: DF.DynamicLink | None
		company: DF.Link
		cost_center: DF.TableMultiSelect[PSOACostCenter]
		currency: DF.Link | None
		customer_collection: DF.Literal["", "Customer Group", "Territory", "Sales Partner", "Sales Person"]
		customers: DF.Table[ProcessStatementOfAccountsCustomer]
		enable_auto_email: DF.Check
		filter_duration: DF.Int
		finance_book: DF.Link | None
		frequency: DF.Literal["Weekly", "Monthly", "Quarterly"]
		from_date: DF.Date | None
		group_by: DF.Literal["", "Group by Voucher", "Group by Voucher (Consolidated)"]
		ignore_exchange_rate_revaluation_journals: DF.Check
		include_ageing: DF.Check
		include_break: DF.Check
		letter_head: DF.Link | None
		orientation: DF.Literal["Landscape", "Portrait"]
		payment_terms_template: DF.Link | None
		pdf_name: DF.Data | None
		posting_date: DF.Date | None
		primary_mandatory: DF.Check
		project: DF.TableMultiSelect[PSOAProject]
		report: DF.Literal["General Ledger", "Accounts Receivable"]
		sales_partner: DF.Link | None
		sales_person: DF.Link | None
		sender: DF.Link | None
		show_net_values_in_party_account: DF.Check
		start_date: DF.Date | None
		subject: DF.Data | None
		terms_and_conditions: DF.Link | None
		territory: DF.Link | None
		to_date: DF.Date | None
	# end: auto-generated types

	def validate(self):
		if not self.subject:
			self.subject = "Statement Of Accounts for {{ customer.customer_name }}"
		if not self.body:
			if self.report == "General Ledger":
				body_str = " from {{ doc.from_date }} to {{ doc.to_date }}."
			else:
				body_str = " until {{ doc.posting_date }}."
			self.body = "Hello {{ customer.customer_name }},<br>PFA your Statement Of Accounts" + body_str
		if not self.pdf_name:
			self.pdf_name = "{{ customer.customer_name }}"

		validate_template(self.subject)
		validate_template(self.body)

		if not self.customers:
			frappe.throw(_("Customers not selected."))

		if self.enable_auto_email:
			if self.start_date and getdate(self.start_date) >= getdate(today()):
				self.to_date = self.start_date
				self.from_date = add_months(self.to_date, -1 * self.filter_duration)


def get_report_pdf(doc, consolidated=True):
	statement_dict = get_statement_dict(doc)
	if not bool(statement_dict):
		return False
	elif consolidated:
		delimiter = '<div style="page-break-before: always;"></div>' if doc.include_break else ""
		result = delimiter.join(list(statement_dict.values()))
		return get_pdf(result, {"orientation": doc.orientation})
	else:
		for customer, statement_html in statement_dict.items():
			statement_dict[customer] = get_pdf(statement_html, {"orientation": doc.orientation})
		return statement_dict


def get_statement_dict(doc, get_statement_dict=False):
	statement_dict = {}
	ageing = ""

	for entry in doc.customers:
		if doc.include_ageing:
			ageing = set_ageing(doc, entry)

		tax_id = frappe.get_doc("Customer", entry.customer).tax_id
		presentation_currency = (
			get_party_account_currency("Customer", entry.customer, doc.company)
			or doc.currency
			or get_company_currency(doc.company)
		)

		filters = get_common_filters(doc)
		if doc.ignore_exchange_rate_revaluation_journals:
			filters.update({"ignore_err": True})

		if doc.report == "General Ledger":
			filters.update(get_gl_filters(doc, entry, tax_id, presentation_currency))
			col, res = get_soa(filters)
			for x in [0, -2, -1]:
				res[x]["account"] = res[x]["account"].replace("'", "")
			if len(res) == 3:
				continue
		else:
			filters.update(get_ar_filters(doc, entry))
			ar_res = get_ar_soa(filters)
			col, res = ar_res[0], ar_res[1]
			if not res:
				continue

		statement_dict[entry.customer] = (
			[res, ageing] if get_statement_dict else get_html(doc, filters, entry, col, res, ageing)
		)

	return statement_dict


def set_ageing(doc, entry):
	ageing_filters = frappe._dict(
		{
			"company": doc.company,
			"report_date": doc.posting_date,
			"ageing_based_on": doc.ageing_based_on,
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
			"party_type": "Customer",
			"party": [entry.customer],
		}
	)
	col1, ageing = get_ageing(ageing_filters)

	if ageing:
		ageing[0]["ageing_based_on"] = doc.ageing_based_on

	return ageing


def get_common_filters(doc):
	return frappe._dict(
		{
			"company": doc.company,
			"finance_book": doc.finance_book if doc.finance_book else None,
			"account": [doc.account] if doc.account else None,
			"cost_center": [cc.cost_center_name for cc in doc.cost_center],
		}
	)


def get_gl_filters(doc, entry, tax_id, presentation_currency):
	return {
		"from_date": doc.from_date,
		"to_date": doc.to_date,
		"party_type": "Customer",
		"party": [entry.customer],
		"party_name": [entry.customer_name] if entry.customer_name else None,
		"presentation_currency": presentation_currency,
		"group_by": doc.group_by,
		"currency": doc.currency,
		"project": [p.project_name for p in doc.project],
		"show_opening_entries": 0,
		"include_default_book_entries": 0,
		"tax_id": tax_id if tax_id else None,
		"show_net_values_in_party_account": doc.show_net_values_in_party_account,
	}


def get_ar_filters(doc, entry):
	return {
		"report_date": doc.posting_date if doc.posting_date else None,
		"party_type": "Customer",
		"party": [entry.customer],
		"customer_name": entry.customer_name if entry.customer_name else None,
		"payment_terms_template": doc.payment_terms_template if doc.payment_terms_template else None,
		"sales_partner": doc.sales_partner if doc.sales_partner else None,
		"sales_person": doc.sales_person if doc.sales_person else None,
		"territory": doc.territory if doc.territory else None,
		"based_on_payment_terms": doc.based_on_payment_terms,
		"report_name": "Accounts Receivable",
		"ageing_based_on": doc.ageing_based_on,
		"range1": 30,
		"range2": 60,
		"range3": 90,
		"range4": 120,
	}


def get_html(doc, filters, entry, col, res, ageing):
	base_template_path = "frappe/www/printview.html"
	template_path = (
		"erpnext/accounts/doctype/process_statement_of_accounts/process_statement_of_accounts.html"
		if doc.report == "General Ledger"
		else "erpnext/accounts/doctype/process_statement_of_accounts/process_statement_of_accounts_accounts_receivable.html"
	)

	if doc.letter_head:
		from frappe.www.printview import get_letter_head

		letter_head = get_letter_head(doc, 0)

	html = frappe.render_template(
		template_path,
		{
			"filters": filters,
			"data": res,
			"report": {"report_name": doc.report, "columns": col},
			"ageing": ageing[0] if (doc.include_ageing and ageing) else None,
			"letter_head": letter_head if doc.letter_head else None,
			"terms_and_conditions": frappe.db.get_value(
				"Terms and Conditions", doc.terms_and_conditions, "terms"
			)
			if doc.terms_and_conditions
			else None,
		},
	)

	html = frappe.render_template(
		base_template_path,
		{"body": html, "css": get_print_style(), "title": "Statement For " + entry.customer},
	)
	return html


def get_customers_based_on_territory_or_customer_group(customer_collection, collection_name):
	fields_dict = {
		"Customer Group": "customer_group",
		"Territory": "territory",
	}
	collection = frappe.get_doc(customer_collection, collection_name)
	selected = [
		customer.name
		for customer in frappe.get_list(
			customer_collection,
			filters=[["lft", ">=", collection.lft], ["rgt", "<=", collection.rgt]],
			fields=["name"],
			order_by="lft asc, rgt desc",
		)
	]
	return frappe.get_list(
		"Customer",
		fields=["name", "customer_name", "email_id"],
		filters=[["disabled", "=", 0], [fields_dict[customer_collection], "IN", selected]],
	)


def get_customers_based_on_sales_person(sales_person):
	lft, rgt = frappe.db.get_value("Sales Person", sales_person, ["lft", "rgt"])
	records = frappe.db.sql(
		"""
		select distinct parent, parenttype
		from `tabSales Team` steam
		where parenttype = 'Customer'
			and exists(select name from `tabSales Person` where lft >= %s and rgt <= %s and name = steam.sales_person)
	""",
		(lft, rgt),
		as_dict=1,
	)
	sales_person_records = frappe._dict()
	for d in records:
		sales_person_records.setdefault(d.parenttype, set()).add(d.parent)
	if sales_person_records.get("Customer"):
		return frappe.get_list(
			"Customer",
			fields=["name", "customer_name", "email_id"],
			filters=[["name", "in", list(sales_person_records["Customer"])]],
		)
	else:
		return []


def get_recipients_and_cc(customer, doc):
	recipients = []
	for clist in doc.customers:
		if clist.customer == customer:
			recipients.append(clist.billing_email)
			if doc.primary_mandatory and clist.primary_email:
				recipients.append(clist.primary_email)
	cc = []
	if doc.cc_to != "":
		try:
			cc = [frappe.get_value("User", doc.cc_to, "email")]
		except Exception:
			pass

	return recipients, cc


def get_context(customer, doc):
	template_doc = copy.deepcopy(doc)
	del template_doc.customers
	template_doc.from_date = format_date(template_doc.from_date)
	template_doc.to_date = format_date(template_doc.to_date)
	return {
		"doc": template_doc,
		"customer": frappe.get_doc("Customer", customer),
		"frappe": frappe.utils,
	}


@frappe.whitelist()
def fetch_customers(customer_collection, collection_name, primary_mandatory):
	customer_list = []
	customers = []

	if customer_collection == "Sales Person":
		customers = get_customers_based_on_sales_person(collection_name)
		if not bool(customers):
			frappe.throw(_("No Customers found with selected options."))
	else:
		if customer_collection == "Sales Partner":
			customers = frappe.get_list(
				"Customer",
				fields=["name", "customer_name", "email_id"],
				filters=[["default_sales_partner", "=", collection_name]],
			)
		else:
			customers = get_customers_based_on_territory_or_customer_group(
				customer_collection, collection_name
			)

	for customer in customers:
		primary_email = customer.get("email_id") or ""
		billing_email = get_customer_emails(customer.name, 1, billing_and_primary=False)

		if int(primary_mandatory):
			if primary_email == "":
				continue

		customer_list.append(
			{
				"name": customer.name,
				"customer_name": customer.customer_name,
				"primary_email": primary_email,
				"billing_email": billing_email,
			}
		)
	return customer_list


@frappe.whitelist()
def get_customer_emails(customer_name, primary_mandatory, billing_and_primary=True):
	"""Returns first email from Contact Email table as a Billing email
	when Is Billing Contact checked
	and Primary email- email with Is Primary checked"""

	billing_email = frappe.db.sql(
		"""
		SELECT
			email.email_id
		FROM
			`tabContact Email` AS email
		JOIN
			`tabDynamic Link` AS link
		ON
			email.parent=link.parent
		JOIN
			`tabContact` AS contact
		ON
			contact.name=link.parent
		WHERE
			link.link_doctype='Customer'
			and link.link_name=%s
			and contact.is_billing_contact=1
			{mcond}
		ORDER BY
			contact.creation desc
		""".format(mcond=get_match_cond("Contact")),
		customer_name,
	)

	if len(billing_email) == 0 or (billing_email[0][0] is None):
		if billing_and_primary:
			frappe.throw(_("No billing email found for customer: {0}").format(customer_name))
		else:
			return ""

	if billing_and_primary:
		primary_email = frappe.get_value("Customer", customer_name, "email_id")
		if primary_email is None and int(primary_mandatory):
			frappe.throw(_("No primary email found for customer: {0}").format(customer_name))
		return [primary_email or "", billing_email[0][0]]
	else:
		return billing_email[0][0] or ""


@frappe.whitelist()
def download_statements(document_name):
	doc = frappe.get_doc("Process Statement Of Accounts", document_name)
	report = get_report_pdf(doc)
	if report:
		frappe.local.response.filename = doc.name + ".pdf"
		frappe.local.response.filecontent = report
		frappe.local.response.type = "download"


@frappe.whitelist()
def send_emails(document_name, from_scheduler=False, posting_date=None):
	doc = frappe.get_doc("Process Statement Of Accounts", document_name)
	report = get_report_pdf(doc, consolidated=False)

	if report:
		for customer, report_pdf in report.items():
			context = get_context(customer, doc)
			filename = frappe.render_template(doc.pdf_name, context)
			attachments = [{"fname": filename + ".pdf", "fcontent": report_pdf}]

			recipients, cc = get_recipients_and_cc(customer, doc)
			if not recipients:
				continue

			subject = frappe.render_template(doc.subject, context)
			message = frappe.render_template(doc.body, context)

			if doc.sender:
				sender_email = frappe.db.get_value("Email Account", doc.sender, "email_id")
			else:
				sender_email = frappe.session.user

			frappe.enqueue(
				queue="short",
				method=frappe.sendmail,
				recipients=recipients,
				sender=sender_email,
				cc=cc,
				subject=subject,
				message=message,
				now=True,
				reference_doctype="Process Statement Of Accounts",
				reference_name=document_name,
				attachments=attachments,
			)

		if doc.enable_auto_email and from_scheduler:
			new_to_date = getdate(posting_date or today())
			if doc.frequency == "Weekly":
				new_to_date = add_days(new_to_date, 7)
			else:
				new_to_date = add_months(new_to_date, 1 if doc.frequency == "Monthly" else 3)
			new_from_date = add_months(new_to_date, -1 * doc.filter_duration)
			doc.add_comment("Comment", "Emails sent on: " + frappe.utils.format_datetime(frappe.utils.now()))
			if doc.report == "General Ledger":
				doc.db_set("to_date", new_to_date, commit=True)
				doc.db_set("from_date", new_from_date, commit=True)
			else:
				doc.db_set("posting_date", new_to_date, commit=True)
		return True
	else:
		return False


@frappe.whitelist()
def send_auto_email():
	selected = frappe.get_list(
		"Process Statement Of Accounts",
		filters={"enable_auto_email": 1},
		or_filters={"to_date": format_date(today()), "posting_date": format_date(today())},
	)
	for entry in selected:
		send_emails(entry.name, from_scheduler=True)
	return True
