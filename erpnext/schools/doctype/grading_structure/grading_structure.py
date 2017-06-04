# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr

class GradingStructure(Document):
    def validate(self):
        grade_intervals = self.get("grade_intervals")
        check_overlap(grade_intervals, self)

#Check if any of the grade intervals for this grading structure overlap
def check_overlap(grade_intervals, parent_doc):
    for interval1 in grade_intervals:
        for interval2 in grade_intervals:
            if interval1.name == interval2.name:
                pass
            else:
                if (interval1.from_score <= interval2.from_score and interval1.to_score >= interval2.from_score) or (interval1.from_score <= interval2.to_score and interval1.to_score >= interval2.to_score):
                    frappe.throw(_("""The intervals for Grade Code {0} overlaps with the grade intervals for other grades. 
                    Please check intervals {0} and {1} and try again""".format(interval1.grade_code, interval2.grade_code))) 