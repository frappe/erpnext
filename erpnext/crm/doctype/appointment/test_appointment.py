# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import datetime


def create_appointments(number):
    for i in range(1, number):
        frappe.get_doc({
            'doctype': 'Appointment',
            'scheduled_time': datetime.datetime.min,
            'customer_name': 'Test Customer'+str(i),
            'customer_phone_number': '8088',
            'customer_skype': 'test'+str(i),
        })

def delete_appointments():
        doc_list = frappe.get_list('Appointment',filters={'scheduled_time':datetime.datetime.min,'customer_phone_number':'8088'})
        for doc in doc_list:
            doc.delete()


class TestAppointment(unittest.TestCase):
    pass
