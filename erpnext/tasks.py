# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.celery_app import celery_task, task_logger

@celery_task()
def send_newsletter(site, newsletter, event):
	# hack! pass event="bulk_long" to queue in longjob queue
	try:
		frappe.connect(site=site)
		doc = frappe.get_doc("Newsletter", newsletter)
		doc.send_bulk()

	except:
		frappe.db.rollback()
		task_logger.warn(frappe.get_traceback())

		# wasn't able to send emails :(
		doc.db_set("email_sent", 0)
		frappe.db.commit()

		raise

	else:
		frappe.db.commit()

	finally:
		frappe.destroy()

@celery_task()
def notify_fiscal_year_end():
	for d in frappe.db.sql("select name,year,year_end_date from `tabFiscal Year` where year_end_date =(current_date + 7)"):
		msg = "Your fiscal year named "+d.name+" is about to end on "+d.year_end_date+".Please create a new Fiscal Year."
		from frappe.email import sendmail, get_system_managers
		recipient_list = get_system_managers()
		sendmail(recipients=recipient_list, msg=msg, subject="Your Fiscal Year is about to end.")