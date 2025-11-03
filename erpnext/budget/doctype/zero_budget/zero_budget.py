# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from typing import TYPE_CHECKING, Optional
from frappe import _
from frappe.utils import now
from frappe.model.document import Document

class ZeroBudget(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:  # pragma: no cover
        from erpnext.budget.doctype.zero_budget_item.zero_budget_item import ZeroBudgetItem
        from frappe.types import DF

        amended_from: DF.Link | None
        company: DF.Link | None
        posting_date: DF.Date | None
        project: DF.Link | None
        total: DF.Float
        zero_budget_item: DF.Table[ZeroBudgetItem]
    # end: auto-generated types

    def on_submit(self):
        update_original_budget(self,"Submit")

    def on_cancel(self):
        self.flags.ignore_links = True

    def before_cancel(self):
        update_original_budget(self,"Cancel")

@frappe.whitelist(allow_guest=True)
def work_breakdown_structure(project = None):
    # Fetch WBS records linked to the specified project
    wbs = frappe.get_all(
        "Work Breakdown Structure",
        fields=["name", "wbs_name", "wbs_level", "overall_budget", "gl_account", "available_budget"],
        filters={"project": project,"docstatus":1,"wbs_level": ["!=", '0']}  # Only filter by project
    )
    return wbs

def update_original_budget(self,event):
    wbs_dict = []
    wbs_list = []
    if self.zero_budget_item:
        for row in self.zero_budget_item:
            if row.get("wbs_element") not in wbs_list:
                wbs_list.append(row.get("wbs_element"))
    if wbs_list:
        for i in wbs_list:
            wbs_dict.append({
                "wbs_id": i,
                "voucher_name":"",
                "voucher_type":"",
                "amount":0.0
            })

    for row in self.zero_budget_item:
        amount = row.get("zero_budget")
        if row.get("wbs_element"):
            for j in wbs_dict:
                if row.get("wbs_element") == j.get("wbs_id"):
                    j.update({
                        "amount": j.get("amount") + row.get("zero_budget"),
                        "wbs_name": frappe.db.get_value("Work Breakdown Structure",row.get("wbs_element"), "wbs_name"),
                        "wbs_level":row.get("wbs_level"),
                        "txn_date":self.posting_date,
                        "voucher_type":self.doctype,
                        "voucher_name":self.name
                    })
            wbs_curr_doc = frappe.get_doc("Work Breakdown Structure",row.get("wbs_element"))
            if event == "Submit":
                wbs_curr_doc.original_budget = wbs_curr_doc.original_budget + amount
                wbs_curr_doc.overall_budget = wbs_curr_doc.original_budget
                wbs_curr_doc.available_budget = wbs_curr_doc.overall_budget - wbs_curr_doc.assigned_overall_budget
                if wbs_curr_doc.locked:
                    frappe.throw(
                        "Transaction Not Allowed for  WBS Element - {0} as this WBS is locked !".format(wbs_curr_doc.name)
                    )
            elif event == "Cancel":
                wbs_curr_doc.original_budget = wbs_curr_doc.original_budget - amount
                wbs_curr_doc.overall_budget = wbs_curr_doc.original_budget
                wbs_curr_doc.available_budget = wbs_curr_doc.overall_budget - wbs_curr_doc.assigned_overall_budget
                if wbs_curr_doc.locked:
                    frappe.throw(
                        "Transaction Not Allowed for  WBS Element - {0} as this WBS is locked !".format(wbs_curr_doc.name)
                    )
            wbs_curr_doc.save(ignore_permissions=True)

    if wbs_dict:
        for i in wbs_dict:
            create_budget_entry(self,i,event,self.company) 
    
def create_budget_entry(self,row,event,company):
    if row.get("wbs_id"):
        bgt_ent = frappe.new_doc("Budget Entry")
        if "projects" in frappe.get_installed_apps():
            bgt_ent.project = self.project
        bgt_ent.wbs = row.get("wbs_id")
        bgt_ent.wbs_name = row.get("wbs_name")
        bgt_ent.wbs_level = row.get("wbs_level")
        bgt_ent.company = company
        bgt_ent.posting_date = self.posting_date
        if event == "Submit":
            bgt_ent.overall_credit = row.get("amount")            
        elif event == "Cancel":
            bgt_ent.overall_debit = row.get("amount")   

        bgt_ent.voucher_type = "Zero Budget"
        bgt_ent.voucher_no = self.name
        bgt_ent.voucher_submit_date = now()
        bgt_ent.save(ignore_permissions=True)
        bgt_ent.submit()