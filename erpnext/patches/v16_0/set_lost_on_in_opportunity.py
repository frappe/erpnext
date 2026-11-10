import json

import frappe
from frappe.query_builder.functions import Date
from frappe.translate import get_all_translations
from frappe.utils import create_batch, getdate

BATCH_SIZE = 500


def execute():
	"""Fill Lost On for lost opportunities from their latest status change, when it is a move to Lost.

	Status changes come from the Version log and from the status label comments. If the latest one is
	not a move to Lost (or there is none), fall back to the last modification date."""
	opportunity = frappe.qb.DocType("Opportunity")
	pending = (opportunity.status == "Lost") & opportunity.lost_on.isnull()

	names = frappe.qb.from_(opportunity).select(opportunity.name).where(pending).run(pluck=True)
	status_labels = get_status_labels() if names else {}
	for batch in create_batch(names, BATCH_SIZE):
		set_lost_on(get_lost_dates(batch, status_labels))

	frappe.qb.update(opportunity).set(opportunity.lost_on, Date(opportunity.modified)).where(pending).run()


def set_lost_on(lost_dates: dict) -> None:
	opportunity = frappe.qb.DocType("Opportunity")
	for name, lost_on in lost_dates.items():
		frappe.qb.update(opportunity).set(opportunity.lost_on, lost_on).where(opportunity.name == name).run()


def get_lost_dates(names: list[str], status_labels: dict[str, str]) -> dict:
	events = get_version_events(names) + get_comment_events(names, status_labels)
	latest_events = {}
	for name, creation, status in sorted(events, key=lambda event: event[1]):
		latest_events[name] = (creation, status)

	return {name: getdate(creation) for name, (creation, status) in latest_events.items() if status == "Lost"}


def get_version_events(names: list[str]) -> list[tuple]:
	version = frappe.qb.DocType("Version")
	versions = (
		frappe.qb.from_(version)
		.select(version.docname, version.data, version.creation)
		.where(
			(version.ref_doctype == "Opportunity")
			& version.docname.isin(names)
			& version.data.like('%"status"%')
		)
	).run(as_dict=True)

	events = [(row.docname, row.creation, get_new_status(row.data)) for row in versions]
	return [event for event in events if event[2]]


def get_new_status(data: str) -> str | None:
	try:
		changed = json.loads(data).get("changed") or []
	except (TypeError, ValueError):
		return None
	statuses = [row[2] for row in changed if len(row) == 3 and row[0] == "status"]
	return statuses[-1] if statuses else None


def get_comment_events(names: list[str], status_labels: dict[str, str]) -> list[tuple]:
	"""Status changes made by `set_status` add a label comment with the status, translated for the user."""
	comment = frappe.qb.DocType("Comment")
	comments = (
		frappe.qb.from_(comment)
		.select(comment.reference_name, comment.creation, comment.content)
		.where(
			(comment.comment_type == "Label")
			& (comment.reference_doctype == "Opportunity")
			& comment.reference_name.isin(names)
			& comment.content.isin(list(status_labels))
		)
	).run(as_dict=True)

	return [(row.reference_name, row.creation, status_labels[row.content]) for row in comments]


def get_status_labels() -> dict[str, str]:
	"""Map each status label, in English and in every language in use, to its status."""
	statuses = frappe.get_meta("Opportunity").get_field("status").options.split("\n")
	labels = {}
	for language in get_languages_in_use():
		translations = get_all_translations(language)
		labels.update({translations.get(status, status): status for status in statuses})

	labels.update({status: status for status in statuses})
	return labels


def get_languages_in_use() -> set[str]:
	user = frappe.qb.DocType("User")
	languages = set(
		frappe.qb.from_(user)
		.select(user.language)
		.distinct()
		.where(user.language.isnotnull())
		.run(pluck=True)
	)
	languages.add(frappe.db.get_single_value("System Settings", "language"))
	return languages
