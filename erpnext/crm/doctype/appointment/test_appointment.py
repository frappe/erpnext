# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import datetime

def create_test_lead():
    if frappe.db.exists({'doctype:''Lead','lead_name':'Test Lead'}):
        return
    test_lead = frappe.get_doc({
        'doctype':'Lead',
        'lead_name':'Test Lead',
        'email_id':'test@example.com'
    })
    test_lead.insert(ignore_permissions=True)
    return test_lead

def create_test_appointments():
    if frappe.db.exists({
        'doctype':'Appointment',
        'email':'test@example.com'
        }):
        return
    test_appointment = frappe.get_doc({
        'doctype':'Appointment',
        'email':'test@example.com',
        'status':'Open',
        'customer_name':'Test Lead',
        'customer_phone_number':'666',
        'customer_skype':'test',
        'customer_email':'test@example.com',
        'scheduled_time':datetime.datetime.now()
    })
    test_appointment.insert()
    return test_appointment

class TestAppointment(unittest.TestCase):
    test_appointment = test_lead = None
    def setUp(self):
        test_lead = create_test_lead()
        test_appointment = test_create_test_appointments()

    def tearDown(self):
        pass

    def test_calendar_event_created(self):
        cal_event = frappe.get_doc('Event',test_appointment.calendar_event)
        self.assertEqual(cal_event.starts_on ,test_appointment.scheduled_time)

    def test_lead_linked(self):
        lead = frappe.get_doc('Lead',self.lead)
        self.assertIsNotNone(lead)