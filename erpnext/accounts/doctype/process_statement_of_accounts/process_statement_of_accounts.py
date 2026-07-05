# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import copy

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, format_date, getdate, now_datetime, today
from frappe.utils.background_jobs import is_job_enqueued
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
from erpnext.utilities.query import get_match_conditions_qb


class ProcessStatementOfAccounts(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.process_statement_of_accounts_cc.process_statement_of_accounts_cc import (
			ProcessStatementOfAccountsCC,
		)
		from erpnext.accounts.doctype.process_statement_of_accounts_customer.process_statement_of_accounts_customer import (
			ProcessStatementOfAccountsCustomer,
		)
		from erpnext.accounts.doctype.psoa_cost_center.psoa_cost_center import PSOACostCenter
		from erpnext.accounts.doctype.psoa_project.psoa_project import PSOAProject

		account: DF.Link | None
		ageing_based_on: DF.Literal["Due Date", "Posting Date"]
		based_on_payment_terms: DF.Check
		body: DF.TextEditor | None
		categorize_by: DF.Literal["", "Categorize by Voucher", "Categorize by Voucher (Consolidated)"]
		cc_to: DF.TableMultiSelect[ProcessStatementOfAccountsCC]
		collection_name: DF.DynamicLink | None
		company: DF.Link
		cost_center: DF.TableMultiSelect[PSOACostCenter]
		currency: DF.Link | None
		customer_collection: DF.Literal["", "Customer Group", "Territory", "Sales Partner", "Sales Person"]
		customers: DF.Table[ProcessStatementOfAccountsCustomer]
		enable_auto_email: DF.Check
		filter_duration: DF.Int
		finance_book: DF.Link | None
		frequency: DF.Literal["Daily", "Weekly", "Biweekly", "Monthly", "Quarterly"]
		from_date: DF.Date | None
		ignore_cr_dr_notes: DF.Check
		ignore_exchange_rate_revaluation_journals: DF.Check
		include_ageing: DF.Check
		include_break: DF.Check
		letter_head: DF.Link | None
		orientation: DF.Literal["Landscape", "Portrait"]
		payment_terms_template: DF.Link | None
		pdf_name: DF.Data | None
		posting_date: DF.Date | None
		primary_mandatory: DF.Check
		print_format: DF.Link | None
		project: DF.TableMultiSelect[PSOAProject]
		report: DF.Literal["General Ledger", "Accounts Receivable"]
		sales_partner: DF.Link | None
		sales_person: DF.Link | None
		sender: DF.Link | None
		show_future_payments: DF.Check
		show_net_values_in_party_account: DF.Check
		show_opening_entries: DF.Check
		show_remarks: DF.Check
		start_date: DF.Date | None
		statement_attachment: DF.Attach | None
		subject: DF.Data | None
		terms_and_conditions: DF.Link | None
		territory: DF.Link | None
		to_date: DF.Date | None
	# end: auto-generated types

	def validate(self):
		self.validate_account()
		self.validate_company_for_table("Cost Center")
		self.validate_company_for_table("Project")

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
		validate_template(self.pdf_name)

		if not self.customers:
			frappe.throw(_("Customers not selected."))

		if self.enable_auto_email:
			if self.start_date and getdate(self.start_date) >= getdate(today()):
				self.to_date = self.start_date
				self.from_date = add_months(self.to_date, -1 * self.filter_duration)

		if self.print_format:
			pf = frappe.db.get_value(
				"Print Format",
				self.print_format,
				["print_format_type", "print_format_for", "report", "disabled"],
				as_dict=True,
			)
			if not pf:
				frappe.throw(title=_("Invalid Print Format"), msg=_("Selected Print Format does not exist."))
			if pf.print_format_type != "Jinja":
				frappe.throw(title=_("Invalid Print Format"), msg=_("Print Format Type should be Jinja."))
			if pf.print_format_for != "Report" or pf.report != self.report or pf.disabled:
				frappe.throw(
					title=_("Invalid Print Format"),
					msg=_(
						"Print Format must be an enabled Report Print Format matching the selected Report."
					),
				)

	def validate_account(self):
		if not self.account:
			return

		if self.company != frappe.get_cached_value("Account", self.account, "company"):
			frappe.throw(
				_("Account {0} doesn't belong to Company {1}").format(
					frappe.bold(self.account),
					frappe.bold(self.company),
				)
			)

	def validate_company_for_table(self, doctype):
		field = frappe.scrub(doctype)
		if not self.get(field):
			return

		fieldname = field + "_name"

		values = set(d.get(fieldname) for d in self.get(field))
		invalid_values = frappe.db.get_all(
			doctype, filters={"name": ["in", values], "company": ["!=", self.company]}, pluck="name"
		)

		if invalid_values:
			msg = _("<p>Following {0}s do not belong to Company {1}:</p>").format(
				doctype, frappe.bold(self.company)
			)

			msg += (
				"<ul>"
				+ "".join(_("<li>{0}</li>").format(frappe.bold(row)) for row in invalid_values)
				+ "</ul>"
			)

			frappe.throw(msg)


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
			doc.currency
			or get_party_account_currency("Customer", entry.customer, doc.company)
			or get_company_currency(doc.company)
		)

		filters = get_common_filters(doc)
		if doc.ignore_exchange_rate_revaluation_journals:
			filters.update({"ignore_err": True})

		if doc.ignore_cr_dr_notes:
			filters.update({"ignore_cr_dr_notes": True})

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
			"show_remarks": doc.show_remarks,
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
		"categorize_by": doc.categorize_by,
		"currency": doc.currency,
		"project": [p.project_name for p in doc.project],
		"show_opening_entries": doc.show_opening_entries,
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
		"show_future_payments": doc.show_future_payments,
		"report_name": "Accounts Receivable",
		"ageing_based_on": doc.ageing_based_on,
		"range1": 30,
		"range2": 60,
		"range3": 90,
		"range4": 120,
	}


def get_html(doc, filters, entry, col, res, ageing):
	base_template_path = "frappe/www/printview.html"
	template_path = "erpnext/accounts/doctype/process_statement_of_accounts/process_statement_of_accounts_accounts_receivable.html"
	if doc.report == "General Ledger":
		template_path = (
			"erpnext/accounts/doctype/process_statement_of_accounts/process_statement_of_accounts.html"
		)

	process_soa_html = frappe.get_hooks("process_soa_html")
	# fetching custom print format for Process Statement of Accounts
	if process_soa_html and process_soa_html.get(doc.report):
		template_path = process_soa_html[doc.report][-1]

	if doc.print_format:
		custom_html, custom_css = frappe.db.get_value("Print Format", doc.print_format, ["html", "css"])
		template_path = f"<style>{custom_css}</style> {custom_html}"

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
	steam = frappe.qb.DocType("Sales Team")
	sp = frappe.qb.DocType("Sales Person")
	records = (
		frappe.qb.from_(steam)
		.select(steam.parent, steam.parenttype)
		.distinct()
		.where(
			(steam.parenttype == "Customer")
			& steam.sales_person.isin(
				frappe.qb.from_(sp).select(sp.name).where((sp.lft >= lft) & (sp.rgt <= rgt))
			)
		)
		.run(as_dict=1)
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
			if clist.billing_email:
				for email in clist.billing_email.split(","):
					recipients.append(email.strip())
			if doc.primary_mandatory and clist.primary_email:
				for email in clist.primary_email.split(","):
					recipients.append(email.strip())
	cc = []
	if doc.cc_to != "":
		try:
			cc = [frappe.get_value("User", user.cc, "email") for user in doc.cc_to]
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
def fetch_customers(customer_collection: str, collection_name: str, primary_mandatory: str | int):
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
def get_customer_emails(customer_name: str, primary_mandatory: str | int, billing_and_primary: bool = True):
	"""Returns first email from Contact Email table as a Billing email
	when Is Billing Contact checked
	and Primary email- email with Is Primary checked"""

	frappe.has_permission("Customer", "read", customer_name, throw=True)

	email = frappe.qb.DocType("Contact Email")
	link = frappe.qb.DocType("Dynamic Link")
	contact = frappe.qb.DocType("Contact")

	query = (
		frappe.qb.from_(email)
		.join(link)
		.on(email.parent == link.parent)
		.join(contact)
		.on(contact.name == link.parent)
		.select(email.email_id)
		.where(
			(link.link_doctype == "Customer")
			& (link.link_name == customer_name)
			& (contact.is_billing_contact == 1)
		)
		.orderby(contact.creation, order=frappe.qb.desc)
	)

	for condition in get_match_conditions_qb("Contact", table=contact):
		query = query.where(condition)

	billing_email = query.run()

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
def download_statements(document_name: str):
	doc = frappe.get_doc("Process Statement Of Accounts", document_name)
	doc.check_permission("read")
	report = get_report_pdf(doc)
	if report:
		frappe.local.response.filename = doc.name + ".pdf"
		frappe.local.response.filecontent = report
		frappe.local.response.type = "download"


@frappe.whitelist()
def queue_statement_download(document_name: str):
	doc = frappe.get_doc("Process Statement Of Accounts", document_name)
	doc.check_permission("read")

	job_id = f"download_statement_of_accounts_{document_name}"
	if is_job_enqueued(job_id):
		return _("A statement generation job is already queued for this document.")

	frappe.enqueue(
		generate_statement_download,
		queue="long",
		document_name=document_name,
		user=frappe.session.user,
		enqueue_after_commit=True,
		job_id=job_id,
		deduplicate=True,
	)

	return _(
		"Statement generation has been queued. You'll be notified when it's ready, and the PDF will be available in the Statement Attachment field."
	)


def generate_statement_download(document_name: str, user: str | None = None):
	doc = frappe.get_doc("Process Statement Of Accounts", document_name)
	report = get_report_pdf(doc)
	if not report:
		if user:
			_notify_user(
				user,
				doc,
				subject=_("Statement generation failed. Please try again or contact support."),
			)
		return

	if doc.statement_attachment:
		old_file = frappe.db.get_value(
			"File",
			{
				"file_url": doc.statement_attachment,
				"attached_to_doctype": doc.doctype,
				"attached_to_name": doc.name,
			},
			"name",
		)

		if old_file:
			frappe.delete_doc("File", old_file, ignore_permissions=True, delete_permanently=True, force=True)

	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": get_pdf_filename(doc.name),
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"content": report,
			"is_private": 1,
		}
	).insert(ignore_permissions=True)

	doc.db_set("statement_attachment", file.file_url)

	if user:
		_notify_user(
			user,
			doc,
			subject=_("Statement of Accounts PDF is ready. Check the Statement Attachment field."),
			link=doc.get_url(),
		)


def _notify_user(user: str, doc, subject: str, email_content: str | None = None, link: str | None = None):
	notification = {
		"doctype": "Notification Log",
		"subject": subject,
		"for_user": user,
		"type": "Alert",
		"document_type": doc.doctype,
		"document_name": doc.name,
	}
	if email_content:
		notification["email_content"] = email_content
	if link:
		notification["link"] = link

	frappe.get_doc(notification).insert(ignore_permissions=True)


def get_send_emails_job_id(document_name: str) -> str:
	return f"send_statement_of_accounts_emails_{document_name}"


@frappe.whitelist()
def queue_send_emails(document_name: str):
	doc = frappe.get_doc("Process Statement Of Accounts", document_name)
	doc.check_permission()

	job_id = get_send_emails_job_id(document_name)
	if is_job_enqueued(job_id):
		return _("An email generation job is already queued or running for this document.")

	psoa_customer_threshold = frappe.db.get_single_value("Accounts Settings", "psoa_customer_threshold")
	queue = "short" if len(doc.customers) <= psoa_customer_threshold else "long"

	frappe.enqueue(
		send_emails,
		queue=queue,
		document_name=document_name,
		user=frappe.session.user,
		enqueue_after_commit=True,
		job_id=job_id,
		deduplicate=True,
	)

	return _("Email generation has been queued and will be processed in the background.")


def send_emails(
	document_name: str,
	from_scheduler: bool = False,
	posting_date: str | None = None,
	user: str | None = None,
):
	doc = frappe.get_doc("Process Statement Of Accounts", document_name)
	doc.check_permission()

	# In scheduler context there is no interactive session user to notify.
	# Fall back to the document owner so failures are actually seen by someone
	# responsible for this PSOA setup.
	notify_user = user if (user and not from_scheduler) else (doc.owner or user)

	try:
		report = get_report_pdf(doc, consolidated=False)
	except Exception:
		frappe.log_error(
			title=f"Failed to generate statement PDFs for {document_name}",
			message=frappe.get_traceback(),
		)
		if notify_user:
			_notify_user(
				notify_user,
				doc,
				subject=_(
					"Statement of Accounts email generation failed. Please try again or contact support."
				),
			)
		return False

	if not report:
		return False

	failed_customers = []
	skipped_customers = []

	for customer, report_pdf in report.items():
		context = get_context(customer, doc)
		filename = frappe.render_template(  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
			doc.pdf_name, context
		)
		recipients, cc = get_recipients_and_cc(customer, doc)
		if not recipients:
			# No recipient configured — this customer was NOT sent a statement,
			# so the cycle is not actually complete for them.
			skipped_customers.append(customer)
			continue

		sender_email = (
			frappe.db.get_value("Email Account", doc.sender, "email_id")
			if doc.sender
			else frappe.session.user
		)
		try:
			frappe.sendmail(
				recipients=recipients,
				sender=sender_email,
				cc=cc,
				subject=frappe.render_template(  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
					doc.subject, context
				),
				message=frappe.render_template(  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
					doc.body, context
				),
				now=True,
				reference_doctype="Process Statement Of Accounts",
				reference_name=document_name,
				attachments=[{"fname": filename + ".pdf", "fcontent": report_pdf}],
				expose_recipients="header",
			)
		except Exception:
			frappe.log_error(
				title=f"Failed to send statement email to {customer} for {document_name}",
				message=frappe.get_traceback(),
			)
			failed_customers.append(customer)
			continue

	all_incomplete = failed_customers + skipped_customers

	if all_incomplete and notify_user:
		_notify_user(
			notify_user,
			doc,
			subject=_(
				"Statement emails were not sent to {0} customer(s). Check the error log for details."
			).format(len(all_incomplete)),
		)

	# Only roll the schedule forward once every intended customer has actually
	# received their statement — otherwise skipped/failed customers get silently
	# dropped from the next cycle instead of being retried.
	if doc.enable_auto_email and from_scheduler and not all_incomplete:
		new_to_date = getdate(posting_date or today())
		if doc.frequency in ("Daily", "Weekly", "Biweekly"):
			frequency = {"Daily": 1, "Weekly": 7, "Biweekly": 14}
			new_to_date = add_days(new_to_date, frequency[doc.frequency])
		else:
			new_to_date = add_months(new_to_date, 1 if doc.frequency == "Monthly" else 3)
		new_from_date = add_months(new_to_date, -1 * doc.filter_duration)
		doc.add_comment("Comment", "Emails sent on: " + frappe.utils.format_datetime(frappe.utils.now()))
		if doc.report == "General Ledger":
			frappe.db.set_value(doc.doctype, doc.name, "to_date", new_to_date)
			frappe.db.set_value(doc.doctype, doc.name, "from_date", new_from_date)
		else:
			frappe.db.set_value(doc.doctype, doc.name, "posting_date", new_to_date)

	return not all_incomplete


def get_pdf_filename(psoa_name):
	timestamp = now_datetime().strftime("%Y%m%d_%H%M%S")
	return f"Statement_of_Accounts_{psoa_name}_{timestamp}.pdf"


@frappe.whitelist()
def send_auto_email():
	frappe.has_permission("Process Statement Of Accounts", throw=True)
	selected = frappe.get_list(
		"Process Statement Of Accounts",
		filters={"enable_auto_email": 1},
		or_filters={"to_date": today(), "posting_date": today()},
	)
	for entry in selected:
		job_id = get_send_emails_job_id(entry.name)
		if is_job_enqueued(job_id):
			continue

		frappe.enqueue(
			send_emails,
			queue="long",
			document_name=entry.name,
			user=None,  # send_emails resolves this to the doc owner for scheduler runs
			from_scheduler=True,
			posting_date=today(),
			enqueue_after_commit=True,
			job_id=job_id,
			deduplicate=True,
		)
	return True
