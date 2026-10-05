# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe.model.document import Document
from frappe.utils.jinja import guess_is_path, validate_template


class ContractTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.crm.doctype.contract_template_fulfilment_terms.contract_template_fulfilment_terms import (
			ContractTemplateFulfilmentTerms,
		)

		contract_terms: DF.TextEditor | None
		fulfilment_terms: DF.Table[ContractTemplateFulfilmentTerms]
		requires_fulfilment: DF.Check
		title: DF.Data | None
	# end: auto-generated types

	def validate(self):
		if self.contract_terms:
			validate_template(self.contract_terms, restrict_globals=True)


@frappe.whitelist()
def get_contract_template(template_name: str, doc: str | dict | Document):
	doc = frappe.parse_json(doc)

	contract_template = frappe.get_doc("Contract Template", template_name)
	contract_template.check_permission()
	contract_terms = None

	if contract_template.contract_terms:
		contract_terms = render_contract_terms(contract_template.contract_terms, doc)

	return {"contract_template": contract_template, "contract_terms": contract_terms}


def render_contract_terms(terms: str, context: dict) -> str:
	# render_template loads a single line ending in a file extension as a template path;
	# a trailing newline keeps it content and Jinja drops that newline from the output
	if guess_is_path(terms):
		terms += "\n"
	return frappe.render_template(terms, context, restrict_globals=True)
