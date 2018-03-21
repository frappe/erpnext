# -*- coding: utf-8 -*-
# Copyright (c) 2015, Erpdeveloper.team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe.utils import flt, getdate
from frappe.utils import cint
from frappe import _
from frappe.utils import nowdate, add_days
import frappe.desk.form.assign_to

import barcode
from barcode.writer import ImageWriter
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class AdministrativeDecision(Document):

    def autoname(self):
        # if self.type == "Coming" :
        #   self.naming_series = "AD-IN/"
        # elif self.type == "Out" :
        #   self.naming_series = "AD-OUT/"
        # elif self.type == "Inside" :
        #   self.naming_series = "AD-INSIDE/"
        # else:
        #   self.naming_series = "AD/"
            
        naming_method = frappe.db.get_value("HR Settings", None, "emp_created_by")
        if not naming_method:
            throw(_("Please setup Employee Naming System in Human Resource > HR Settings"))
        else:
            if naming_method == 'Naming Series':
                self.name = make_autoname(self.naming_series + '.####')
        self.transaction_number = self.name

        if self.type == "Sent Document" :
            self.issued_number = self.name  




    # API for Generate Barcode Button 
    # js calls api and give it name of image
    def barcode_attach2(self,name):
        try:
            # frappe.throw(str(name))
            barcode_class = barcode.get_barcode_class('code39')
            ean = barcode_class(name, ImageWriter(), add_checksum=False)
            barcode_path = frappe.get_site_path()+'/public/files/'
            ean.save(barcode_path+name)
            # ean.save(barcode_path+self.name+'.png')

            self.save_image("/files/", name + '.png')

            img_path = "/files/" + name + ".png"

            # frappe.db.sql("""update `tabAdministrative Decision` set barcode_img = %s
            #     where name = %s""", (img_path, name))
            # frappe.db.commit()

            self.barcode_img = img_path
            # administrative_doc = frappe.get_doc('Administrative Decision', name) 
            # administrative_doc.barcode_img = img_path
            # administrative_doc.save()
            # frappe.db.commit()


            return img_path

        except Exception as e:
            raise e
        

    def barcode_attach(self):
        barcode_class = barcode.get_barcode_class('code39')
        ean = barcode_class(self.name, ImageWriter(), add_checksum=False)
        barcode_path = frappe.get_site_path()+'/public/files/'

        ean.save(barcode_path+self.name)
        # ean.save(barcode_path+self.name+'.png')

        self.save_image("/files/",self.name + '.png')
        
    def save_image(self,path, name):
        # save barcode image to file table
        attach_image = frappe.get_doc({
            "doctype": "File",
            "file_name": name,
            "file_url": path + name,
            "folder":"home"
        })

        attach_image.insert()


    def after_insert(self):
        self.barcode_attach()
        img_path = "/files/" + self.name + ".png"

        # frappe.db.sql("""update `tabAdministrative Decision` set barcode_img = %s
        #     where name = %s""", (img_path, self.name))
        # frappe.db.commit()

        self.barcode_img = img_path
        # administrative_doc = frappe.get_doc('Administrative Decision', self.name) 
        # administrative_doc.barcode_img = img_path
        # administrative_doc.save()
        # frappe.db.commit()



    def validate(self):
        # self.validate_dates()
        self.check_employee()

        # self.check_branch_department()
        # self.validate_fields()
        if self.get('docstatus') == 1:
            self.validate_approve()
            # if self.state != "Active" and  not self.get('__islocal'):
            #   frappe.throw(_("All board must Approve before submitted"))


    def on_update(self):
        self.assign_to_admins()

    def assign_to_admins(self):
        pass


    # def validate_dates(self):
    #   if getdate(self.start_date) > getdate(self.end_date):
    #       frappe.throw(_("End Date can not be less than Start Date"))
            
    def check_employee(self) :
        if self.type == "Inside Document" :
            if not self.employee:
                frappe.throw(_("Employee Missing"))
        elif self.type == "Received Document":
            if not self.coming_from:
                frappe.throw(_("The Issued Address Missing"))



    # def check_branch_department(self):
    #   if self.type == "Inside" :
    #       if not self.department or not self.branch:
    #           frappe.throw(_("Add Branch and Department information"))
    #       if not self.start_date:
    #           frappe.throw(_("Add Start Date"))

    # def validate_fields(self):
    #   if self.type == "Out":
    #       if not self.start_date:
    #           frappe.throw(_("Add Start Date"))
        # if self.type == "Out" or self.type == "Coming" :
        #   if not self.end_date:
        #       frappe.throw(_("Add End Date"))

    def validate_approve(self):
        checker = 1
        decision = self.administrative_board
        if decision:
            for d in self.administrative_board :
                if d.decision != "Approve":
                    checker =0
            if checker==1:
                self.state = "Active"


    def change_administrative_board_decision(self,decision):
        administrative_board = frappe.get_doc('Administrative Board',{'parent' :self.name ,
        'user_id':frappe.session.user } )       # self.administrative_board
        if administrative_board :
            administrative_board.set("decision",decision)
            administrative_board.save()
        return administrative_board

def get_emp(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql(""" select name,employee_name from `tabEmployee` """)

    