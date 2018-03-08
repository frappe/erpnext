# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Meter(Document):
	pass


@frappe.whitelist(allow_guest=True)
def create_invoice(customer=None,items= None,name=None,meter_recharge_names=None):
    from frappe.utils import cstr, cint, getdate, get_first_day, get_last_day, date_diff, add_days
    from frappe.utils import add_to_date, getdate, get_datetime
    
    # add new sales invoice
    doc = frappe.new_doc("Sales Invoice")
    
    # add name of new saalse invoice
    if name :
        doc.title = customer+" "+name
    else:
        doc.title = customer
    # get date now
    doc.due_date=getdate()
    
    # get time now
    doc.posting_time=get_datetime()
    
    # get name of customer from login 
    doc.customer=customer
    # accounts must be type account recivable with abbr of company
    #  doc.debit_to="Creditors - MT"

    # add child table (items) of sales invoice
    lis = []
    
    import json

    items = json.loads(items)
    doc.set("items",items)

    # save slase invoice and submited
    doc.save(ignore_permissions=True)

    doc.submit()
    
    # add name sales invoice to meter recharge
    meter_recharge_names = json.loads(meter_recharge_names)

    for meter_recharge_name in meter_recharge_names:
        frappe.db.sql(""" UPDATE `tabMETER RECHARGE` SET sales_invoice = '{0}'  WHERE name = '{1}' """.format(str(doc.name),str(meter_recharge_name)))
        frappe.db.commit()


    return doc.name



@frappe.whitelist(allow_guest=True)
def get_all_collector():
    import requests
    r = requests.get("http://202.130.44.124:38080/smart-meter-api/api/collector")
    return  r.json()

@frappe.whitelist(allow_guest=True)
def add_collector(data):
    import requests
    import json

    url = "http://202.130.44.124:38080/smart-meter-api/api/collector"
    #  data={"key": 123456,"logKey": 1234568,"latitude": "sample latitude","longitude": "sample longitude"}

    headers = {'content-type': 'application/json'}

    r = requests.post( url, data =data, headers=headers)
    return  r.json()

@frappe.whitelist(allow_guest=True)
def add_meter(data, name_meter):
    import requests
    import json
    
    url = "http://202.130.44.124:38080/smart-meter-api/api/meter"
    
    headers = {'content-type': 'application/json'}
    
    r = requests.post( url, data =data, headers=headers)
    
    external_meter_id = r.json()['id']
    
    frappe.db.sql(""" UPDATE `tabMeter` SET external_meter_id = '{0}'  WHERE name = '{1}' """.format(external_meter_id,name_meter))
    frappe.db.commit()
    return  r.json()


@frappe.whitelist(allow_guest=True)
def add_meterrecharge(data, meter_recharge_names):
    import requests
    import json
    import ast

    meter_recharge_names = ast.literal_eval(meter_recharge_names)
    url = "http://202.130.44.124:38080/smart-meter-api/api/meterrecharge"
    
    headers = {'content-type': 'application/json'}
    i =0
    meter_recharges = json.loads(data)
    for meter_recharge in meter_recharges:
        meter_recharge=json.dumps(meter_recharge)
        r = requests.post( url, data = meter_recharge, headers=headers)
        external_meterrecharge_id = r.json()['id']
        frappe.db.sql(""" UPDATE `tabMETER RECHARGE` SET external_meter_recharge_id = '{0}'  WHERE name = '{1}' """.format(str(external_meterrecharge_id),str(meter_recharge_names[i])))
        frappe.db.commit()
        i=i+1


    return  r.json()




@frappe.whitelist(allow_guest=True)
def api_add_meterread(data, meter_reads_names):
    import requests
    import json
    import ast
    
    meter_reads_names = ast.literal_eval(meter_reads_names)
    url = "http://202.130.44.124:38080/smart-meter-api/api/meterread"
    
    headers = {'content-type': 'application/json'}
    i =0
    meter_reads = json.loads(data)
    for meter_read in meter_reads:
        meter_read=json.dumps(meter_read)
        r = requests.post( url, data = meter_read, headers=headers)
        external_meter_read_id=r.json()['id']
        frappe.db.sql(""" UPDATE `tabMETER READ` SET external_meter_read_id = '{0}'  WHERE name = '{1}' """.format(str(external_meter_read_id),str(meter_reads_names[i])))
        frappe.db.commit()
        i=i+1

    
    return  r.json()



@frappe.whitelist(allow_guest=True)
def add_customer_meter(meter_id = None, customer = None):
    
    doc=frappe.get_doc("Customer",customer)
    doc.append("customer_meter", {"meter_id": meter_id,})
    doc.save(ignore_permissions=True)

    return  doc




