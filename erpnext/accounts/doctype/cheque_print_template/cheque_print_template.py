# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document


class ChequePrintTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		acc_no_dist_from_left_edge: DF.Float
		acc_no_dist_from_top_edge: DF.Float
		acc_pay_dist_from_left_edge: DF.Float
		acc_pay_dist_from_top_edge: DF.Float
		amt_in_figures_from_left_edge: DF.Float
		amt_in_figures_from_top_edge: DF.Float
		amt_in_word_width: DF.Float
		amt_in_words_from_left_edge: DF.Float
		amt_in_words_from_top_edge: DF.Float
		amt_in_words_line_spacing: DF.Float
		bank_name: DF.Data
		cheque_height: DF.Float
		cheque_size: DF.Literal["", "Regular", "A4"]
		cheque_width: DF.Float
		date_dist_from_left_edge: DF.Float
		date_dist_from_top_edge: DF.Float
		has_print_format: DF.Check
		is_account_payable: DF.Check
		message_to_show: DF.Data | None
		payer_name_from_left_edge: DF.Float
		payer_name_from_top_edge: DF.Float
		scanned_cheque: DF.Attach | None
		signatory_from_left_edge: DF.Float
		signatory_from_top_edge: DF.Float
		starting_position_from_top_edge: DF.Float
	# end: auto-generated types

	pass


@frappe.whitelist()
def create_or_update_cheque_print_format(template_name):
	frappe.only_for("System Manager")

	if not frappe.db.exists("Print Format", template_name):
		cheque_print = frappe.new_doc("Print Format")
		cheque_print.update(
			{
				"doc_type": "Payment Entry",
				"standard": "No",
				"custom_format": 1,
				"print_format_type": "Jinja",
				"name": template_name,
			}
		)
	else:
		cheque_print = frappe.get_doc("Print Format", template_name)

	doc = frappe.get_doc("Cheque Print Template", template_name)

	account_payee = ""
	if doc.is_account_payable:
		account_payee = """
		<span style="top:{acc_pay_dist_from_top_edge}cm; left:{acc_pay_dist_from_left_edge}cm;
			border-bottom: solid 1px;border-top:solid 1px; width:2cm;text-align: center; position: absolute;">
				{{{{ {message_to_show} | e }}}}
		</span>""".format(
			acc_pay_dist_from_top_edge=doc.acc_pay_dist_from_top_edge,
			acc_pay_dist_from_left_edge=doc.acc_pay_dist_from_left_edge,
			message_to_show=frappe.as_json(doc.message_to_show or _("Account Pay Only"), ensure_ascii=False),
		)

	cheque_print.html = """
<style>
	.print-format {{
		padding: 0px;
	}}
	@media screen {{
		.print-format {{
			padding: 0in;
		}}
	}}
</style>
<div style="position: relative; top:{starting_position_from_top_edge}cm">
	<div style="width:{cheque_width}cm;height:{cheque_height}cm;">
		{account_payee}
		<span style="top:{date_dist_from_top_edge}cm; left:{date_dist_from_left_edge}cm;
			position: absolute;">
			{{{{ frappe.utils.formatdate(doc.reference_date) or '' }}}}
		</span>
		<span style="top:{acc_no_dist_from_top_edge}cm;left:{acc_no_dist_from_left_edge}cm;
			position: absolute;  min-width: 6cm;">
			{{{{ (doc.bank_account_no or '') | e }}}}
		</span>
		<span style="top:{payer_name_from_top_edge}cm;left: {payer_name_from_left_edge}cm;
			position: absolute;  min-width: 6cm;">
			{{{{doc.party_name}}}}
		</span>
		<span style="top:{amt_in_words_from_top_edge}cm; left:{amt_in_words_from_left_edge}cm;
			position: absolute; display: block; width: {amt_in_word_width}cm;
			line-height:{amt_in_words_line_spacing}cm; word-wrap: break-word;">
				{{{{frappe.utils.money_in_words(doc.base_paid_amount or doc.base_received_amount, doc.company_currency)}}}}
		</span>
		<span style="top:{amt_in_figures_from_top_edge}cm;left: {amt_in_figures_from_left_edge}cm;
			position: absolute; min-width: 4cm;">
			{{{{doc.get_formatted("base_paid_amount") or doc.get_formatted("base_received_amount")}}}}
		</span>
		<span style="top:{signatory_from_top_edge}cm;left: {signatory_from_left_edge}cm;
			position: absolute;  min-width: 6cm;">
			{{{{doc.company}}}}
		</span>
	</div>
</div>""".format(
		starting_position_from_top_edge=doc.starting_position_from_top_edge
		if doc.cheque_size == "A4"
		else 0.0,
		cheque_width=doc.cheque_width,
		cheque_height=doc.cheque_height,
		account_payee=account_payee,
		date_dist_from_top_edge=doc.date_dist_from_top_edge,
		date_dist_from_left_edge=doc.date_dist_from_left_edge,
		acc_no_dist_from_top_edge=doc.acc_no_dist_from_top_edge,
		acc_no_dist_from_left_edge=doc.acc_no_dist_from_left_edge,
		payer_name_from_top_edge=doc.payer_name_from_top_edge,
		payer_name_from_left_edge=doc.payer_name_from_left_edge,
		amt_in_words_from_top_edge=doc.amt_in_words_from_top_edge,
		amt_in_words_from_left_edge=doc.amt_in_words_from_left_edge,
		amt_in_word_width=doc.amt_in_word_width,
		amt_in_words_line_spacing=doc.amt_in_words_line_spacing,
		amt_in_figures_from_top_edge=doc.amt_in_figures_from_top_edge,
		amt_in_figures_from_left_edge=doc.amt_in_figures_from_left_edge,
		signatory_from_top_edge=doc.signatory_from_top_edge,
		signatory_from_left_edge=doc.signatory_from_left_edge,
	)

	cheque_print.save(ignore_permissions=True)

	frappe.db.set_value("Cheque Print Template", template_name, "has_print_format", 1)

	return cheque_print


def update_existing_cheque_print_formats():
	frappe.only_for("System Manager")

	template_names = frappe.get_all("Cheque Print Template", pluck="name")
	if not template_names:
		return

	default_messages = None
	for template_name in frappe.get_all(
		"Print Format",
		filters={
			"name": ["in", template_names],
			"doc_type": "Payment Entry",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"raw_printing": 0,
		},
		pluck="name",
	):
		print_format = frappe.get_doc("Print Format", template_name)
		# Only migrate a region that still matches the saved message, preserving custom markup.
		message = re.search(
			r'border-bottom: solid 1px;border-top:solid 1px; width:2cm;text-align: center; position: absolute;">\n\t{4}'
			r"(?P<message>.*)"
			r"\n\t{2}</span>\n\t{2}<span[^>]*>\n\t{3}{{ frappe\.utils\.formatdate\(doc\.reference_date\) or '' }}",
			print_format.html or "",
			flags=re.DOTALL,
		)
		saved_message = frappe.db.get_value("Cheque Print Template", template_name, "message_to_show")
		if not saved_message and default_messages is None:
			default_messages = {"Account Pay Only"}
			default_messages.update(
				_("Account Pay Only", lang=language) for language in frappe.get_all("Language", pluck="name")
			)

		for message_text in [saved_message] if saved_message else default_messages:
			escaped_message = "{{ " + frappe.as_json(message_text, ensure_ascii=False) + " | e }}"
			if message and message["message"] in (message_text, escaped_message):
				break
		else:
			frappe.log_error(
				title=_("Cheque Print Format Requires Review"),
				message=_(
					"The account-payee message in Print Format {0} could not be identified unambiguously. "
					"Its HTML has been preserved. "
					"Review and escape the message in its custom HTML, or regenerate the format "
					"using Update Print Format."
				).format(print_format.name),
				reference_doctype="Print Format",
				reference_name=print_format.name,
			)
			continue

		if message["message"] == escaped_message:
			continue

		print_format.html = (
			print_format.html[: message.start("message")]
			+ escaped_message
			+ print_format.html[message.end("message") :]
		)
		print_format.save()
