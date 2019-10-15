# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import datetime
from frappe.model.document import Document


class AppointmentBookingSettings(Document):
    min_date = '01/01/1970 '
    format_string = "%d/%m/%Y %H:%M:%S"

    def validate(self):
        self.validate_availability_of_slots()

    def validate_availability_of_slots(self):
        for record in self.availability_of_slots:
            from_time = datetime.datetime.strptime(
                self.min_date+record.from_time, self.format_string)
            to_time = datetime.datetime.strptime(
                self.min_date+record.to_time, self.format_string)
            timedelta = to_time-from_time
            self.from_time_is_later_than_to_time(from_time, to_time)
            self.duration_is_divisible(from_time, to_time)

    def from_time_is_later_than_to_time(self, from_time, to_time):
        if from_time > to_time:
            err_msg = 'From Time cannot be later than To Time for '+record.day_of_week
            frappe.throw(_(err_msg))

    def duration_is_divisible(self, from_time, to_time):
        timedelta = to_time - from_time
        if timedelta.total_seconds() % (self.appointment_duration * 60):
            frappe.throw(
                _('The difference between from time and To Time must be a multiple of Appointment'))
