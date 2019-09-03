# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class Timezone(Document):
    def validate(self):
        if self.offset > 720 or self.offset < -720:
            frappe.throw(
                'Timezone offsets must be between -720 and +720 minutes')
