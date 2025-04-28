# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
<<<<<<< HEAD
from frappe.utils import create_batch, getdate
=======
from frappe.utils import getdate
>>>>>>> 7c4cf3e834 (Favicon.svg)

from erpnext.accounts.doctype.subscription.subscription import DateTimeLikeObject, process_all


class ProcessSubscription(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		posting_date: DF.Date
		subscription: DF.Link | None
	# end: auto-generated types

	def on_submit(self):
<<<<<<< HEAD
		self.process_all_subscription()

	def process_all_subscription(self):
		filters = {"status": ("!=", "Cancelled")}

		if self.subscription:
			filters["name"] = self.subscription

		subscriptions = frappe.get_all("Subscription", filters, pluck="name")

		for subscription in create_batch(subscriptions, 500):
			frappe.enqueue(
				method="erpnext.accounts.doctype.subscription.subscription.process_all",
				queue="long",
				subscription=subscription,
				posting_date=self.posting_date,
			)
=======
		process_all(subscription=self.subscription, posting_date=self.posting_date)
>>>>>>> 7c4cf3e834 (Favicon.svg)


def create_subscription_process(
	subscription: str | None = None, posting_date: DateTimeLikeObject | None = None
):
	"""Create a new Process Subscription document"""
	doc = frappe.new_doc("Process Subscription")
	doc.subscription = subscription
	doc.posting_date = getdate(posting_date)
	doc.submit()
