import json

import frappe
from frappe.query_builder.functions import Date
from frappe.translate import get_all_translations
from frappe.utils import create_batch, getdate

BATCH_SIZE = 500


def execute():
	"""Fill Lost On for lost opportunities from the Version log, then from the "Lost" status comment,
	else from the last modification."""
	opportunity = frappe.qb.DocType("Opportunity")
	pending = (opportunity.status == "Lost") & opportunity.lost_on.isnull()

	for get_lost_dates in (get_lost_dates_from_versions, get_lost_dates_from_comments):
		names = frappe.qb.from_(opportunity).select(opportunity.name).where(pending).run(pluck=True)
		for batch in create_batch(names, BATCH_SIZE):
			set_lost_on(get_lost_dates(batch))

	frappe.qb.update(opportunity).set(opportunity.lost_on, Date(opportunity.modified)).where(pending).run()


def set_lost_on(lost_dates: dict) -> None:
	opportunity = frappe.qb.DocType("Opportunity")
	for name, lost_on in lost_dates.items():
		frappe.qb.update(opportunity).set(opportunity.lost_on, lost_on).where(opportunity.name == name).run()


def get_lost_dates_from_versions(names: list[str]) -> dict:
	version = frappe.qb.DocType("Version")
	versions = (
		frappe.qb.from_(version)
		.select(version.docname, version.data, version.creation)
		.where(
			(version.ref_doctype == "Opportunity")
			& version.docname.isin(names)
			& version.data.like('%"status"%')
		)
		.orderby(version.creation)
	).run(as_dict=True)

	return {row.docname: getdate(row.creation) for row in versions if is_marked_lost(row.data)}


def is_marked_lost(data: str) -> bool:
	try:
		changed = json.loads(data).get("changed") or []
	except (TypeError, ValueError):
		return False
	return any(row[0] == "status" and row[2] == "Lost" for row in changed if len(row) == 3)


def get_lost_dates_from_comments(names: list[str]) -> dict:
	"""Status changes made from a Quotation add a "Lost" label comment, translated for the user."""
	comment = frappe.qb.DocType("Comment")
	comments = (
		frappe.qb.from_(comment)
		.select(comment.reference_name, comment.creation)
		.where(
			(comment.comment_type == "Label")
			& (comment.reference_doctype == "Opportunity")
			& comment.reference_name.isin(names)
			& comment.content.isin(get_lost_labels())
		)
		.orderby(comment.creation)
	).run(as_dict=True)

	return {row.reference_name: getdate(row.creation) for row in comments}


def get_lost_labels() -> list[str]:
	user = frappe.qb.DocType("User")
	languages = set(
		frappe.qb.from_(user)
		.select(user.language)
		.distinct()
		.where(user.language.isnotnull())
		.run(pluck=True)
	)
	languages.add(frappe.db.get_single_value("System Settings", "language"))
	return list({"Lost", *(get_all_translations(language).get("Lost", "Lost") for language in languages)})
