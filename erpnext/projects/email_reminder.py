import frappe, datetime, dateutil
from frappe.utils import cint

@frappe.whitelist()
def hourly_reminder():
    msg = "How is your project? Please update your project"
    data = []
    reminder = frappe.db.sql("""SELECT `tabProject User`.user FROM `tabProject User` INNER JOIN `tabProject` ON `tabProject`.project_name = `tabProject User`.parent WHERE `tabProject`.frequency = "Hourly";""")
    for x in reminder:
        emails = x[0]
        data.append(emails)

    print("===================")
    send_emails(data)


def send_emails(data):
    emails = data
    print (emails)
    from frappe.desk.page.chat.chat import post
    for email in emails:
        print email
        post(**{"txt": "hehehe", "contact": email, "subject": "Test rani", "notify": 1})
