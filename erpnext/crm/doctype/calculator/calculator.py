# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Calculator(Document):
    def validate(self):
        frappe.msgprint("validate...")        
        self.calculate()
        
        
    def on_update(self):
        frappe.msgprint("on_update")

    def on_submit(self):
        frappe.msgprint("on_submit")

    def on_cancel(self):
        frappe.msgprint("on_cancel")
    
    def calculate(self):
        if self.operator == "+":
            self.result = self.first_number + self.second_number
        elif self.operator =="-":
             self.result = self.first_number - self.second_number
        elif self.operator =="*":
             self.result=self.first_number * self.second_number
        elif self.operator =="/":
             self.result=self.first_number / self.second_number

 

   