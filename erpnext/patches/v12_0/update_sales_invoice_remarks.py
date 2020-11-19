from __future__ import unicode_literals
import frappe

from frappe import _
from frappe.utils import formatdate

def execute():
    si_list = frappe.db.get_all('Sales Invoice', filters = {
        'docstatus': 1,
        'remarks': 'No Remarks',
        'po_no' : ['!=', ''],
        'po_date' : ['!=', '']
        }, 
        fields = ['name', 'po_no', 'po_date']
    )

    for doc in si_list:
        remarks = _("Against Customer Order {0} dated {1}").format(doc.po_no, 
					formatdate(doc.po_date))
        
        frappe.db.set_value('Sales Invoice', doc.name, 'remarks', remarks)
        
        gl_entry_list = frappe.db.get_all('GL Entry', filters = {
            'voucher_type': 'Sales Invoice',
            'remarks': 'No Remarks',
            'voucher_no' : doc.name
            },
            fields = ['name']
        )
        
        for entry in gl_entry_list:
            frappe.db.set_value('GL Entry', entry.name, 'remarks', remarks)