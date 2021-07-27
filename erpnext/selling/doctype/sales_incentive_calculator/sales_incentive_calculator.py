# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from datetime import date
import json
import frappe
from frappe.model.document import Document

class SalesIncentiveCalculator(Document):
  def before_save(self):
    for i in self.invoice_list:
      if i.discount:
        d=i.amount * i.discount/100
        i.amount=d
        f=i.rate * i.discount/100
        i.rate=f
  def on_submit(self):
    lst=frappe.db.sql("""select distinct customer from `tabSales Incentive Calculator Invoice`""",as_dict=1)
    for i in lst:
      doc=frappe.new_doc("Sales Invoice")
      doc.customer=i.customer
      doc.is_return=1
      doc.due_date=date.today()
      for j in self.invoice_list:
        doc.append("items",{
                "item_code":j.item,
                "qty":-j.qty,
                "rate":j.rate,
                "amount":-j.amount
              })
    doc.save(ignore_permissions=True)

@frappe.whitelist()
def get_list():
  list=[]
  lst=[]
  doc=frappe.db.get_all("Customer Sales Incentives",{"docstatus":1},['name'])
  db=frappe.db.get_all("Sales Incentive Calculator",{"docstatus":1},['customer_sales_incentive'])
  for i in db:
    if i.customer_sales_incentive:
      lst.append(i.customer_sales_incentive)
  for i in doc:
    if i.name not in lst:
      list.append(i.name)
  return list

    
@frappe.whitelist()
def fetch_details(customer_sales_incentive):
    a=""
    doc=frappe.get_doc("Customer Sales Incentives",customer_sales_incentive)
    data  = json.loads(doc.filters_json)
    for i in data:
      print(i)
      if i[0]=="Sales Invoice":
        if isinstance(i[3], str):
          filter=str(i[1])+str(i[2])+'"'+str(i[3])+'"'
          a+=" and si." +filter
        if isinstance(i[3], int):
          filter=str(i[1])+str(i[2])+str(i[3])
          a+=" and si."+filter
        if isinstance(i[3], list):
          a+="and si."+str(i[1])+" >= "+'"'+str(i[3][0])+'"'+" and "+"si."+str(i[1])+" <= "+'"'+str(i[3][1])+'"'
      if i[0]=="Sales Invoice Item":
        if isinstance(i[3], str):
          filter=str(i[1])+str(i[2])+'"'+str(i[3])+'"'
          a+=" and sii." +filter
        if isinstance(i[3], int):
          filter=str(i[1])+str(i[2])+str(i[3])
          a+=" and sii."+filter
        if isinstance(i[3], list):
          a+="and sii."+str(i[1])+" >= "+'"'+str(i[3][0])+'"'+" and "+"si."+str(i[1])+" <= "+'"'+str(i[3][1])+'"'
    
    
     
    if doc.scheme_applicable=="Customer Group":
      h=[]
      for i in doc.customer_group:
        if i.idx ==1:
          v=""
          v+=" and c.customer_group ="+'"'+str(i.customer_group)+'"'
        elif i.idx > 1:
          h.append(i.customer_group)
          v=""
          v+=" and c.customer_group in "+ str(h)
      c = frappe.db.sql("""select si.name,si.customer,si.customer_name,si.posting_date,ssi.item_code,ssi.item_name,ssi.qty,ssi.rate,ssi.amount from `tabSales Invoice` si 
                      Inner Join `tabSales Invoice Item` ssi Join `tabCustomer` c where ssi.parent=si.name and c.name=si.customer and si.docstatus=1 {v} {a} """.format(v=v,a=a),as_dict=1)
      return c
    elif doc.scheme_applicable=="Customer":
      h=[]
      for i in doc.customer:
        if i.idx ==1:
          v=""
          v+=" and c.customer ="+'"'+str(i.customer)+'"'
        elif i.idx > 1:
          h.append(i.customer)
          v=""
          v+=" and si.customer in "+ str(h)
      c = frappe.db.sql("""select si.name,si.customer,si.customer_name,si.posting_date,ssi.item_code,ssi.item_name,ssi.rate,ssi.qty,ssi.amount from `tabSales Invoice` si 
                      inner join `tabSales Invoice Item` ssi where ssi.parent=si.name and si.docstatus=1 {v} {a} """.format(v=v,a=a),as_dict=1)
      return c
    else:
      c = frappe.db.sql("""select si.name,si.customer,si.customer_name,si.posting_date,ssi.item_code,ssi.item_name,ssi.rate,ssi.qty,ssi.amount from `tabSales Invoice` si 
                      inner join `tabSales Invoice Item` ssi where ssi.parent=si.name and si.docstatus=1 {a} """.format(a=a),as_dict=1)
      return c


@frappe.whitelist()
def get_payment(customer_sales_incentive):
    a=""
    doc=frappe.get_doc("Customer Sales Incentives",customer_sales_incentive)
    data  = json.loads(doc.filters_json)
    print(data)
    for i in data:
      print(i[1])
      if i[0]=="Sales Invoice":
        if isinstance(i[3], str):
          filter=str(i[1])+str(i[2])+'"'+str(i[3])+'"'
          a+=" and si." +filter
        if isinstance(i[3], int):
          filter=str(i[1])+str(i[2])+str(i[3])
          a+=" and si."+filter
        if isinstance(i[3], list):
          a+="and si."+str(i[1])+" >= "+'"'+str(i[3][0])+'"'+" and "+"si."+str(i[1])+" <= "+'"'+str(i[3][1])+'"'
      if i[0]=="Sales Invoice Item":
        if isinstance(i[3], str):
          filter=str(i[1])+str(i[2])+'"'+str(i[3])+'"'
          a+=" and sii." +filter
        if isinstance(i[3], int):
          filter=str(i[1])+str(i[2])+str(i[3])
          a+=" and sii."+filter
        if isinstance(i[3], list):
          a+="and sii."+str(i[1])+" >= "+'"'+str(i[3][0])+'"'+" and "+"si."+str(i[1])+" <= "+'"'+str(i[3][1])+'"'
    
     
    if doc.scheme_applicable=="Customer Group":
      h=[]
      v=""
      for i in doc.customer_group:
        if i.customer_group:
          if i.idx ==1:
            v+=" and c.customer_group ="+'"'+str(i.customer_group)+'"'
          elif i.idx > 1:
            h.append(i.customer_group)
            v+=" and c.customer_group in "+ str(h)
      c ="""select si.name,si.customer,si.customer_name,si.posting_date,ssi.item_code,ssi.item_name,ssi.rate,ssi.qty,ssi.amount from `tabSales Invoice` si 
                      Inner Join `tabSales Invoice Item` ssi Join `tabCustomer` c where ssi.parent=si.name and c.name=si.customer and si.status="Paid" {v} {a} """
      e=frappe.db.sql(c.format(v=v,a=a),as_dict=1)
      return e
    elif doc.scheme_applicable=="Customer":
      h=[]
      v=""
      for i in doc.customer:
        if i.customer:
          if i.idx ==1:
            v+=" and c.customer ="+'"'+str(i.customer)+'"'
          elif i.idx > 1:
            h.append(i.customer)
            v+=" and si.customer in "+ str(h)
      c = frappe.db.sql("""select si.name,si.customer,si.customer_name,si.posting_date,ssi.item_code,ssi.item_name,ssi.qty,ssi.rate,ssi.amount from `tabSales Invoice` si 
                      Inner Join `tabSales Invoice Item` ssi where ssi.parent=si.name and si.status="Paid" and si.customer='%s' {v}{a} """.format(v=v,a=a),as_dict=1)
      return c
    else:
      c = frappe.db.sql("""select si.name,si.customer,si.customer_name,si.posting_date,ssi.item_code,ssi.item_name,ssi.qty,ssi.amount from `tabSales Invoice` si 
                      Inner Join `tabSales Invoice Item` ssi where ssi.parent=si.name and si.status="Paid" {a} """.format(a=a),as_dict=1)
      print(c)
      return c
