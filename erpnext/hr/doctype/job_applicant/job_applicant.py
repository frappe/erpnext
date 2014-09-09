# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.utilities.transaction_base import TransactionBase
from frappe.utils import extract_email_id

class JobApplicant(TransactionBase):

	def get_sender(self, comm):
		return frappe.db.get_value('Jobs Email Settings',None,'email_id') or comm.sender or frappe.session.user

	def validate(self):
		self.set_status()
