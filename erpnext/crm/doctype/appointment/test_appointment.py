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


class TestAppointment(unittest.TestCase):
    def setUp(self):
        settings = frappe.get_doc('Appointment Booking Settings')
        create_appointments(settings.number_of_agents)
        frappe.get_doc({
            'doctype': 'Appointment',
            'scheduled_time': datetime.datetime.min,
            'customer_name': 'Extra Customer',
            'customer_phone_number': '8088',
            'customer_skype': 'extra_customer',
        })

    def tearDown(self):
        delete_appointments()

    def delete_appointments(self):
        doc_list = frappe.get_list('Appointment',filters={'scheduled_time':datetime.datetime.min,'customer_phone_number':'8088'})
        for doc in doc_list:
            doc.delete()

    def test_number_of_appointments(self):
        settings = frappe.get_doc('Appointment Booking Settings')
        self.assertFalse(frappe.db.exists('Apoointment',
                                            filters={'scheduled_time': datetime.datetime.min, 'customer_name':'Extra Customer'}),
                             settings.number_of_agents,
                             "Number of appointments exceed number of agents")
