# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
import frappe
import os
from frappe.model.document import Document
from frappe.utils import get_site_base_path
from frappe.utils.data import flt, nowdate, getdate, cint
from frappe.utils.csvutils import read_csv_content_from_uploaded_file
from frappe.utils.password import update_password as _update_password
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate, get_datetime
from frappe.utils import date_diff
from datetime import timedelta
import datetime
from umalqurra.hijri_date import HijriDate
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta

def tst_emails():
    from frappe.core.doctype.communication.email import make
    content_msg_emp="test email send from tawari using tawari email"
    make(subject = "Passport Validity Notification", content=content_msg_emp, recipients='omar.ja93@gmail.com',
        send_email=True, sender="erp@tawari.sa")




def passport_validate_check():
    from frappe.core.doctype.communication.email import make
    frappe.flags.sent_mail = None

    emp = frappe.db.sql("select name,valid_upto,user_id,passport_validation_notification from `tabEmployee`")
    for i in emp:
        if i[1] and i[3]:
            date_difference = date_diff(i[1], getdate(nowdate()))

            if date_difference <= 30 :
                content_msg_emp="Your passport validity will end after {0} days".format(date_difference)
                content_msg_mng="Passport validity will end after {0} days for employee: {1}".format(date_difference,i[0])

                prefered_email = frappe.get_value("Employee", filters = {"name": i[0]}, fieldname = "prefered_email")
                prefered_email_mng = frappe.get_value("Employee", filters = {"name": 'EMP0015'}, fieldname = "prefered_email")
                prefered_email_mng1 = frappe.get_value("Employee", filters = {"name": 'EMP0007'}, fieldname = "prefered_email")
                prefered_email_mng2 = frappe.get_value("Employee", filters = {"name": 'EMP0050'}, fieldname = "prefered_email")

                if prefered_email:
                    try:
                        sent = 0
                        make(subject = "Passport Validity Notification", content=content_msg_emp, recipients=prefered_email,
                            send_email=True, sender="info@tadweeer.com")

                        # make(subject = "Passport Validity Notification", content=content_msg_mng, recipients=prefered_email_mng,
                        #     send_email=True, sender="info@tadweeer.com")

                        # make(subject = "Passport Validity Notification", content=content_msg_mng, recipients=prefered_email_mng1,
                        #     send_email=True, sender="info@tadweeer.com")

                        # make(subject = "Passport Validity Notification", content=content_msg_mng, recipients=prefered_email_mng2,
                        #     send_email=True, sender="info@tadweeer.com")

                        sent = 1
                        print 'send email for '+prefered_email
                    except:
                        frappe.msgprint("could not send")

                print content_msg_emp
                print content_msg_mng
                print '----------------------------------------------------------------'



def add_gosi_component():
    emps = frappe.get_all("Employee",filters={'emp_nationality': "Saudi Arabia" },fields={'name','employee_name'})
    for emp in emps:
        doc = frappe.db.sql("""select parent from `tabSalary Structure Employee` where employee = '{0}' """.format(emp.name))
        if (doc):
            x = frappe.get_doc("Salary Structure",doc[0][0])
            x.append("deductions", {
                            "salary_component": "Gosi",
                            "amount_based_on_formula": 1,
                            "formula": '(B+H)*.1',
                            "condition": ""
                        })
            x.save(ignore_permissions=True)
            print("*********************")
            print(x.name)

            

def tst_add_locc():
    frappe.get_doc({
        "doctype":"Leave Allocation",
        "employee": 'EMPtst0001',
        "employee_name": 'عمر',
        "leave_type": 'Annual Leave - اجازة اعتيادية',
        "from_date": '2020-01-01',
        "to_date": '2020-12-31',
        "carry_forward": cint(1),
        "new_leaves_allocated": 0,
        "docstatus": 1
    }).insert(ignore_permissions=True)



def tst_edit_allo():
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open('/home/frappe/frappe-bench/apps/client/client/Book1.csv', "r") as infile:  
        rows = read_csv_content(infile.read())
        for index, row in enumerate(rows):
            emp=frappe.db.sql("select work_days from `tabEmployee` where name='EMP00{0}'".format(row[0]))
            allocation = frappe.db.sql("select name from `tabLeave Allocation` where employee='EMP00{0}' order by creation desc limit 1".format(row[0]))
            
            doc = frappe.get_doc('Leave Allocation', allocation[0][0])
            doc.new_leaves_allocated = flt(row[3]) - (doc.total_leaves_allocated-flt(emp[0][0]))
            doc.flags.ignore_validate = True
            doc.save(ignore_permissions=True)
            print 'Done'




# def tst_edit_allo():
#     doc = frappe.get_doc('Leave Allocation', 'LAL/00692')
#     while doc.total_leaves_allocated != 65.84:
#         doc.new_leaves_allocated += 0.01
#         doc.flags.ignore_validate = True
#         doc.save(ignore_permissions=True)
#         print 'Done'




def tst_allo():
    length=frappe.db.sql("select count(name) from `tabEmployee` where status!='left'")
    emp=frappe.db.sql("select name,work_days from `tabEmployee` where status!='left'")

    for i in range(length[0][0]):
        deserved_leave = round(flt(emp[i][1])/12, 2)
        allocation = frappe.db.sql("select name from `tabLeave Allocation` where employee='{0}' order by creation desc limit 1".format( emp[i][0]))
        if allocation:
            if str(frappe.utils.get_last_day(nowdate())) == str(nowdate()):
                doc = frappe.get_doc('Leave Allocation', allocation[0][0])
                doc.new_leaves_allocated += deserved_leave
                doc.flags.ignore_validate = True
                doc.save(ignore_permissions=True)
                print 'Done'




def tst_leave():
    emp = frappe.get_list("Employee", filters={"name": 'EMPtst0001'}, fields=["work_days"])
    leave = frappe.get_list("Leave Allocation", filters={"employee": 'EMPtst0001'}, fields=["total_leaves_allocated,from_date,to_date"])
    leave_days = frappe.db.sql("select sum(total_leave_days) from `tabLeave Application` where docstatus=1 and employee='{0}' and posting_date between '{1}' and '{2}'".format('EMPtst0001', leave[0].from_date, leave[0].to_date))[0][0]
    if not leave_days:
        leave_days = 0
    leave_balance =  int(leave[0].total_leaves_allocated) - int(leave_days)

    current_date = datetime.datetime.strptime(str(nowdate()), '%Y-%m-%d')
    current_month = current_date.month

    current_year = datetime.datetime.strptime(str(leave[0].from_date), '%Y-%m-%d')
    current_year_month = current_year.month

    print leave_balance,current_month,current_year_month,leave[0].from_date



def tst_end_of_service():
    award_info = get_award('2016-01-01', '2018-05-22', 2500, 'دوام كامل' , 'استقالة الموظف')
    print round(award_info['award'],2)


def tst_sal():
    frappe.get_doc({
        "doctype": "Employee",
        "employee_name_english": "omar",
        "employee_name": "عمر",
        "designation": "المدير العام",
        "civil_id_no": 123456789,
        "emp_nationality": "Saudi Arabia",
        "date_of_joining": "2016-01-01",
        "date_of_birth": "1993-02-02",
        "naming_series": "EMPtst",
        "gender": "ذكر"
    }).insert(ignore_permissions=True)


def val_leave_expense():
    emp = frappe.get_list("Employee", filters={"name": 'EMP0001'}, fields=["work_days"])
    leave = frappe.get_list("Leave Allocation", filters={"employee": 'EMP0001'}, fields=["total_leaves_allocated"])
    print emp[0].work_days,leave[0].total_leaves_allocated
    if leave[0].total_leaves_allocated > int(emp[0].work_days):
        print leave[0].total_leaves_allocated - int(emp[0].work_days)
    else:
        frappe.throw("Employee {0} can't have leave balance expense claim this year".format('EMP0001'))



def add_contract_type():
    length=frappe.db.sql("select count(name) from `tabEmployee`")
    emp=frappe.db.sql("select name from `tabEmployee` ")

    for i in range(length[0][0]):
        print emp[i][0]
        doc_emp = frappe.get_doc('Employee', emp[i][0])
        doc_emp.type_of_contract = "دوام كامل"
        doc_emp.flags.ignore_validate = True
        doc_emp.save(ignore_permissions=True)



def valid_start_leave():
    # s = "2018-06-02"
    # posting date
    allocation = frappe.db.sql("select from_date,to_date from `tabLeave Allocation` where employee='EMP0006' order by creation asc limit 1")
    # from_date = datetime.datetime.strptime(str(allocation[0][0]), '%Y-%m-%d')
    valid_date = allocation[0][0] + relativedelta(months=+3)
    # print allocation[0][0]
    # print valid_date
    if date.today() < valid_date:
        print allocation[0][0]
        print valid_date

      



# def valid_start_leave():
#     s = "2018-06-02"
#     # posting date
#     allocation = frappe.db.sql("select from_date,to_date from `tabLeave Allocation` where employee='EMP0006' order by creation asc limit 1")
#     from_date = datetime.datetime.strptime(str(allocation[0][0]), '%Y-%m-%d')
#     valid_date = date(from_date.year, from_date.month, from_date.day) + relativedelta(months=+3)
#     # print allocation[0][0]
#     # print valid_date
#     if "2018-06-02" < valid_date:
#         print allocation[0][0]
#         print valid_date

      


def hooked_leave_allocation_builder():
    length=frappe.db.sql("select count(name) from `tabEmployee` where status!='left'")
    emp=frappe.db.sql("select name,date_of_joining,employee_name,department,emp_nationality,work_days from `tabEmployee` where status!='left'")
    c=0
    for i in range(length[0][0]):
        leave_allocation=frappe.db.sql("select from_date,to_date from `tabLeave Allocation` where employee='{0}' order by creation desc ".format(emp[i][0]))
        if leave_allocation:

            if str(datetime.date.today()) > str(leave_allocation[0][1]):
                next_allocation = datetime.datetime.strptime(str(leave_allocation[0][1]), '%Y-%m-%d')

                frappe.get_doc({
                    "doctype":"Leave Allocation",
                    "employee": emp[i][0],
                    "employee_name": emp[i][2],
                    "department": emp[i][3],
                    "leave_type": 'Annual Leave - اجازة اعتيادية',
                    "from_date": date(next_allocation.year, next_allocation.month, next_allocation.day) + relativedelta(days=+1),
                    "to_date": date(next_allocation.year, next_allocation.month, next_allocation.day) + relativedelta(days=+1,years=+1),
                    "carry_forward": cint(1),
                    "new_leaves_allocated": emp[i][5],
                    "docstatus": 1
                }).insert(ignore_permissions=True)

                
                print leave_allocation[0][0],leave_allocation[0][1]
                c+=1
        
        else:

            first_allocation = datetime.datetime.strptime(str(emp[i][1]), '%Y-%m-%d')
            next_first_allocation= date(first_allocation.year, first_allocation.month, first_allocation.day) + relativedelta(years=+0)
            next_second_allocation= date(first_allocation.year, first_allocation.month, first_allocation.day) + relativedelta(years=+1)

            if str(datetime.date.today()) > str(next_first_allocation):
                frappe.get_doc({
                    "doctype":"Leave Allocation",
                    "employee": emp[i][0],
                    "employee_name": emp[i][2],
                    "department": emp[i][3],
                    "leave_type": 'Annual Leave - اجازة اعتيادية',
                    "from_date": next_first_allocation,
                    "to_date": next_second_allocation,
                    "carry_forward": cint(1),
                    "new_leaves_allocated": emp[i][5],
                    "docstatus": 1
                }).insert(ignore_permissions=True)


    print 'Count ',c





def tst_allocation():
    length=frappe.db.sql("select count(name) from `tabEmployee` where status!='left'")
    emp=frappe.db.sql("select name,date_of_joining,employee_name,department,emp_nationality,work_days from `tabEmployee` where status!='left'")
    c=0
    for i in range(length[0][0]):
        leave_allocation=frappe.db.sql("select from_date,to_date from `tabLeave Allocation` where employee='{0}' order by creation desc ".format(emp[i][0]))
        if leave_allocation:

            if str(datetime.date.today()) > str(leave_allocation[0][1]):
                next_allocation = datetime.datetime.strptime(str(leave_allocation[0][1]), '%Y-%m-%d')

                frappe.get_doc({
                    "doctype":"Leave Allocation",
                    "employee": emp[i][0],
                    "employee_name": emp[i][2],
                    "department": emp[i][3],
                    "leave_type": 'Annual Leave - اجازة اعتيادية',
                    "from_date": date(next_allocation.year, next_allocation.month, next_allocation.day) + relativedelta(days=+1),
                    "to_date": date(next_allocation.year, next_allocation.month, next_allocation.day) + relativedelta(days=+1,years=+1),
                    "carry_forward": cint(1),
                    "new_leaves_allocated": emp[i][5],
                    "docstatus": 1
                }).insert(ignore_permissions=True)

                
                print leave_allocation[0][0],leave_allocation[0][1]
                c+=1

    print c



def add_salary():
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open('/home/frappe/frappe-bench/apps/client/client/sal.csv', "r") as infile:  
        rows = read_csv_content(infile.read())
        for index, row in enumerate(rows):
            if row[0]:
                query = frappe.db.sql("select name, employee_name, date_of_joining, status from `tabEmployee` where civil_id_no='{0}'".format(row[1]), as_dict=1)
                if query:
                    deductions = []
                    earnings = []
                    comps = ["الراتب الاساسي", "بدل السكن", "بدل الموصلات", "بدل الهاتف", "بدل اضافي"]
                    idx = 1
                    for c, i in zip(comps, range(2,7)):
                        if row[i]:
                            comp={ "doctype": "Salary Detail", "salary_component": c, "parenttype": "Salary Structure", "parentfield": "earnings", "formula": row[i], "idx": idx }
                            idx += 1
                            earnings.append(comp)


                if query[0].status == "Active":
                    print query[0].name
                    print row[2]
                    ss = frappe.new_doc("Salary Structure")
                    ss.update(
                        {
                        "doctype": "Salary Structure",
                        "name": query[0].name + "-SS",
                        "owner": "Administrator",
                        "from_date":query[0].date_of_joining,
                        "company": "Tadweeer",
                        "is_active": "Yes",
                        "payment_account": "40000000 - Expenses - المصاريف - T",
                        "employees": [
                                      {
                                        "doctype": "Salary Structure Employee",
                                        "parenttype": "Salary Structure",
                                        "base": row[6],
                                        "variable": 0,
                                        "from_date":query[0].date_of_joining,
                                        "employee": query[0].name,
                                        "docstatus": 0,
                                        "employee_name": query[0].employee_name,
                                        "parentfield": "employees"
                                      }
                        ],
                        "earnings": earnings,
                        "deductions": deductions,
                        "hour_rate": 0, 
                        "salary_slip_based_on_timesheet": 0
                     }
                        )
                    ss.insert()
                    




def add_emp():
    import sys
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    # print "Importing " + path
    with open('/home/frappe/frappe-bench/apps/client/client/emp.csv', "r") as infile:
        rows = read_csv_content(infile.read())

        cc = 0
        for index, row in enumerate(rows):
            print index

            frappe.get_doc({
                "doctype": "Employee",
                "employee_name_english": row[1],
                "employee_name": row[2],
                "designation": row[3],
                "civil_id_no": row[5],
                "emp_nationality": row[6],
                "date_of_joining": row[7],
                "date_of_birth": row[8],
                "department": row[9],
                "branch": row[10],
                "user_id": row[11],
                "work_days": row[12],
                "naming_series": "EMP",
                "gender": "ذكر"
            }).insert(ignore_permissions=True)

            
        print cc



def add_usres_email():
    import sys
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    # print "Importing " + path
    with open('/home/frappe/frappe-bench/apps/client/client/emp.csv', "r") as infile:
        rows = read_csv_content(infile.read())

        cc = 0
        for index, row in enumerate(rows):

            cc += 1
            string = str(row[1])
            tt = string.split()
            if row[11]:
                print tt[0]+'.'+tt[-1]


                frappe.get_doc({
                    "doctype": "User",
                    "user_type": 'System User',
                    "email": row[11],
                    "first_name": tt[0],
                    "last_name": tt[-1],
                    "language": "ar",
                    "civil_id_no":row[9],
                    "username": tt[0]+'.'+tt[-1],
                    "new_password": 123,
                    "send_welcome_email": 0
                }).insert(ignore_permissions=True)

                _update_password(row[11], row[5])

            
        print cc



def add_translation( ignore_links=False, overwrite=False, submit=False, pre_process=None, no_email=True):
    import sys
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open('/home/frappe/frappe-bench/apps/client/Translation.csv', "r") as infile:
        rows = read_csv_content(infile.read())
        for index, row in enumerate(rows):
            if not frappe.db.exists("Translation", {"source_name": row[0]}) and (row[0] is not None):
                print index,'---',row[0]
                frappe.get_doc({
                        "doctype":"Translation",
                        "language": 'ar',
                        "source_name": row[0],
                        "target_name": row[1]
                    }).insert(ignore_permissions=True)
            else:
                try:
                    frappe.db.sql("""update `tabTranslation` set target_name="{0}" where source_name="{1}" """.format(row[1],row[0]))
                    print row[0]
                except: 
                    pass
                

def add_reports_to():
    import sys
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    # print "Importing " + path
    with open('/home/frappe/frappe-bench/apps/client/emps.csv', "r") as infile:
        rows = read_csv_content(infile.read())

        cc = 0
        names = []
        result_manager = frappe.db.sql(
                 "select name,employee_name,Designation from tabEmployee")
        print result_manager[1][0]
        for index, row in enumerate(rows):
            print row[3]
            for i in result_manager:
                if i[2] == row[3]:
                    print "adding......"
                    emp_name = frappe.db.sql("select name from tabEmployee where employee_name='{0}'".format(row[1]))
                    if emp_name:
                        print emp_name[0][0]
                        doc_emp = frappe.get_doc('Employee',emp_name[0][0])
                        doc_emp.reports_to = i[0]
                        doc_emp.save(ignore_permissions=True)






def add_usr_id_to_employee():
    import sys
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    # print "Importing " + path
    # with open('/home/frappe/frappe-bench/apps/client/emps.csv', "r") as infile:
    #     rows = read_csv_content(infile.read())

    #     result_user = frappe.db.sql(
    #             "select name from tabUser where civil_id_no='{0}'".format(row[9]))
    result_user = frappe.db.sql(
                 "select email,civil_id_no from tabUser")
    # print result_user[1][1]
    for i in result_user:
        emp_name = frappe.db.sql("select name from tabEmployee where civil_id_no='{0}'".format(i[1]))
        if emp_name:
            doc_emp = frappe.get_doc('Employee',emp_name[0][0])
            doc_emp.user_id = i[0]
            print i[0]
            doc_emp.save(ignore_permissions=True)


def add_usr():
    import sys
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    # print "Importing " + path
    with open('/home/frappe/frappe-bench/apps/client/emps.csv', "r") as infile:
        rows = read_csv_content(infile.read())

        cc = 0
        names = []
        for index, row in enumerate(rows):

            result = frappe.db.sql(
                "select name from tabEmployee where civil_id_no='{0}'".format(row[9]))
            
            print row[0]
            cc += 1
            string = str(row[0])
            tt = string.split()
        #    rr=frappe.db.sql("select name from tabUser where email='{0}'".format(row[3]))

        #    if rr:
        #        pass
        #    else:
            print cc
            name = tt[0] + "." + tt[-1]+"@tadweer.sa"
            if row[15] != None:
                name = row[15]

            print name
            print "***************************"
            middle_name = ""
            if len(tt)>2 and tt[1] != "-":
                middle_name = tt[1]
                if len(tt)>3 and tt[2] != "-":
                    middle_name = tt[1]+ " " + tt[2]
            if name in names:
                if len(tt)> 2:
                    name = tt[0] +"." + tt[1]+"@tadweer.sa"
                else:
                    name = tt[0] + "." + tt[-1]+"_2"+"@tadweer.sa"
            frappe.get_doc({
                "doctype": "User",
                "user_type": 'System User',
                "email": name,
                "first_name": tt[0],
                "last_name": tt[-1],
                "middle_name": middle_name,
                "language": "ar",
                "civil_id_no":row[9],
                "username": name.split("@")[0],
                "new_password": 123,
                "send_welcome_email": 0
            }).insert(ignore_permissions=True)
            names.append(name)
        if result:
            frappe.db.sql(
                "update `tabEmployee` set user_id='{0}' where civil_id='{1}'".format(row[3], row[2]))
            print "h"

        print cc


def timee():

    # time= frappe.db.sql("select time from `tabLeave App` ")
    time = frappe.db.sql("select time from `tabLeave App` ")
    # print len(time)
    for i in time:
        print i[0]


def tst():
    #mm =date_diff('2018-04-23', '2018-03-20')
    date1 = datetime.date(2018, 9, 25)
    date2 = datetime.date(2018, 10, 8)
    day = datetime.timedelta(days=1)

    while date1 <= date2:
        print date1.strftime('%Y.%m.%d')
        date1 = date1 + day

    for d in daterange(date2, date1):
        print d.strftime('%Y.%m.%d')


def balance():
    t = frappe.db.sql(
        "select total from `tabLeave App` where employee='EMP/0003' ")[0]
    print t[0]


# def val():
#     to_date =frappe.db.sql("select to_date from `tabLeave App` where employee='EMP/0003' ")[0][0]
#     from_date = frappe.db.sql("select from_date from `tabLeave App` where employee='EMP/0003' ")[0][0]
#     for i in daterange(from_date):
#         print i


def num():

    to_date = frappe.db.sql(
        "select to_date from `tabLeave App` where employee='EMP/0003' ")[0][0]
    from_date = frappe.db.sql(
        "select from_date from `tabLeave App` where employee='EMP/0003' ")[0][0]
    day_count = (to_date - from_date).days + 1

    # m =datetime.datetime.today().strftime('%Y-%m-%d')
    # for single_date in (from_date + timedelta(n) for n in range(day_count)):
    #     print single_date
    #     if str(single_date) >= '2018-02-14' and str(single_date)<= '2018-02-20' :
    #         print "not alllowe"
    #     else:
    #         print 'allow'

    # if str(from_date) >= m or m <= str(to_date):
    #     print ('no')
    #     print m

    # else:
    #     print ('allow')

    # if m == day_count :
    #     print ('not allow')
    # else :
    #     print single_date

    #print single_date


def add_items():
    import sys
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/client/client/item1.csv", "r") as infile:
        rows = read_csv_content(infile.read())
        c = 0

        for index, row in enumerate(rows):
            print index,row[0]
            frappe.get_doc({
                "doctype": "Item",
                "item_group": row[0],
                "subgroup_1": row[1],
                "subgroup_2": row[2],
                "item_name": row[3]+'-item',
                "item_code": row[3]+'-item',
                "stock_uom": 'kg',
                "disabled": 1,
                "is_stock_item": 1,
                "standard_rate": row[4],
                "is_fixed_asset": 0,
                "is_purchase_item": 1,
                "is_sales_item": 1

            }).insert(ignore_permissions=True)

    print c


def make_salary_structure():
    import sys
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/client/emps.csv", "r") as infile:
        rows = read_csv_content(infile.read())
        c = 0

        for index, row in enumerate(rows):
            ss_doc = frappe.new_doc("Salary Structure")
            # emp_des = frappe.get_value(
            #     "Employee", filters={"civil_id_no": row[9]}, fieldname="Designation")
            designations = frappe.get_list("Designation", fields=['name'])
            for des in designations:
                des_emps = frappe.get_list(
                    "Employee", filters={"designation": row[2]}, fields=["name"])
                print(des_emps)
                # frappe.new_doc("Salary Structure")

            # emp_des = frappe.get_list("Employee", fields = ['designation', 'name'])

            # for single_des in emp_des:
            #     if fingle_des != "EMP/0001":

            #     print(single_des)
            # emp_des = frappe.get_value()
            #     "Employee", filters={"civil_id_no": row[9]}, fieldname="Designation")
            # print(emp_des)

            # ss_doc.name = emp_des


def add_items_group():
    import sys
    from frappe.utils.csvutils import read_csv_content
    from frappe.core.doctype.data_import.importer import upload
    with open("/home/frappe/frappe-bench/apps/client/client/Item.csv", "r") as infile:
        rows = read_csv_content(infile.read())
        c = 0

        for index, row in enumerate(rows):

            frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": 'item - '+row[2],
                "parent_item_group": row[1],
                "is_group": 0

            }).insert(ignore_permissions=True)

    print c
