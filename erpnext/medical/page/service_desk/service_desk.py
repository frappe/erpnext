# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from collections import OrderedDict

@frappe.whitelist()
def get_patient_services_info(company, patient, from_date, to_date, physician=None):
    if not company:
        frappe.throw("Please select company")
    if not patient:
        frappe.throw("Please select patient")
    payload = {}
    drugs = OrderedDict()
    procedures = []
    labtests = []

    conditions = ("company='{0}' and patient='{1}'").format(company, patient)
    if physician:
        conditions += ("and physician='{0}'").format(physician)
    consultations = frappe.db.sql(_("""select name from tabConsultation where {0}
    and docstatus<2 and consultation_date between '{1}' and '{2}' order by consultation_date desc""").format(
    conditions, from_date, to_date), as_dict=1)
    for consultation in consultations:
        c_obj = frappe.get_doc("Consultation", consultation.name)
        key = consultation.name
        if(c_obj.drug_prescription):
            for drug in c_obj.drug_prescription:
                if drugs.has_key(key):
                    drugs[key].append([drug.drug_name, drug.dosage, drug.period, drug.name])
                else:
                    drugs[key] = [[drug.drug_name, drug.dosage, drug.period, drug.name]]
        if(c_obj.procedure_prescription):
            procedure_dict = get_details_by_line("Procedure Appointment", c_obj.name, c_obj.physician, c_obj.procedure_prescription)
            if procedure_dict:
                procedures.extend(procedure_dict)
        if(c_obj.test_prescription):
            test_dict = get_details_by_line("Lab Test", c_obj.name, c_obj.physician, c_obj.test_prescription)
            if test_dict:
                labtests.extend(test_dict)

    appointments = get_appointments(conditions, from_date, to_date)
    if appointments:
        payload["appointments"] = appointments
    if drugs:
        payload["drugs"] = drugs
    if procedures:
        payload["procedures"] = procedures
    if labtests:
        payload["labtests"] = labtests

    return payload

def get_appointments(conditions, from_date, to_date):
    data = []
    appointments = frappe.db.sql(_("""select name, physician, start_dt,  status, invoice from tabAppointment where {0} and appointment_date between '{1}' and '{2}' order by start_dt desc""").format(conditions, from_date, to_date), as_dict=1)
    for item in appointments:
        status = False
        invoice = False
        if item.invoice:
            invoice = item.invoice
            status = frappe.get_value("Sales Invoice", item.invoice, "status")
        data.append([item.name, item.physician, item.start_dt, item.status, item.invoice, status])
    return data

def get_details_by_line(dt, consultation, physician, lines):
    key = consultation
    data = []
    for line in lines:
        doc = False
        docstatus = False
        invoice = False
        status = False
        if line.invoice:
            invoice = line.invoice
            status = frappe.get_value("Sales Invoice", invoice, "status")
        docs = frappe.db.exists({ "doctype": dt, "prescription": line.name})
        if docs:
            doc = docs[0][0]
            docstatus = frappe.get_value(dt, doc, "status")
        if (dt == "Lab Test"):
            data.append([line.test_code, doc, docstatus, invoice, status, line.name, consultation, physician])
        else:
            data.append([line.procedure_template, doc, docstatus, invoice, status, line.name, consultation, physician])

    if data:
        return data
    return False
