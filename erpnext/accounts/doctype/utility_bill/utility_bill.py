# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import requests, json
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, get_datetime, get_url, nowdate, now_datetime, money_in_words
from erpnext.custom_utils import check_future_date
from erpnext.integrations.bank_api import fetch_balance
from erpnext.accounts.doctype.bank_payment.bank_payment import get_transaction_id

class UtilityBill(Document):
    def validate(self):
        check_future_date(self.posting_date)
        self.calculate_tds_net()
        self.get_bank_available_balance()
        self.remove_bill_without_os()
        self.update_pi_number()
        if self.workflow_state == "Waiting For Verification":
            self.payment_status="Pending"
            
    def before_submit(self):
        self.utility_payment()
        self.update_status()
        # if self.payment_status=="Payment Successful":
        #     self.make_direct_payment()
        
    def update_pi_number(self):
        for a in self.get("item"):
            if not a.pi_number:
                a.pi_number = get_transaction_id()

    def get_bank_available_balance(self):
        if self.bank_account and frappe.db.get_value('Bank Payment Settings', "BOBL", 'enable_one_to_one'):
            try:
                result = fetch_balance(self.bank_account)
            except Exception as e:
                frappe.msgprint(_("Unable to fetch Bank Balance.\n  {}").format(str(e)))
            else:
                if result['status'] == "0":
                    self.bank_balance = result['balance_amount']
                else:
                    frappe.msgprint(_("Unable to fetch Bank Balance.\n  {}").format(result['error']))

    def on_submit(self):
        self.db_set("workflow_state", self.payment_status)
    
    def on_cancel(self):
        if self.workflow_state=="Partial Payment" or self.workflow_state=="Payment Successful":
            frappe.throw("Not allowed to cancel the Utility Bill Payments")
    
    def update_status(self):
        success = failed = 0
        for a in self.item:
            if a.payment_status == "Failed":
                failed += 1
            elif a.payment_status == "Success":
                success += 1
        if success > 0 and failed > 0:
            self.payment_status = "Partial Payment"
        elif failed == 0 and success > 0:
            self.payment_status = "Payment Successful"
        elif failed > 0 and success == 0:
            self.payment_status = "Payment Failed"
        
    def calculate_tds_net(self):
        total_amount = total_tds = net_amount = 0.00
        for a in self.item:
            total_amount += a.invoice_amount
            total_tds += a.tds_amount
            net_amount += a.net_amount
        self.total_bill_amount = total_amount
        self.total_tds_amount = total_tds
        self.net_payable_amount = net_amount
        
        if self.tds_percent and not self.net_payable_amount:
            frappe.throw("Net Payable amount should be greater than zero")
    
    def utility_payment(self):
        for d in self.item:
            if d.outstanding_amount > 0 and not d.payment_status_code:
                api_name, service_id, service_type, consumer_field = frappe.db.get_value("Utility Service Type", d.utility_service_type, ["payment_api", "service_id", "service_type", "unique_key_field"])
                api_details = frappe.get_doc("API Detail", api_name)
                url = api_details.api_link
                api_param = {}
                os = str(d.outstanding_amount)
                if os.count("."):
                    os_nu = os.split(".",1)[0]
                    os_ch = os.split(".",1)[1]
                    os_ch = os_ch if len(os_ch) > 1 else str(os_ch)+"0"
                    actual_os = str(os_nu)+"."+str(os_ch)
                else:
                    actual_os = str(os)
                for a in api_details.item:
                    if a.pre_defined_value:
                        api_param[a.param] = str(a.defined_value)
                    elif a.param == "serviceid":
                        api_param[a.param] = str(service_id)
                    elif a.param == "servicetype":
                        api_param[a.param] = str(service_type)
                    elif a.param == "FrmAcctNum":
                        api_param[a.param] = str(self.bank_account)
                    elif a.param == "Amt":
                        api_param[a.param] = str(actual_os)
                    elif a.param == "pi":
                        api_param[a.param] = d.pi_number
                if consumer_field == "landlnenumber":
                    consumer_field = "landlinenumber"
    
                api_param[consumer_field] = str(d.consumer_code)
                payload = json.dumps(api_param)
                d.request = str(payload)
                headers = {
                'Content-Type': 'application/json'
                }               
                response = requests.request("POST", url, headers=headers, data=payload)
                details = response.json()
                d.response = str(details)
                res_status = details['statusCode']
                d.payment_status_code = res_status
                if res_status == "00":
                    d.payment_response_msg = details['ResultMessage']
                    d.payment_journal_no = details['jrnlno']
                    d.payment_status = "Success"
                else:
                    d.payment_response_msg = details['ErrorMessage']
                    d.payment_status = "Failed"

    @frappe.whitelist()
    def get_utility_services(self):
        data = []
        data = frappe.db.sql("""
                      SELECT 
                        i.utility_service_type, i.customer_identification, 
                        i.consumer_code, i.party,
                        i.service_id, i.service_type
                      FROM `tabUtility Services` u 
                      INNER JOIN `tabUtility Services Item` i
                      ON u.name = i.parent
                      WHERE i.disabled = 0
                        and u.name = '{}'
                       """.format(self.utility_services), as_dict=True)
        self.set('item', [])
        for d in data:
            row = self.append('item', {})
            api_name, service_id, service_type, consumer_field, expense_account = frappe.db.get_value("Utility Service Type", d.utility_service_type, ["fetch_outstanding_api", "service_id", "service_type", "unique_key_field","expense_account"])
            api_details = frappe.get_doc("API Detail", api_name)
            url = api_details.api_link
            api_param = {}
            for a in api_details.item:
                if a.pre_defined_value:
                    api_param[a.param] = a.defined_value
                elif a.param == "SERVICEID":
                    api_param[a.param] = service_id
                elif a.param == "SERVICETYPE":
                    api_param[a.param] = service_type
            if str(consumer_field) != "RRCOTaxCode":
                api_param[consumer_field.upper()] = d.consumer_code
            else:
                api_param[consumer_field] = d.consumer_code
            
            payload = json.dumps(api_param)
            headers = {
            'Content-Type': 'application/json'
            }

            response = requests.request("POST", url, headers=headers, data=payload)
            details = response.json()
            res_status = details['statusCode']
            row.payment_status = "Pending"
            if res_status == "00":
                row.invoice_amount = details['ResultMessage']
                row.outstanding_amount = details['ResultMessage']
                row.response_msg = "Success"
                row.net_amount = details['ResultMessage']
            elif res_status == "01":
                row.response_msg = details['ErrorMessage']
            row.debit_account = expense_account
            row.outstanding_datetime = now_datetime()
            row.fetch_status_code = res_status
            row.create_direct_payment = 1
            row.update(d)
    
    @frappe.whitelist()
    def get_utility_outstandings(self):
        for d in self.item:
            frappe.msgprint("d:{}".format(str(d)))
            if not d.utility_service_type:
                frappe.throw("Utility Service Type is mandatory")
            api_name, service_id, service_type, consumer_field, expense_account = frappe.db.get_value("Utility Service Type", d.utility_service_type, ["fetch_outstanding_api", "service_id", "service_type", "unique_key_field","expense_account"])
            api_details = frappe.get_doc("API Detail", api_name)
            url = api_details.api_link
            api_param = {}
            for a in api_details.item:
                if a.pre_defined_value:
                    api_param[a.param] = a.defined_value
                elif a.param == "SERVICEID":
                    api_param[a.param] = service_id
                elif a.param == "SERVICETYPE":
                    api_param[a.param] = service_type
            if str(consumer_field) != "RRCOTaxCode":
                api_param[consumer_field.upper()] = d.consumer_code
            else:
                api_param[consumer_field] = d.consumer_code
                
            payload = json.dumps(api_param)
            headers = {
                'Content-Type': 'application/json'
            }

            response = requests.request("POST", url, headers=headers, data=payload)
            details = response.json()
            res_status = details['statusCode']
            d.payment_status = "In Progress"
            if res_status == "00":
                d.invoice_amount = details['ResultMessage']
                d.outstanding_amount = details['ResultMessage']
                d.response_msg = "Success"
                d.net_amount = details['ResultMessage']
            elif res_status == "01":
                d.response_msg = details['ErrorMessage']
                d.invoice_amount = 0
                d.outstanding_amount = 0
                d.net_amount = 0
            d.debit_account = expense_account
            d.outstanding_datetime = now_datetime()
            d.fetch_status_code = res_status

    @frappe.whitelist()
    def make_direct_payment(self):
        if self.direct_payment:
            frappe.throw("Direct Payment No. <b> {} </b>already created for this Utility Bill".format(self.direct_payment))

        doc = frappe.new_doc("Direct Payment")
        doc.branch = self.branch
        doc.cost_center = self.cost_center
        doc.posting_date = self.posting_date
        doc.payment_type = "Payment"
        doc.tds_percent = self.tds_percent
        doc.tds_account = self.tds_account
        doc.credit_account = self.expense_account
        doc.utility_bill = str(self.name)
        doc.business_activity = self.business_activity
        doc.remarks = "Utility Bill Payment " + str(self.name)
        doc.status = "Completed"
        if self.item:
            count_child = 0
            for a in self.item:
                #if a.create_direct_payment:
                if a.invoice_amount > 0 and a.payment_status == "Success":
                    doc.append("item", {
                                "party_type": "Supplier",
                                "party": a.party,
                                "account": a.debit_account,
                                "amount": a.invoice_amount,
                                "invoice_no": a.invoice_no,
                                "invoice_date": a.invoice_date,
                                "tds_applicable": a.tds_applicable,
                                "taxable_amount": a.invoice_amount,
                                "tds_amount": a.tds_amount,
                                "net_amount": a.net_amount,
                                "payment_status": "Payment Successful"
                        })
                    count_child +=1
            if count_child > 0:
                doc.save()
            if doc.name:
                self.db_set("direct_payment", doc.name)
            return doc.name
        # doc = frappe.new_doc("Direct Payment")
        # doc.branch = self.branch
        # doc.cost_center = self.cost_center
        # doc.posting_date = self.posting_date
        # doc.payment_type = "Payment"
        # doc.tds_percent = self.tds_percent
        # doc.tds_account = self.tds_account
        # doc.credit_account = self.expense_account
        # doc.utility_bill = str(self.name)
        # doc.business_activity = self.business_activity
        # doc.remarks = "Utility Bill Payment " + str(self.name)
        # doc.status = "Completed"
        # if self.item:
        #     count_child = 0
        #     for a in self.item:
        #         if a.create_direct_payment:
        #             if a.invoice_amount > 0 and a.payment_status == "Success":
        #                 doc.append("item", {
        #                         "party_type": "Supplier",
        #                         "party": a.party,
        #                         "account": a.debit_account,
        #                         "amount": a.invoice_amount,
        #                         "invoice_no": a.invoice_no,
        #                         "invoice_date": a.invoice_date,
        #                         "tds_applicable": a.tds_applicable,
        #                         "taxable_amount": a.invoice_amount,
        #                         "tds_amount": a.tds_amount,
        #                         "net_amount": a.net_amount,
        #                         "payment_status": "Payment Successful"
        #                     })
        #                 count_child +=1
        #     if count_child > 0:
        #         doc.submit()
        #     if doc.name:
        #         self.db_set("direct_payment", doc.name)
        #         frappe.msgprint("Direct Payment created and submitted for this Utility Bill")
                
    def remove_bill_without_os(self):
        to_remove = []
        for d in self.get("item"):
            if not d.outstanding_amount:
                to_remove.append(d)
                
        [self.remove(d) for d in to_remove]