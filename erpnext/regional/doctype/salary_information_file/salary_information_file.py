# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import get_link_to_form

class SalaryInformationFile(Document):
	def validate(self):
		if not self.employer_establishment_id:
			frappe.throw(_("Enter {0} in Company: {1}").format(
				bold("Employer Establishment ID"),
				bold(get_link_to_form("Company", self.company))
			))

def get_company_bank_details(company):
	return frappe.get_all("Bank Account", filters={"is_company_account": 1, "company": company},
		fields = ["bank", "iban", "bank_account_no"])
