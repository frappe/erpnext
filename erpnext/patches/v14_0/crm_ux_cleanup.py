import frappe
from frappe.model.utils.rename_field import rename_field
from frappe.utils import add_months, cstr, today


def execute():
	for doctype in ("CRM Note", "Lead", "Opportunity", "Prospect", "Prospect Lead"):
		frappe.reload_doc("crm", "doctype", doctype)

	try:
		rename_field("Lead", "designation", "job_title")
		rename_field("Opportunity", "converted_by", "opportunity_owner")

		frappe.db.sql(
			"""
			update `tabProspect Lead`
			set parentfield='leads'
			where parentfield='partner_lead'
		"""
		)
	except Exception as e:
		if e.args[0] != 1054:
			raise

	add_calendar_event_for_leads()
	add_calendar_event_for_opportunities()


def add_calendar_event_for_leads():
	# create events based on next contact date
	leads = frappe.db.sql(
		"""
		select name, contact_date, contact_by, ends_on, lead_name, lead_owner
		from tabLead
		where contact_date >= %s
	""",
		add_months(today(), -1),
		as_dict=1,
	)

	for d in leads:
		event = frappe.get_doc(
			{
				"doctype": "Event",
				"owner": d.lead_owner,
				"subject": ("Contact " + cstr(d.lead_name)),
				"description": (
					("Contact " + cstr(d.lead_name)) + (("<br>By: " + cstr(d.contact_by)) if d.contact_by else "")
				),
				"starts_on": d.contact_date,
				"ends_on": d.ends_on,
				"event_type": "Private",
			}
		)

		event.append("event_participants", {"reference_doctype": "Lead", "reference_docname": d.name})

		event.insert(ignore_permissions=True)


def add_calendar_event_for_opportunities():
	# create events based on next contact date
	opportunities = frappe.db.sql(
		"""
		select name, contact_date, contact_by, to_discuss,
			party_name, opportunity_owner, contact_person
		from tabOpportunity
		where contact_date >= %s
	""",
		add_months(today(), -1),
		as_dict=1,
	)

	for d in opportunities:
		event = frappe.get_doc(
			{
				"doctype": "Event",
				"owner": d.opportunity_owner,
				"subject": ("Contact " + cstr(d.contact_person or d.party_name)),
				"description": (
					("Contact " + cstr(d.contact_person or d.party_name))
					+ (("<br>By: " + cstr(d.contact_by)) if d.contact_by else "")
					+ (("<br>Agenda: " + cstr(d.to_discuss)) if d.to_discuss else "")
				),
				"starts_on": d.contact_date,
				"event_type": "Private",
			}
		)

		event.append(
			"event_participants", {"reference_doctype": "Opportunity", "reference_docname": d.name}
		)

		event.insert(ignore_permissions=True)
