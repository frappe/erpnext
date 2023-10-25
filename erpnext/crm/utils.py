import frappe
from frappe.desk.notifications import notify_mentions
from frappe.model.document import Document
from frappe.utils import cstr, now, today
from pypika import functions


def update_lead_phone_numbers(contact, method):
	if contact.phone_nos:
		contact_lead = contact.get_link_for("Lead")
		if contact_lead:
			phone = mobile_no = contact.phone_nos[0].phone

			if len(contact.phone_nos) > 1:
				# get the default phone number
				primary_phones = [
					phone_doc.phone for phone_doc in contact.phone_nos if phone_doc.is_primary_phone
				]
				if primary_phones:
					phone = primary_phones[0]

				# get the default mobile number
				primary_mobile_nos = [
					phone_doc.phone for phone_doc in contact.phone_nos if phone_doc.is_primary_mobile_no
				]
				if primary_mobile_nos:
					mobile_no = primary_mobile_nos[0]

			lead = frappe.get_doc("Lead", contact_lead)
			lead.db_set("phone", phone)
			lead.db_set("mobile_no", mobile_no)


def copy_comments(doctype, docname, doc):
	comments = frappe.db.get_values(
		"Comment",
		filters={"reference_doctype": doctype, "reference_name": docname, "comment_type": "Comment"},
		fieldname="*",
	)
	for comment in comments:
		comment = frappe.get_doc(comment.update({"doctype": "Comment"}))
		comment.name = None
		comment.reference_doctype = doc.doctype
		comment.reference_name = doc.name
		comment.insert()


def link_communications(doctype, docname, doc):
	communication_list = get_linked_communication_list(doctype, docname)

	for communication in communication_list:
		communication_doc = frappe.get_doc("Communication", communication)
		communication_doc.add_link(doc.doctype, doc.name, autosave=True)


def get_linked_communication_list(doctype, docname):
	communications = frappe.get_all(
		"Communication", filters={"reference_doctype": doctype, "reference_name": docname}, pluck="name"
	)
	communication_links = frappe.get_all(
		"Communication Link",
		{"link_doctype": doctype, "link_name": docname, "parent": ("not in", communications)},
		pluck="parent",
	)

	return communications + communication_links


def link_communications_with_prospect(communication, method):
	prospect = get_linked_prospect(communication.reference_doctype, communication.reference_name)

	if prospect:
		already_linked = any(
			[
				d.name
				for d in communication.get("timeline_links")
				if d.link_doctype == "Prospect" and d.link_name == prospect
			]
		)
		if not already_linked:
			row = communication.append("timeline_links")
			row.link_doctype = "Prospect"
			row.link_name = prospect
			row.db_update()


def get_linked_prospect(reference_doctype, reference_name):
	prospect = None
	if reference_doctype == "Lead":
		prospect = frappe.db.get_value("Prospect Lead", {"lead": reference_name}, "parent")

	elif reference_doctype == "Opportunity":
		opportunity_from, party_name = frappe.db.get_value(
			"Opportunity", reference_name, ["opportunity_from", "party_name"]
		)
		if opportunity_from == "Lead":
			prospect = frappe.db.get_value(
				"Prospect Opportunity", {"opportunity": reference_name}, "parent"
			)
		if opportunity_from == "Prospect":
			prospect = party_name

	return prospect


def link_events_with_prospect(event, method):
	if event.event_participants:
		ref_doctype = event.event_participants[0].reference_doctype
		ref_docname = event.event_participants[0].reference_docname
		prospect = get_linked_prospect(ref_doctype, ref_docname)
		if prospect:
			event.add_participant("Prospect", prospect)
			event.save()


def link_open_tasks(ref_doctype, ref_docname, doc):
	todos = get_open_todos(ref_doctype, ref_docname)

	for todo in todos:
		todo_doc = frappe.get_doc("ToDo", todo.name)
		todo_doc.reference_type = doc.doctype
		todo_doc.reference_name = doc.name
		todo_doc.save()


def link_open_events(ref_doctype, ref_docname, doc):
	events = get_open_events(ref_doctype, ref_docname)
	for event in events:
		event_doc = frappe.get_doc("Event", event.name)
		event_doc.add_participant(doc.doctype, doc.name)
		event_doc.save()


@frappe.whitelist()
def get_open_activities(ref_doctype, ref_docname):
	tasks = get_open_todos(ref_doctype, ref_docname)
	events = get_open_events(ref_doctype, ref_docname)

	return {"tasks": tasks, "events": events}


def get_open_todos(ref_doctype, ref_docname):
	return frappe.get_all(
		"ToDo",
		filters={"reference_type": ref_doctype, "reference_name": ref_docname, "status": "Open"},
		fields=[
			"name",
			"description",
			"allocated_to",
			"date",
		],
	)


def get_open_events(ref_doctype, ref_docname):
	event = frappe.qb.DocType("Event")
	event_link = frappe.qb.DocType("Event Participants")

	query = (
		frappe.qb.from_(event)
		.join(event_link)
		.on(event_link.parent == event.name)
		.select(
			event.name,
			event.subject,
			event.event_category,
			event.starts_on,
			event.ends_on,
			event.description,
		)
		.where(
			(event_link.reference_doctype == ref_doctype)
			& (event_link.reference_docname == ref_docname)
			& (event.status == "Open")
		)
	)
	data = query.run(as_dict=True)

	return data


def open_leads_opportunities_based_on_todays_event():
	event = frappe.qb.DocType("Event")
	event_link = frappe.qb.DocType("Event Participants")

	query = (
		frappe.qb.from_(event)
		.join(event_link)
		.on(event_link.parent == event.name)
		.select(event_link.reference_doctype, event_link.reference_docname)
		.where(
			(event_link.reference_doctype.isin(["Lead", "Opportunity"]))
			& (event.status == "Open")
			& (functions.Date(event.starts_on) == today())
		)
	)
	data = query.run(as_dict=True)

	for d in data:
		frappe.db.set_value(d.reference_doctype, d.reference_docname, "status", "Open")


class CRMNote(Document):
	@frappe.whitelist()
	def add_note(self, note):
		self.append("notes", {"note": note, "added_by": frappe.session.user, "added_on": now()})
		self.save()
		notify_mentions(self.doctype, self.name, note)

	@frappe.whitelist()
	def edit_note(self, note, row_id):
		for d in self.notes:
			if cstr(d.name) == row_id:
				d.note = note
				d.db_update()

	@frappe.whitelist()
	def delete_note(self, row_id):
		for d in self.notes:
			if cstr(d.name) == row_id:
				self.remove(d)
				break
		self.save()
