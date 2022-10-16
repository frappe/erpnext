# Copyright (c) 2016, Druk Holding & Investments Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import date_diff, get_last_day, nowdate, flt
from erpnext.accounts.general_ledger import make_gl_entries

##
#Return number of days between two dates or zero 
##
def get_number_of_days(end_date=None, start_date=None):
    if start_date and end_date:
        num_of_days = date_diff(start_date, end_date)
    else:
        num_of_days = 0
    
    return num_of_days

# Ver 20160627.1 by SSK, Fetching the latest
@frappe.whitelist()
def get_loss_tolerance():
    loss_tolerance = frappe.db.sql("select name,loss_tolerance,loss_qty_flat from `tabLoss Tolerance` order by creation desc limit 1;");
    #msgprint(_("Fetching Loss Tolerance {0}").format(loss_tolerance))
    return (loss_tolerance);

# Ver 20160627.1 by SSK, Fetching the latest
@frappe.whitelist()
def get_parent_cost_center(temp):
    parent_cc = frappe.db.sql("select name from `tabCost Center`;");
    return (parent_cc);

@frappe.whitelist()
def calculate_depreciation_date():
    return get_last_day(nowdate());

##
#Return all the child cost centers of the current cost center
##
def get_child_cost_centers(current_cs=None):
    allchilds = allcs = [];
    cs_name = cs_par_name = "";

    if current_cs:
        #Get all cost centers
        allcs = frappe.db.sql("SELECT name, parent_cost_center FROM `tabCost Center`", as_dict=True)
        #get the current cost center name
        query ="SELECT name, parent_cost_center FROM `tabCost Center` where name = \"" + current_cs + "\";"
        current = frappe.db.sql(query, as_dict=True)

        if(current):
            for a in current:
                cs_name = a['name']
                cs_par_name = a['parent_cost_center']

        #loop through the cost centers to search for the child cost centers
        allchilds.append(cs_name)
        for b in allcs:
            for c in allcs:
                if(c['parent_cost_center'] in allchilds):
                    if(c['name'] not in allchilds):
                        allchilds.append(c['name'])

    return allchilds

##
#Return all the child accounts of the current accounts
##
def get_child_accounts(current_acc=None):
    allchilds = allacc = []
    acc_name = acc_parent_name = ""

    if current_acc:
        #Get all cost centers
        allacc = frappe.db.sql("SELECT name, parent_account FROM `tabAccount`", as_dict=True)
        #get the current cost center name
        query ="SELECT name, parent_account FROM `tabAccount` where name = \"" + current_acc + "\";"
        current = frappe.db.sql(query, as_dict=True)

        if(current):
            for a in current:
                acc_name = a['name']
                acc_parent_name = a['parent_account']

        #loop through the cost centers to search for the child cost centers
        allchilds.append(acc_name)

        for b in allacc:
            for c in allacc:
                if(c['parent_account'] in allchilds):
                    if(c['name'] not in allchilds):
                        allchilds.append(c['name'])

    return allchilds

##
#Set default fiscal year
##
def get_fiscal_year(self):
    return frappe.utils.nowdate()[:4]

##
#Set default company
##
def get_company(self):
    return frappe.defaults.get_user_default("company")

##
# Update JVs if already depreciated
##
def update_jv(jv_name, dep_amount):
    jv = frappe.get_doc("Journal Entry", jv_name)
    ##Change the total debit and credit
    jv.db_set("total_debit", flt(dep_amount))
    jv.db_set("total_credit", flt(dep_amount))
    ##Change credit/debit_in_account_currency
    for acc in jv.accounts:
        jv_acc = frappe.get_doc("Journal Entry Account", acc.name)
        if acc.credit_in_account_currency > 0:
            #Set credit value
            jv_acc.db_set("credit_in_account_currency", flt(dep_amount))
        else:
            #Set debit value
            jv_acc.db_set("debit_in_account_currency", flt(dep_amount))
    
    ##Get the list of GL Entries related to the above journal entry
    gl_list = frappe.db.sql("select name from `tabGL Entry` where voucher_no = %s", jv_name, as_dict=True)
    
    for gl in gl_list:
        gl_obj = frappe.get_doc("GL Entry", gl.name)
        if gl_obj.debit_in_account_currency > 0:
            gl_obj.db_set("debit_in_account_currency", flt(dep_amount))
            gl_obj.db_set("debit", flt(dep_amount))
        else:
            gl_obj.db_set("credit_in_account_currency", flt(dep_amount))
            gl_obj.db_set("credit", flt(dep_amount))

