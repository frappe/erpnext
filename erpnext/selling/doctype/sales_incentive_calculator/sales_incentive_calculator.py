# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SalesIncentiveCalculator(Document):

  pass

@frappe.whitelist()
def fetch_details(fd,td):
    a = frappe.db.sql("""select si.name,si.customer,si.outstanding_amount,si.posting_date from `tabSales Invoice` si where posting_date>= %s and posting_date <= %s""",(fd,td),as_dict=1)
    print(a)
    return a


@frappe.whitelist()
def get_payment(fd,td):
    a=frappe.db.sql("""select p.name,p.party_name,p.total_allocated_amount,p.posting_date from `tabPayment Entry` p where posting_date>= %s and posting_date<= %s""",(fd,td),as_dict=1)
    print(a)
    return a