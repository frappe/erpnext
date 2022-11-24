# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, now, get_bench_path,get_site_path, touch_file, getdate, get_datetime
from frappe.model.document import Document
from erpnext.integrations.bps import SftpClient
from erpnext.integrations.bank_api import intra_payment, inter_payment, inr_remittance, fetch_balance
import datetime
import os
from frappe.model.naming import make_autoname
import csv
from frappe.model.mapper import get_mapped_doc
import traceback
from datetime import datetime

class BankPayment(Document):
    def validate(self):
        self.update_status()
        self.set_defaults()
        self.validate_paid_from_account()
        self.validate_items()
        self.update_totals()
        self.get_bank_available_balance()
        self.check_one_one_or_bulk_payment()
        if self.transaction_type == "Leave Travel Concession":
            self.validate_je()
        

    def before_submit(self):
        self.validate_timing()
        self.update_status()
        self.update_pi_number()

    def on_submit(self):
        self.validate_mandatory()
        self.update_transaction_status()
    
    def on_cancel(self):
        self.check_for_transactions_in_progress()
        self.update_status()
        self.update_transaction_status(cancel=True)
  
    def update_pi_number(self):
        if self.payment_type == "One-One Payment":
            for a in self.get("items"):
                a.pi_number = get_transaction_id()
        else:
            if self.get("debit_notes"):
                intra_bank_pi = inter_bank_pi = inr_pi = " "
                for a in self.get("debit_notes"):
                    pi_no = get_transaction_id()
                    a.pi_number = pi_no
                    if a.note_type == "Intra-Bank Payment":
                        intra_bank_pi = pi_no
                    elif a.note_type == "Inter-Bank Payment":
                        inter_bank_pi = pi_no
                    else:
                        inr_pi = pi_no

                for b in self.get("items"):
                    if b.bank_name == "BOBL":
                        b.pi_number = intra_bank_pi
                    elif b.bank_name == "INR":
                        b.pi_number = inr_pi
                    else:
                        b.pi_number = inter_bank_pi
                
    def update_item_status(self, status):
        for rec in self.items:
            rec.status = status
            
    #added by cety on 9/08/2021 to not allow transaction for more than 10 records.
    def check_one_one_or_bulk_payment(self):
        get_max_transaction = frappe.db.get_value('Bank Payment Settings', "BOBL", 'transaction_limit')
        get_transaction = frappe.db.sql("""select count(bpi.employee) from `tabBank Payment` bp, `tabBank Payment Item` bpi where bp.name=bpi.parent and bp.name='{}'""".format(self.name))
        if self.transaction_type == "Salary" and self.payment_type == "One-One Payment" and get_transaction[0][0] > get_max_transaction:
            frappe.throw("For transaction more than 10 records, Please select Payment Type to Bulk Payment!")
        else:
            pass
    #added by cety on 15/09/2021 to not allow transaction after office hour.
    #Modified by Thukten to restrict timing only for Inter Bank Transaction
    def validate_timing(self):
        inter_transaction = frappe.db.sql("""select count(*) as transaction
                                            from `tabBank Payment` bp, `tabBank Payment Item` bpi 
                                            where bp.name=bpi.parent 
                                            and bp.name='{}'
                                            and bpi.bank_name!='BOBL'""".format(self.name), as_dict=True)
        if inter_transaction[0].transaction > 0:
            hms = '%H:%M:%S'
            now = datetime.now()
            now_time = now.strftime(hms)
            now_time = datetime.strptime(now_time, hms)
            start_time = str(frappe.db.get_value("Bank Payment Settings", "BOBL", "from_time"))
            end_time = str(frappe.db.get_value("Bank Payment Settings", "BOBL", "to_time"))
            from_time = datetime.strptime(start_time, hms)
            to_time = datetime.strptime(end_time, hms)
            if now_time >= from_time and now_time <= to_time:
                pass
            else:
                frappe.throw("<b>Inter Bank Transaction</b> are only allowed between from <b>{}</b> till <b>{} </b>!".format(start_time, end_time), title="Transaction Restricted!")

    #added by kinley on 2021-12-16
    def validate_je(self):
        doc = frappe.get_doc("Leave Travel Concession", self.transaction_no)
        je = frappe.get_doc("Journal Entry",str(doc.journal_entry))
        if je.docstatus != 1:
            frappe.throw("Journal Entry {} linked wih Leave Travel Concession {} is not submitted".format(je.name,self.transaction_no))
        
    def get_bank_available_balance(self):
        ''' get paying bank balance '''
        if self.bank_account_no:
            if frappe.db.get_value('Bank Payment Settings', self.bank_name, 'enable_one_to_one'):
                try:
                    result = fetch_balance(self.bank_account_no)
                    if result['status'] == "0":
                        self.bank_balance = result['balance_amount']
                    else:
                        frappe.msgprint(_("Unable to fetch Bank Balance.\n  {}").format(result['error']))
                except Exception as e:
                    frappe.msgprint(_("Unable to fetch Bank Balance.\n  {}").format(str(e)))
        if flt(self.bank_balance) > 0 and flt(self.bank_balance) < flt(self.total_amount):
            frappe.throw("Current Bank Balance {} is less than the total payment amount {}".format(self.bank_balance, self.total_amount))

    def check_for_transactions_in_progress(self):
        if self.status in ("Failed", "Waiting Acknowledgement"):
            frappe.throw(_("Cancellation is not permitted for status <b>{}</b>").format(self.status))
        for i in frappe.get_all("Bank Payment Item", ["*"],{"parent": self.name, "status": "Completed"}):
            frappe.throw(_("<b>Row#{}:</b> Cancellation is not permitted as payment for <b>{}</b> is already complete").format(i.idx, i.beneficiary_name), title="Failed")

    def update_status(self):
        status = {0: 'Draft', 1: 'Pending', 2: 'Cancelled'}[self.docstatus]
        if self.docstatus == 2:
            self.db_set("status", "Cancelled")
            self.db_set('workflow_state', 'Cancelled')

        self.status = status
        self.update_item_status(status)

    @frappe.whitelist()
    def process_payment(self):
        if self.status != "Pending":
            frappe.msgprint(_("Only transactions in Pending status can be processed"))
            return

        if self.payment_type == "Bulk Payment":
            process_bulk_payment(self)
        else:
            process_one_to_one_payment(self)

    @frappe.whitelist()
    def reupload_files(self):
        upload_files(self)

    def validate_items(self):
        if not self.get("items"):
            frappe.throw(_("No transactions found for payment processing"), title="No Data Found")

        # duplicate transaction checks
        for i in self.get("items"):
            if i.bank_branch and not i.financial_system_code:
                i.financial_system_code = frappe.db.get_value("Financial Institution Branch", i.bank_branch, "financial_system_code")
            if not i.bank_account_type or not i.bank_account_no:
                frappe.throw("Row#{}: <b>Bank Account Type</b> or <b>Account No</b> are missing ".format(i.idx))
            for j in frappe.db.sql("""
                    select name, docstatus from `tabBank Payment` bp
                    where bp.name != "{name}"
                    and bp.transaction_type = "{transaction_type}"
                    and bp.docstatus < 2
                    and exists(select 1
                        from `tabBank Payment Item` bpi
                        where bpi.parent = bp.name
                        and bpi.transaction_type = bp.transaction_type
                        and bpi.transaction_id = "{transaction_id}"
                        and bpi.transaction_reference = "{transaction_reference}"
                        and bpi.status != 'Failed')
                """.format(name=self.name, transaction_type=i.transaction_type, transaction_id=i.transaction_id, transaction_reference=i.transaction_reference),as_dict=True):
                frappe.throw(_("Row#{}: {} is already processed via {}").format(
                        i.idx, frappe.get_desk_link(i.transaction_type,i.transaction_id),
                        frappe.get_desk_link(self.doctype, j.name)
                    ), title="Transaction Details")

    def update_transaction_status(self, cancel=False):
        ''' update respective transactions status '''
        for i in self.get("items"):		
            if cancel:
                status = 'Payment Cancelled'
            elif i.status == 'Completed':
                status = 'Payment Successful'
            elif i.status == 'Failed':
                status = 'Payment Failed'
            else:
                status = 'Payment Under Process'

            if self.transaction_type == 'Direct Payment':
                doc = frappe.get_doc('Direct Payment', i.transaction_id)
                doc.payment_status = status
                for rec in doc.item:
                    if rec.name == i.transaction_reference:
                        rec.payment_status = status
                        rec.bank_payment = self.name
                doc.save(ignore_permissions=True)

            elif self.transaction_type == 'Payment Entry':
                doc = frappe.get_doc('Payment Entry', i.transaction_id)
                doc.payment_status = status
                doc.bank_payment = self.name
                doc.save(ignore_permissions=True)
            elif self.transaction_type == 'Journal Entry':
                doc = frappe.get_doc('Journal Entry', i.transaction_id)
                doc.payment_status = status
                doc.bank_payment = self.name
                doc.save(ignore_permissions=True)

    def set_defaults(self):
        self.posting_date = now()

    def validate_mandatory(self):
        if not self.payment_type:
            frappe.throw(_("<b>Payment Type</b> is mandatory"))

        if frappe.db.get_value('Bank Payment Settings', self.bank_name, 'enable_one_to_one'):
            if not flt(self.bank_balance) or (flt(self.total_amount) > flt(self.bank_balance)):
                frappe.throw(_("Insufficient Bank Balance to proceed"))
        else:
            if self.payment_type == 'One-One Payment':
                frappe.throw(_("One-One Payment is disabled"))

        # validate transactions
        for rec in self.items:
            if not rec.beneficiary_name:
                frappe.throw(_("Row#{} : <b>Beneficiary Name</b> is mandatory").format(rec.idx))
            elif not rec.bank_name:
                frappe.throw(_("Row#{} : <b>Beneficiary Bank</b> is missing for <b>{}</b>").format(rec.idx, rec.beneficiary_name))
            elif not rec.bank_account_no:
                frappe.throw(_("Row#{} : <b>Beneficiary Bank Account No.</b> is missing for <b>{}</b>").format(rec.idx, rec.beneficiary_name))
            elif not flt(rec.amount):
                frappe.throw(_("Row#{} : <b>Amount</b> should be greater than 0 <b>{}</b>").format(rec.idx, rec.beneficiary_name))

            if rec.bank_name not in (self.bank_name, 'INR'):
                if not rec.bank_branch:
                    frappe.throw(_("Row#{} : <b>Bank Branch</b> is missing for <b>{}</b>").format(rec.idx, rec.beneficiary_name))
                elif not rec.financial_system_code:
                    frappe.throw(_("Row#{} : <b>Financial System Code</b> is missing for Bank Branch<b>{}</b>").format(rec.idx, rec.bank_branch))

    def validate_paid_from_account(self):
        ''' validate paid_from account for bank details '''
        if not self.paid_from:
            frappe.throw(_("Paid From is mandatory"))

        doc = frappe.db.get("Account", self.paid_from)
        self.bank_name = doc.bank_name
        self.bank_branch = doc.bank_branch
        self.bank_account_type = doc.bank_account_type
        self.bank_account_no = doc.bank_account_no
        if doc:
            if not doc.bank_name:
                frappe.throw(_("<b>Bank Name</b> is not set for {}").format(frappe.get_desk_link("Account",self.paid_from)))
            elif not doc.bank_branch:
                frappe.throw(_("<b>Bank's Branch</b> is not set for {}").format(frappe.get_desk_link("Account",self.paid_from)))
            elif not doc.bank_account_type:
                frappe.throw(_("<b>Bank Account Type</b> is not set for {}").format(frappe.get_desk_link("Account",self.paid_from)))
            elif not doc.bank_account_no:
                frappe.throw(_("<b>Bank Account No.</b> is not set for {}").format(frappe.get_desk_link("Account",self.paid_from)))

            if not frappe.db.exists("Bank Payment Settings", doc.bank_name):
                frappe.throw(_("Bank Payment Settings for <b>{}</b> not configured in the system").format(doc.bank_name))

    def set_payment_type(self):
        transaction_limit = frappe.db.get_value("Bank Payment Settings", self.bank_name, "transaction_limit")

        if cint(transaction_limit) < 0:
            frappe.throw(_("Invalid <b>Transaction Limit</b> under {}").format(frappe.get_desk_link("Bank Payment Settings", self.bank_name)))  
        self.payment_type = "One-One Payment" if cint(len(self.items)) <= cint(transaction_limit) else "Bulk Payment"

    @frappe.whitelist()
    def get_entries(self):
        self.load_items()
        self.load_banks()							
        self.load_debit_notes()
        return self.total_amount

    def update_totals(self):
        total_amount = 0
        for i in self.items:
            total_amount += flt(i.amount,2)
        self.load_banks()
        self.load_debit_notes()
        self.total_amount = total_amount
        return total_amount

    def load_items(self):
        total_amount = 0
        self.set('items', [])
        for i in self.get_transactions():
            import re
            beneficiary_name = re.sub('[^A-Za-z0-9 ]+', '', i.beneficiary_name)
            row = self.append('items', {})
            row.update(i)
            total_amount += flt(i.amount,2)
        
        self.total_amount = total_amount
        if not self.get("items"):
            frappe.throw(_("No transactions found for payment processing for <b>{}</b>").format(self.transaction_type), title="No Data Found")
            return total_amount
  
    def load_banks(self):
        bank_totals  = {}

        self.set('banks', [])
        for i in self.items:
            if i.bank_name in bank_totals:
                bank_totals[i.bank_name] += flt(i.amount,2)
            else:
                bank_totals[i.bank_name] = flt(i.amount,2)

        for i in bank_totals:
            row = self.append('banks', {})
            row.update({'bank_name': i, 'amount': bank_totals[i]})

    def load_debit_notes(self):
        debit_notes  = {}
        self.validate_paid_from_account()

        bank = frappe.db.get_value("Account", self.paid_from, "bank_name")
        for i in self.items:
            if i.bank_name == "INR":
                debit_notes['INR Payment'] = flt(debit_notes.get('INR Payment'),2) + flt(i.amount,2)
            elif i.bank_name == bank:
                debit_notes['Intra-Bank Payment'] = flt(debit_notes.get('Intra-Bank Payment'),2) + flt(i.amount,2)
            else:
                debit_notes['Inter-Bank Payment'] = flt(debit_notes.get('Inter-Bank Payment'),2) + flt(i.amount,2)

        self.set('debit_notes', [])
        for i in debit_notes:
            row = self.append('debit_notes', {})
            row.update({'note_type': i, 'amount': debit_notes[i], 'debit_note': None})

    def get_transactions(self):
        data = []
        if self.transaction_type == "Mechanical Payment":
            data = self.get_mechanical_payments()
        elif self.transaction_type == "Salary":
            data = self.get_salary()
        elif self.transaction_type in ("Bonus"):
            frappe.msgprint(_("Under development"))
        elif self.transaction_type == "Payment Entry":
            data = self.get_payment_entry()
        elif self.transaction_type == "Direct Payment":
            data = self.get_direct_payment()
        elif self.transaction_type == "Journal Entry":
            data = self.get_journal_entry()
        elif self.transaction_type == "Leave Travel Concession":
            data = self.get_ltc_payment()
        elif self.transaction_type == "Employee Loan Payment":
            data = self.get_loan_detail()
        elif self.transaction_type == "PBVA":
            data = self.get_pbva()
        return data
    
    """
    # Fetch Employee Loan Details
    # Author: thukday@gmail.com
    # Date : 2022-02-07
    """
    def get_loan_detail(self):
        if not self.institution_name:
            frappe.throw("Please select Financial Institution")

        doc = frappe.get_doc("Financial Institution", self.institution_name)
        if not doc.employee_loan_payment_in_bob:
            return frappe.db.sql("""SELECT "Salary Slip" transaction_type, t1.name transaction_id, 
                            t2.name transaction_reference, t1.modified transaction_date,
                            t1.employee, t1.employee_name beneficiary_name, 
                            t2.institution_name bank_name, t2.bank_branch, fib.financial_system_code,
                            t2.bank_account_type, t2.reference_number as bank_account_no, t2.amount,
                            'Loan remittance for {month}-{salary_year}' remarks, "Draft" status						
                        FROM `tabSalary Slip` t1
                            JOIN `tabSalary Detail` t2 ON t1.name = t2.parent
                            LEFT JOIN `tabFinancial Institution Branch` fib ON fib.name = t2.bank_branch
                        WHERE t1.fiscal_year = '{salary_year}'
                        AND t2.amount > 0
                        AND t2.salary_component = 'Financial Institution Loan'
                        AND t1.month = '{salary_month}'
                        AND t1.docstatus = 1
                        AND t2.institution_name = '{institution}'
                        AND NOT EXISTS(select 1
                            FROM `tabBank Payment Item` bpi
                            WHERE bpi.transaction_type = 'Salary Slip'
                            AND bpi.transaction_id = t1.name
                            AND bpi.transaction_reference = t2.name
                            AND bpi.parent != '{bank_payment}'
                            AND bpi.docstatus != 2
                            AND bpi.status NOT IN ('Cancelled', 'Failed')
                        )
                    """.format(salary_year=self.fiscal_year, 
                        salary_month=self.get_month_id(self.month),
                        month=self.month, institution=self.institution_name,
                        bank_payment = self.name), as_dict=True)
        else:
            return frappe.db.sql("""SELECT "Salary Slip" transaction_type, t1.name transaction_id, 
                            t2.name transaction_reference, t1.modified transaction_date,
                            fi.account_holder_name beneficiary_name, 
                            'BOBL' as bank_name, fi.bank_branch, fib.financial_system_code,
                            fi.bank_account_type, fi.account_no bank_account_no, sum(t2.amount) as amount,
                            'Loan remittance for {month}-{salary_year}' remarks, "Draft" status						
                        FROM `tabSalary Slip` t1
                            JOIN `tabSalary Detail` t2 ON t1.name = t2.parent
                            JOIN `tabFinancial Institution` fi ON fi.name = t2.institution_name
                            LEFT JOIN `tabFinancial Institution Branch` fib ON fib.name = fi.bank_branch
                        WHERE t1.fiscal_year = '{salary_year}'
                        AND t2.salary_component = 'Financial Institution Loan'
                        AND t1.month = '{salary_month}'
                        AND t1.docstatus = 1
                        AND t2.institution_name = '{institution}'
                    """.format(salary_year=self.fiscal_year, 
                        salary_month=self.get_month_id(self.month),
                        month=self.month, institution=self.institution_name,
                        bank_payment = self.name), as_dict=True)

    def get_journal_entry(self):
        data = []
        if self.pf_remittance:
            if not self.pf_vendor:
                frappe.throw("Please select PF Service Provider/Vendor")
            ven_doc = frappe.get_doc("Supplier", self.pf_vendor)
            for a in frappe.db.sql("""select je.name transaction_id, jea.name transaction_reference, 
                                je.posting_date transaction_date, round(jea.credit_in_account_currency,2) as credit
                                from `tabJournal Entry` je join `tabJournal Entry Account` jea
                                on je.name = jea.parent
                                left join `tabAccount` a on a.name = jea.account
                                where je.name = '{journal_entry}'
                                and a.account_type = "Bank"
                                and je.docstatus = 1
                                AND NOT EXISTS(select 1
                                    FROM `tabBank Payment Item` bpi
                                    WHERE bpi.transaction_type = 'Journal Entry'
                                    AND bpi.transaction_id = je.name
                                    AND bpi.parent != '{bank_payment}'
                                    AND bpi.docstatus != 2
                                    AND bpi.status NOT IN ('Cancelled', 'Failed')
                                )
                                """.format(journal_entry = self.transaction_no, bank_payment = self.name), as_dict=True):
                data.append(frappe._dict({
                            'transaction_type': 'Journal Entry',
                            'transaction_id': a.transaction_id,
                            'trnasaction_reference': a.transaction_reference,
                            'transaction_date': a.transaction_date,
                            'supplier': ven_doc.name,
                            'beneficiary_name': ven_doc.supplier_name,
                            'bank_name': ven_doc.bank_name_new,
                            'bank_branch': ven_doc.bank_branch,
                            'bank_account_type': ven_doc.bank_account_type,
                            'bank_account_no': ven_doc.account_number,
                            'amount': flt(a.credit),
                            'status': "Draft",
                            'remarks': "PF Remittance"
                        }))
            return data
        cond = ""
        if self.transaction_no:
            cond = 'AND je.name = "{}"'.format(self.transaction_no)
        elif not self.transaction_no and self.from_date and self.to_date:
            cond = 'AND je.posting_date BETWEEN "{}" AND "{}"'.format(str(self.from_date), str(self.to_date))       
        for a in frappe.db.sql("""SELECT je.name transaction_id, je.posting_date transaction_date
                                FROM `tabJournal Entry` je 
                                where je.branch = "{branch}"
                                {cond}
                                AND je.voucher_type = 'Bank Entry'
                                AND je.docstatus = 1
                                AND NOT EXISTS(select 1
                                    FROM `tabBank Payment Item` bpi
                                    WHERE bpi.transaction_type = 'Journal Entry'
                                    AND bpi.transaction_id = je.name
                                    AND bpi.parent != '{bank_payment}'
                                    AND bpi.docstatus != 2
                                    AND bpi.status NOT IN ('Cancelled', 'Failed')
                                )
                                ORDER BY je.posting_date
                            """.format(branch = self.branch, 
                             bank_payment = self.name, 
                            cond = cond), as_dict=True):
            amount_to_deposit = 0.00
            party_type = party = reference_type = reference_name = ""
            party_count = 0
            
            for p in frappe.db.sql("""select party_type, party, count(distinct party) as party_count, user_remark
                                from `tabJournal Entry Account` 
                                where parent = '{journal_entry}'
                                AND party IS NOT NULL
                                AND party != ""
                                """.format(journal_entry = a.transaction_id), as_dict=True):
                party_count = p.party_count
                party = p.party
                party_type = p.party_type
            if party_count > 1:
                frappe.msgprint("Bank Payment is not allowed from this Journal Entry {} as there are two partys involved".format(a.transaction_id))
            else:
                for b in frappe.db.sql("""SELECT ja.name transaction_reference, ja.reference_type, 
                                            ja.reference_name, ja.party_type, ja.party, ja.account,
                                        round(ja.debit_in_account_currency,2) as debit_amount, 
                                        round(ja.credit_in_account_currency,2) as credit_amount
                                        FROM `tabJournal Entry Account` ja
                                        WHERE ja.parent = '{parent}'
                                    """.format(parent = a.transaction_id), as_dict=True):
                    if frappe.db.get_value("Account", b.account, "account_type") == "Bank" and b.credit_amount > 0:
                        amount_to_deposit +=  flt(b.credit_amount)
                    if not party_type and not party:
                        reference_type = b.reference_type if b.reference_type and not reference_type else ""
                        reference_name = b.reference_name if b.reference_name and not reference_name else ""
                        if reference_type and reference_name:
                            if reference_type in ['Travel Authorization','Travel Claim','Overtime Application','Leave Encashment','Employee Benefits']:
                                party_type = "Employee"
                                party      = frappe.db.get_value(reference_type, reference_name, "employee")
                            else:
                                party_type = "Supplier"
                                party      = frappe.db.get_value(reference_type, reference_name, "employee")
                        if not party:
                            frappe.msgprint("Party missing for Journal Entry {}".format(a.transaction_id))
                employee = supplier = ""
                if party_type == "Supplier":
                    query = """select s.bank_name_new as bank_name, s.bank_branch, s.bank_account_type, 
                                    s.account_number as bank_account_no, s.supplier_name as beneficiary_name,
                                    (CASE WHEN s.bank_name_new = "INR" THEN s.inr_bank_code ELSE NULL END) inr_bank_code,
                                    (CASE WHEN s.bank_name_new = "INR" THEN s.inr_purpose_code ELSE NULL END) inr_purpose_code
                                    from `tabSupplier` s
                                    WHERE s.name = '{party}'
                                """.format(party = party)
                    supplier = party
                elif party_type == "Employee":
                    query = """select e.bank_name, e.bank_branch, e.bank_account_type, e.employee_name as beneficiary_name,
                                    e.bank_ac_no as bank_account_no, NULL inr_bank_code, NULL inr_purpose_code
                                    from `tabEmployee` e
                                    WHERE e.name = '{party}'
                                """.format(party = party)
                    employee = party
                if amount_to_deposit > 0:
                    for c in frappe.db.sql(query, as_dict=True):					
                        data.append(frappe._dict({
                            'transaction_type': 'Journal Entry',
                            'transaction_id': a.transaction_id,
                            'transaction_date': a.transaction_date,
                            'employee': employee,
                            'supplier': supplier,
                            'beneficiary_name': c.beneficiary_name,
                            'bank_name': c.bank_name,
                            'bank_branch': c.bank_branch,
                            'bank_account_type': c.bank_account_type,
                            'bank_account_no': c.bank_account_no,
                            'amount': flt(amount_to_deposit),
                            'inr_bank_code': c.inr_bank_code,
                            'inr_purpose_code': c.inr_purpose_code,
                            'status': "Draft",
                            'vehicle_no': p.user_remark
                        }))
        return data

    def get_direct_payment(self):
        cond = ""
        if self.transaction_no:
            cond = 'AND dp.name = "{}"'.format(self.transaction_no)
        elif not self.transaction_no and self.from_date and self.to_date:
            cond = 'AND dp.posting_date BETWEEN "{}" AND "{}"'.format(str(self.from_date), str(self.to_date))

        return frappe.db.sql("""SELECT "Direct Payment" transaction_type, dp.name transaction_id, 
                dpi.name transaction_reference, dp.posting_date transaction_date, 
                (CASE WHEN dpi.party_type = 'Supplier' THEN dpi.party ELSE NULL END) as supplier, 
                (CASE WHEN dpi.party_type = 'Employee' THEN dpi.party ELSE NULL END) as employee, 
                (CASE WHEN dpi.party_type = 'Supplier' THEN s.supplier_name ELSE e.employee_name END) as beneficiary_name,
                (CASE WHEN dpi.party_type = 'Supplier' THEN s.bank_name_new ELSE e.bank_name END) as bank_name, 
                (CASE WHEN dpi.party_type = 'Supplier' THEN s.bank_branch ELSE e.bank_branch END) as bank_branch, 
                (CASE WHEN dpi.party_type = 'Supplier' THEN s.bank_account_type ELSE e.bank_account_type END) as bank_account_type, 
                (CASE WHEN dpi.party_type = 'Supplier' THEN s.account_number ELSE e.bank_ac_no END) as bank_account_no,
                round((dpi.net_amount-(select ifnull(sum(dpd.amount),0)
                            from `tabDirect Payment Deduction` dpd
                            where dpd.parent = dp.name 
                            and dpd.party_type = dpi.party_type
                            and dpd.party = dpi.party
                        )
                ),2) amount						
                FROM `tabDirect Payment` dp 
                INNER JOIN `tabDirect Payment Item` dpi ON dpi.parent = dp.name
                LEFT JOIN `tabSupplier` s ON dpi.party_type = 'Supplier' AND s.name = dpi.party
                LEFT JOIN `tabEmployee` e ON dpi.party_type = 'Employee' AND e.name = dpi.party
                WHERE dp.branch = "{branch}" 
                {cond}
                AND dp.docstatus = 1
                AND ifnull(dp.utility_bill,'') = ''
                AND dpi.party_type IS NOT NULL
                AND dpi.party IS NOT NULL
                AND IFNULL(dpi.net_amount,0) > 0
                AND ifnull(dpi.payment_status,'') IN ('','Failed','Payment Failed')
                AND NOT EXISTS(select 1
                FROM `tabBank Payment Item` bpi
                WHERE bpi.transaction_type = 'Direct Payment'
                AND bpi.transaction_id = dp.name
                AND bpi.transaction_reference = dpi.name
                AND bpi.parent != '{bank_payment}'
                AND bpi.docstatus != 2
                AND bpi.status NOT IN ('Cancelled', 'Failed')
                )
        ORDER BY dp.posting_date, dp.name """.format(direct_payment = self.transaction_no, 
            bank_payment = self.name,
            branch = self.branch,
            cond = cond), as_dict=True)

    def get_payment_entry(self):
        cond = ""
        if self.transaction_no:
            cond = 'AND pe.name = "{}"'.format(self.transaction_no)
        elif not self.transaction_no and self.from_date and self.to_date:
            cond = 'AND pe.posting_date BETWEEN "{}" AND "{}"'.format(str(self.from_date), str(self.to_date))
    
        return frappe.db.sql("""SELECT "Payment Entry" transaction_type, pe.name transaction_id, 
                        pe.name transaction_reference, pe.posting_date transaction_date, 
                        pe.party as supplier, pe.party as beneficiary_name, 
                        s.bank_name_new as bank_name, s.bank_branch, fib.financial_system_code, s.bank_account_type, s.account_number as bank_account_no,
                        round((pe.paid_amount + (select ifnull(sum(ped.amount),0)
                                            from `tabPayment Entry Deduction` ped
                                            where ped.parent = pe.name
                                            )
                        ),2) amount,
                        (CASE WHEN s.bank_name_new = "INR" THEN s.inr_bank_code ELSE NULL END) inr_bank_code,
                        (CASE WHEN s.bank_name_new = "INR" THEN s.inr_purpose_code ELSE NULL END) inr_purpose_code,
                        "Draft" status
                    FROM `tabPayment Entry` pe
                    JOIN `tabSupplier` s ON s.name = pe.party
                    LEFT JOIN `tabFinancial Institution Branch` fib ON fib.name = s.bank_branch
                    WHERE pe.branch = "{branch}" 
                    {cond}
                    AND pe.docstatus = 1
                    AND pe.party_type = 'Supplier'
                    AND pe.party IS NOT NULL
                    AND IFNULL(pe.paid_amount,0) > 0
                    AND NOT EXISTS(select 1
                        FROM `tabBank Payment Item` bpi
                        WHERE bpi.transaction_type = 'Payment Entry'
                        AND bpi.transaction_id = pe.name
                        AND bpi.parent != '{bank_payment}'
                        AND bpi.docstatus != 2
                        AND bpi.status NOT IN ('Cancelled', 'Failed')
                    )
        ORDER BY pe.posting_date, pe.name """.format( 
            bank_payment = self.name,
            branch = self.branch,
            cond = cond), as_dict=True)

    def get_month_id(self, month_abbr):
        return {"January": "01", "February": "02", "March": "03", "April": "04", "May": "05", "June": "06",
            "July": "07", "August": "08", "September": "09", "October": "10", "November": "11", "December": "12"}[month_abbr]

    def get_conditions(self):
        cond = []
        for field_name in ("employee", "department", "division"):
            if self.get(field_name):
                cond.append('t1.{} = "{}"'.format(field_name, self.get(field_name)))

        if self.region:
            child_cc = get_child_cost_centers(self.region)
            if child_cc:
                if len(child_cc) == 1:
                    cond.append("""t1.cost_center = "{}" """.format(child_cc[0]))
                else:
                    child_cc = map(str, child_cc)
                    cond.append("""t1.cost_center in {}""".format(tuple(child_cc)))

        if cond:
            cond = ' AND ' + ' AND '.join(cond)
        return cond if cond else ""

    def get_salary(self):
        cond = ""
        if not self.fiscal_year:
            frappe.throw(_("Please select Fiscal Year"))
        elif not self.month:
            frappe.throw(_("Please select Month"))

        cond = self.get_conditions()
        return frappe.db.sql("""SELECT "Salary Slip" transaction_type, t1.name transaction_id, 
                        t1.name transaction_reference, t1.modified transaction_date,
                        t1.employee, t1.employee_name beneficiary_name, 
                        IFNULL(t1.bank_name, e.bank_name) bank_name, 
                        IFNULL(t1.bank_branch, e.bank_branch) bank_branch, fib.financial_system_code,
                        e.bank_account_type,
                        IFNULL(t1.bank_account_no, e.bank_ac_no) bank_account_no, 
                        round(t1.net_pay,2) amount,
                        'Salary for {month}-{salary_year}' remarks, "Draft" status						
                    FROM `tabSalary Slip` t1
                        JOIN `tabEmployee` e ON t1.employee = e.name
                        LEFT JOIN `tabFinancial Institution Branch` fib ON fib.name = IFNULL(t1.bank_branch, e.bank_branch)
                    WHERE t1.fiscal_year = '{salary_year}'
                    AND t1.month = '{salary_month}'
                    AND t1.docstatus = 1
                    AND e.salary_mode = 'Bank'
                    {cond}
                    AND IFNULL(t1.net_pay,0) > 0
                    AND NOT EXISTS(select 1
                        FROM `tabBank Payment Item` bpi, `tabBank Payment` bp
                        WHERE bpi.transaction_type = 'Salary Slip'
                        AND bp.name=bpi.parent
                        AND bp.transaction_type not in ('Employee Loan Payment')
                        AND bpi.transaction_id = t1.name
                        AND bpi.parent != '{bank_payment}'
                        AND bpi.docstatus != 2
                        AND bpi.status NOT IN ('Cancelled', 'Failed')
                    )
        """.format(salary_year=self.fiscal_year, 
            salary_month=self.get_month_id(self.month),
            month=self.month,
            bank_payment = self.name,
            cond = cond), as_dict=True)

    def get_mechanical_payments(self):
        if self.transaction_no:
            cond = 'and t1.name = "{}"'.format(self.transaction_no)

        data = frappe.db.sql("""
            select 
                'Mechanical Payment' as transaction_type,
                name 		 as transaction_id, 
                posting_date 	 as transaction_date,
                beneficiary_name,
                beneficiary_bank as bank_name,
                beneficiary_branch as bank_branch,
                beneficiary_bank_account_no as bank_account_no,
                round(net_amount,2) 	 as amount
            from `tabMechanical Payment` t1
            where t1.expense_account = "{paid_from}"
            and t1.docstatus = 1
            and t1.online_payment = 1
            and t1.bank_payment is null
            {cond}
            and not exists(select 1
                from `tabBank Payment Item` t2
                where t2.transaction_type = "{transaction_type}"
                and t2.transaction_id = t1.name
                and t2.docstatus < 2
                and t2.parent != "{name}")
        """.format(paid_from=self.paid_from, name=self.name, 
                transaction_type=self.transaction_type, cond=cond), as_dict=True)
        return data

    #ltc payment added by cety on 12/16/2021
    def get_ltc_payment(self):
        cond = ""
        if not self.fiscal_year:
            frappe.throw(_("Please select Fiscal Year"))
        if self.transaction_no:
            cond = "and ltc.name = '{}'".format(self.transaction_no)
        if self.branch:
            cond = "and ltc.branch='{}'".format(self.branch)
        return frappe.db.sql("""SELECT 
                            "Leave Travel Concession" as transaction_type, ltc.name as transaction_id, ltc.name as transaction_reference,
                            ltc.posting_date as transaction_date, ltcd.employee_name as beneficiary_name,
                            ltcd.bank_name, (select bank_branch from `tabEmployee` where name=ltcd.employee) as bank_branch,
                            (select bank_account_type from `tabEmployee` where name=ltcd.employee) as bank_account_type, ltcd.bank_ac_no as bank_account_no, ltcd.amount
                            FROM `tabLeave Travel Concession` ltc, `tabLTC Details` ltcd
                            WHERE ltc.docstatus = 1
                            {cond}
                            AND ltc.name = ltcd.parent
                            AND NOT EXISTS(select 1 
                                        FROM `tabBank Payment Item` bpi
                                        WHERE bpi.transaction_type = 'Leave Travel Concession'
                                        AND bpi.transaction_id = ltc.name
                                        AND bpi.parent != '{bank_payment}'
                                        AND bpi.docstatus != 2
                                        AND bpi.status NOT IN ('Cancelled', 'Failed')
                            )
                            """.format( cond = cond, bank_payment = self.name), as_dict=1)
    #added by cety on 5-04-2022
    def get_pbva(self):
        cond = ""
        if not self.fiscal_year:
            frappe.throw(_("Please select Fiscal Year"))
        if self.transaction_no:
            cond = "and p.name = '{}'".format(self.transaction_no)
        if self.branch:
            cond = "and p.branch='{}'".format(self.branch)
        if self.fiscal_year:
            cond += "and p.fiscal_year='{}'".format(self.fiscal_year)
        return frappe.db.sql("""SELECT 
                            "PBVA" as transaction_type, p.name as transaction_id, p.name as transaction_reference,
                            p.posting_date as transaction_date, 
                            pd.employee_name as beneficiary_name,
                            (select bank_name from `tabEmployee` where name=pd.employee) as bank_name, 
                            (select bank_branch from `tabEmployee` where name=pd.employee) as bank_branch,
                            (select bank_account_type from `tabEmployee` where name=pd.employee) as bank_account_type, 
                            (select bank_ac_no from `tabEmployee` where name=pd.employee)as bank_account_no, 
                            pd.balance_amount as amount
                            FROM `tabPBVA` p, `tabPBVA Details` pd
                            WHERE p.docstatus = 1
                            {cond} 
                            AND p.name = pd.parent
                            AND NOT EXISTS(select 1 
                                        FROM `tabBank Payment Item` bpi
                                        WHERE bpi.transaction_type = 'PBVA'
                                        AND bpi.transaction_id = p.name
                                        AND bpi.parent != '{bank_payment}'
                                        AND bpi.docstatus != 2
                                        AND bpi.status NOT IN ('Cancelled', 'Failed')
                            )
                            """.format( cond = cond, bank_payment = self.name), as_dict=1)
        
def process_one_to_one_payment(doc, publish_progress=True):
    stat = 0
    processing = completed = failed = doc_modified = 0
    PromoCode = frappe.db.get_value("Bank Payment Settings", "BOBL", "promo_code")
    for i in doc.get("items"):
        PEMSRefNum = i.pi_number
        bpi = frappe.get_doc('Bank Payment Item', i.name)
        if i.bank_name == "BOBL":
            from_acc = doc.bank_account_no
            trans_amount = i.amount
            to_acc = i.bank_account_no 
            result = intra_payment(from_acc, trans_amount, PromoCode, to_acc, PEMSRefNum)
        elif i.inr_bank_code:
            Amt = i.amount
            AcctNum = doc.bank_account_no
            BnfcryAcct = i.bank_account_no
            BnfcryName = i.beneficiary_name
            BnfcryAddr1 = "Benficiary Address"
            IFSC = ""
            BankCode = ""
            PurpCode = ""
            RemittersName = ""
            RemittersAddr1 = ""
            ComsnOpt = ""
            if i.employee:
                bnf_acc_type = frappe.db.get_value("Employee", i.employee, "bank_account_type")
            else:
                bnf_acc_type = frappe.db.get_value("Supplier", i.supplier, "bank_account_type")
            BnfcryAcctTyp = bnf_acc_type
            BnfcryRmrk = str(doc.remarks)
            RemitterName = doc.company
            BfscCode = frappe.db.get_value("Financial Institution Branch", frappe.db.get_value("Supplier", i.supplier, "bank_branch"), "financial_system_code")
            RemitterAcctType = frappe.db.get_value("Account", doc.paid_from, "bank_account_type")
            result = inr_remittance(AcctNum, Amt, BnfcryAcct, BnfcryName, BnfcryAddr1, IFSC, BankCode, PurpCode, RemittersName, RemittersAddr1, ComsnOpt, PromoCode, PEMSRefNum)
        else:
            Amt = i.amount
            PayeeAcctNum = doc.bank_account_no
            BnfcryAcct = i.bank_account_no
            BnfcryName = i.beneficiary_name
            if i.financial_system_code and i.bank_account_type:
                bnf_acc_type = i.bank_account_type
                BfscCode = i.financial_system_code
            else:
                if i.bank_branch:
                    bnf_acc_type = i.bank_account_type
                    BfscCode = str(frappe.db.get_value("Financial Institution Branch", i.bank_branch, "financial_system_code"))
                elif i.employee:
                    bnf_acc_type = frappe.db.get_value("Employee", i.employee, "bank_account_type")
                    BfscCode = str(frappe.db.get_value("Financial Institution Branch", frappe.db.get_value("Employee", i.employee, "bank_branch"), "financial_system_code"))
                elif i.supplier:
                    bnf_acc_type = frappe.db.get_value("Supplier", i.supplier, "bank_account_type")
                    BfscCode = str(frappe.db.get_value("Financial Institution Branch", frappe.db.get_value("Supplier", i.supplier, "bank_branch"), "financial_system_code"))
            BnfcryAcctTyp = bnf_acc_type
            BnfcryRmrk = str(doc.remarks)
            RemitterName = doc.company
            RemitterAcctType = frappe.db.get_value("Account", doc.paid_from, "bank_account_type")
            result = inter_payment(Amt, PayeeAcctNum, BnfcryAcct, BnfcryName, BnfcryAcctTyp, BnfcryRmrk, RemitterName, BfscCode, RemitterAcctType, PEMSRefNum)
        if result['status'] == "Success":
            completed += 1
            bpi.db_set("status", "Completed")
        else:
            stat = 1
            failed += 1
            bpi.db_set("status", "Failed")
        
        bpi.db_set("error_message", str(result['message']))
        bpi.db_set("bank_journal_no", str(result['jrnl_no']))

    # update bank payment and transaction status
    status = None
    if completed and failed:
        status = "Partial Payment"
    elif failed:
        status = "Failed"
    elif completed:
        status = "Completed"

    if status:
        doc.db_set('status', status)
        doc.db_set('workflow_state', status)
        doc.reload()
        doc.update_transaction_status()
        doc.reload()

def process_bulk_payment(doc, publish_progress=True):
    ''' generate and sftp the files to bank '''
    posting_date= get_datetime()
    if doc.status in ('Draft', 'Completed', 'Cancelled', 'Waiting Acknowledgement'):
        frappe.throw(_("You cannot process payment for transactions in <b>{}</b> status").format(doc.status))

    generate_files(doc, posting_date)
    upload_files(doc)
    doc.reload()

def generate_files(doc, posting_date):
    ''' generate files for pending transactions '''
    file_list   = []

    # do not generate any new files if there are old ones Pening for upload or Waiting Acknowledgement  
    if frappe.db.exists("Bank Payment Upload", {"parent": doc.name, "status": ("in",("Pending", "Waiting Acknowledgement"))}):
        return

    for i in doc.get("debit_notes"):
        filepath = ""
        filename = get_filename(i.note_type, posting_date, i.pi_number)
        debit_note = str(get_site_path())+"/"+str(i.debit_note)
        noof_transactions = 0

        # add debit note manual attachments if any
        if i.amount and i.debit_note and not frappe.db.exists("Bank Payment Upload", {"parent": doc.name, "file_name": str(doc.name)+str(os.path.basename(debit_note)), "docstatus": 1}):
            file_list.append([str(debit_note), str(doc.name)+str(os.path.basename(debit_note)), noof_transactions])

        # add bank payment file
        if i.note_type == "Intra-Bank Payment":			
            filepath, noof_transactions = get_intra_bank_file(doc, filename, posting_date)
            if filepath:
                file_list.append([filepath, os.path.basename(filepath), noof_transactions])
        elif i.note_type == "Inter-Bank Payment":
            filepath, noof_transactions = get_inter_bank_file(doc, filename, posting_date)
            if filepath:
                file_list.append([filepath, os.path.basename(filepath), noof_transactions])
        elif i.note_type == "INR Payment":
            filepath, noof_transactions = get_inr_bank_file(doc, filename, posting_date)
            if filepath:
                file_list.append([filepath, os.path.basename(filepath), noof_transactions])

    if not file_list:
        frappe.msgprint(_("No transactions found for processing"))

    for file in file_list:
        row = doc.append('uploads', {})
        row.update({
            'file_name': file[1],
            'local_path': file[0],
            'remote_path': file[1],
            'noof_transactions': file[2],
            'uploaded': posting_date,
            'status': 'Pending',
            'docstatus': 1
        })
        row.save(ignore_permissions=True)
    return file_list

def upload_files(doc):
    try:
        sftp = SftpClient(doc.bank_name)
    except Exception as e:
        frappe.throw(_("Connection to bank failed {}").format(str(e)))

    error = 0
    for rec in doc.uploads:
        bpu = frappe.get_doc('Bank Payment Upload', rec.name)
        status 	  = bpu.status
        error_msg = None
        if rec.status in ('Pending', 'Upload Failed'):
            try:
                sftp.upload_list([[rec.local_path, rec.remote_path]])
            except Exception as e:
                error += 1
                status = 'Upload Failed'
                error_msg = traceback.format_exc()
            else:
                status = 'Waiting Acknowledgement'

            bpu.db_set('status', status)
            bpu.db_set('error', error_msg)
            bpu.db_set('last_updated', get_datetime())

            for i in doc.items:
                if rec.file_name and i.file_name and rec.file_name.lower() == i.file_name.lower():
                    frappe.get_doc('Bank Payment Item', i.name).db_set('status','Waiting Acknowledgement' if not error else 'Upload Failed')

    doc.db_set("status", "Waiting Acknowledgement" if not error else "Upload Failed")
    doc.db_set("workflow_state", "Waiting Acknowledgement" if not error else "Upload Failed")
    doc.reload()
    sftp.close()
        
def get_transaction_id(bank="BOBL"):
    promo_code = frappe.db.get_value('Bank Payment Settings', bank, 'promo_code')
    return make_autoname(str(promo_code) + '.YYYY.MM.DD.########')

def get_filename(note_type, posting_date, pi_number):
    posting_date = posting_date.strftime('%Y%m%d%H%M%S')
    
    if note_type == 'Intra-Bank Payment':
        filename = ["PEMSPAY", posting_date[:8], pi_number]
    elif note_type == 'Inter-Bank Payment':
        filename = ["BULK", "00020", posting_date[:8], pi_number]
    elif note_type == 'INR Payment':
        filename = ["INR", pi_number, "00010", posting_date[:8], "111111", pi_number[-3:]]
    else:
        filename = pi_number

    return "_".join(filename)

def get_intra_bank_file(doc, filename, posting_date, account_type="01"):
    ''' generate file in intra bank format and return the filename '''
 
    debit_rec   = []
    credit_rec  = []
    total_amount= 0

    filepath = ''
    slno	 = 0

    # get credit records for transactions
    for i in doc.get("items"):
        narration = str(doc.name) + ' ' + str(doc.remarks if doc.remarks else i.remarks)
        account_type = "03" if i.bank_account_type == "03" else "01"
        if str(doc.bank_name) == str(i.bank_name) and i.status in ('Pending', 'Failed'):
            slno += 1
            frappe.get_doc('Bank Payment Item', i.name).db_set('file_name', filename+'.csv')
            credit_rec.append([account_type, i.bank_account_no, flt(i.amount,2), "BTN", 
                      filename.split("_")[-1], narration[:30], posting_date.strftime("%d%m%Y"), "1"])
            total_amount += flt(i.amount,2)

    # get debit record for paid_from 
    if total_amount:
        debit_rec.append(["51", doc.bank_account_no, flt(total_amount,2), "BTN", 
                    filename.split("_")[-1], remove_special_characters(narration[:30]), posting_date.strftime("%d%m%Y"), "1"])

    # generate file if both debit and credit records exist
    if debit_rec and credit_rec:
        filepath = get_site_path('private','files','epayment','upload').rstrip("/")+"/"

        # create the directory epayment if it does not exist
        if not os.path.exists(filepath):
            os.makedirs(filepath)

        filepath = filepath+filename+'.csv'
        with open(filepath, 'w') as file:
            writer = csv.writer(file)
            writer.writerows(debit_rec+credit_rec)

    noof_transactions = slno
    return filepath, noof_transactions

def get_inter_bank_file(doc, filename, posting_date, account_type="01"):
    ''' generate file in inter bank format and return the filename '''

    rec  = []
    total_amount= 0

    filepath	= ''
    slno	= 0
    paying_customer = frappe.db.get_value("Bank Payment Settings", doc.bank_name, "paying_customer")  

    # get credit records for transactions
    for i in doc.get("items"):
        narration = str(doc.name) + ' ' + str(doc.remarks if doc.remarks else i.remarks)
        if str(doc.bank_name) not in (str(i.bank_name),'INR') and i.status in ('Pending', 'Failed'):
            slno += 1
            amount_str = format_amount(i.amount)
            frappe.get_doc('Bank Payment Item', i.name).db_set('file_name', filename+'.csv')
            rec.append([slno, doc.bank_account_no, paying_customer, i.financial_system_code, i.bank_account_type,
                   i.bank_account_no, i.beneficiary_name[:50], remove_special_characters(narration[:100]), "BTN", amount_str,
                   posting_date.strftime("%Y%m%d"), 0, 0, filename.split("_")[-1]])
   
            total_amount += flt(i.amount,2)

    if len(rec):
        # header row
        total_amount_str = format_amount(total_amount)
        rec = [["03", "001", "01", "FT01", "001", "BHUB", "RMAB", "1", "1",  posting_date.strftime("%Y%m%d%H%M%S"),
                    posting_date.strftime("%Y%m%d") , len(rec), total_amount_str, filename.split("_")[-1]]] + rec

    # generate file if both debit and credit records exist
    if rec:
        filepath = get_site_path('private','files','epayment','upload').rstrip("/")+"/"
        if not os.path.exists(filepath):
            os.makedirs(filepath)

        filepath = filepath+filename+'.csv'
        with open(filepath, 'w') as file:
            writer = csv.writer(file)
            writer.writerows(rec)

    noof_transactions = slno
    return filepath, noof_transactions

def format_amount(amount):
    amount_str = str(flt(amount,2))
    amount_str_nu = amount_str.split(".")[0] 
    amount_str_ch = amount_str.split(".")[1].ljust(2,"0")
    amount_str =  str(amount_str_nu) + "." + str(amount_str_ch)
    return amount_str

def remove_special_characters(narration):
    import re
    formatted_narration = re.sub('[^A-Za-z0-9]+', ' ', str(narration))
    return formatted_narration

def get_inr_bank_file(doc, filename, posting_date):
    posting_date = posting_date.strftime("%Y%m%d%H%M%S") 

@frappe.whitelist()
def get_paid_from(doctype, txt, searchfield, start, page_len, filters):
    if not filters.get("branch"):
        frappe.msgprint(_("Please select <b>Paid From Branch</b> first"))
    data = []
    data = frappe.db.sql("""select a.name, a.bank_name, a.bank_branch, a.bank_account_type, a.bank_account_no
        from `tabBranch` b, `tabAccount` a
        where b.name = "{}"
        and a.name = b.expense_bank_account
        and a.bank_name is not null
        and a.bank_branch is not null
        and a.bank_account_type is not null
        and a.bank_account_no is not null
    """.format(filters.get("branch")))

    if filters.get("branch") and not data:
        expense_bank_account = frappe.db.get_value("Branch", filters.get("branch"), "expense_bank_account")
        if not expense_bank_account:
            frappe.msgprint(_("Default <b>Expense Bank Account</b> is not set for this branch"))
        else:
            account = frappe.db.get("Account", expense_bank_account)
            if not account.bank_name:
                frappe.msgprint(_('<b>Bank Name</b> is not set for {}').format(frappe.get_desk_link("Account", expense_bank_account)))
            elif not account.bank_branch:
                frappe.msgprint(_("""<b>Bank Account's Branch</b> is not set for {} """).format(frappe.get_desk_link("Account", expense_bank_account)))
            elif not account.bank_account_no:
                frappe.msgprint(_('<b>Bank Account No.</b> is not set for {}').format(frappe.get_desk_link("Account", expense_bank_account)))
            elif not account.bank_account_type:
                frappe.msgprint(_('<b>Bank Account Type</b> is not set for {}').format(frappe.get_desk_link("Account", expense_bank_account)))
    return data

def get_child_cost_centers(current_cs=None):
    allchilds = allcs = []
    cs_name = cs_par_name = ""

    if current_cs:
        #Get all cost centers
        allcs = frappe.db.sql("SELECT name, parent_cost_center FROM `tabCost Center`", as_dict=True)
        #get the current cost center name
        query = """SELECT name, parent_cost_center FROM `tabCost Center` where name = "{}" """.format(current_cs)
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
