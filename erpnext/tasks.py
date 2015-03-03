# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
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
