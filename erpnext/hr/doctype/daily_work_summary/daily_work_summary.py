# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from email_reply_parser import EmailReplyParser
from frappe import _
from frappe.model.document import Document
from frappe.utils import global_date_format


class DailyWorkSummary(Document):
	def send_mails(self, dws_group, emails):
		"""Send emails to get daily work summary to all users \
			in selected daily work summary group"""
		incoming_email_account = frappe.db.get_value(
			"Email Account", dict(enable_incoming=1, default_incoming=1), "email_id"
		)

		self.db_set("email_sent_to", "\n".join(emails))
		frappe.sendmail(
			recipients=emails,
			message=dws_group.message,
			subject=dws_group.subject,
			reference_doctype=self.doctype,
			reference_name=self.name,
			reply_to=incoming_email_account,
		)

	def send_summary(self):
		"""Send summary of all replies. Called at midnight"""
		args = self.get_message_details()
		emails = get_user_emails_from_group(self.daily_work_summary_group)
		frappe.sendmail(
			recipients=emails,
			template="daily_work_summary",
			args=args,
			subject=_(self.daily_work_summary_group),
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

		self.db_set("status", "Sent")

	def get_message_details(self):
		"""Return args for template"""
		dws_group = frappe.get_doc("Daily Work Summary Group", self.daily_work_summary_group)

		replies = frappe.get_all(
			"Communication",
			fields=["content", "text_content", "sender"],
			filters=dict(
				reference_doctype=self.doctype,
				reference_name=self.name,
				communication_type="Communication",
				sent_or_received="Received",
			),
			order_by="creation asc",
		)

		did_not_reply = self.email_sent_to.split()

		for d in replies:
			user = frappe.db.get_values(
				"User", {"email": d.sender}, ["full_name", "user_image"], as_dict=True
			)

			d.sender_name = user[0].full_name if user else d.sender
			d.image = user[0].image if user and user[0].image else None

			original_image = d.image
			# make thumbnail image
			try:
				if original_image:
					file_name = frappe.get_list("File", {"file_url": original_image})

					if file_name:
						file_name = file_name[0].name
						file_doc = frappe.get_doc("File", file_name)
						thumbnail_image = file_doc.make_thumbnail(
							set_as_thumbnail=False, width=100, height=100, crop=True
						)
						d.image = thumbnail_image
			except Exception:
				d.image = original_image

			if d.sender in did_not_reply:
				did_not_reply.remove(d.sender)
			if d.text_content:
				d.content = frappe.utils.md_to_html(EmailReplyParser.parse_reply(d.text_content))

		did_not_reply = [
			(frappe.db.get_value("User", {"email": email}, "full_name") or email) for email in did_not_reply
		]

		return dict(
			replies=replies,
			original_message=dws_group.message,
			title=_("Work Summary for {0}").format(global_date_format(self.creation)),
			did_not_reply=", ".join(did_not_reply) or "",
			did_not_reply_title=_("No replies from"),
		)


def get_user_emails_from_group(group):
	"""Returns list of email of enabled users from the given group

	:param group: Daily Work Summary Group `name`"""
	group_doc = group
	if isinstance(group_doc, str):
		group_doc = frappe.get_doc("Daily Work Summary Group", group)

	emails = get_users_email(group_doc)

	return emails


def get_users_email(doc):
	return [d.email for d in doc.users if frappe.db.get_value("User", d.user, "enabled")]
