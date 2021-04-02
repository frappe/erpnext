# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Compare(Document):
    def validate(self):
        frappe.msgprint("validate...")
        self.validate_dates()

    def on_submit(self):
        self.update_compare()

    def update_compare(self):
        frappe.db.set_value('Compare', str(self.Compare), {
            'target_start_date': self.target_start_date,
            'target_end_date': self.target_end_date,
            'from_date': self.from_date,
            'end_date': self.end_date
        })


    def validate_dates(self):
        if self.from_date > self.to_date:
           frappe.throw("From Date can not be greater than To Date.")


	

   