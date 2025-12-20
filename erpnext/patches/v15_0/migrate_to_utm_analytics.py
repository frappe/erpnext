import click
import frappe
from frappe.query_builder.functions import Coalesce

from erpnext.setup.install import create_marketgin_campagin_custom_fields


def execute():
	"""
	Remove Lead Source doctype and use UTM Source Instead
	Ensure that for each Campaign, a UTM Campaign is also set
	"""
	if not frappe.db.exists("DocType", "Lead Source") or not frappe.db.exists("DocType", "UTM Source"):
		return

	ls = frappe.qb.DocType("Lead Source")
	ms = frappe.qb.DocType("UTM Source")

	# Fetch all Lead Sources
	if lead_sources := frappe.qb.from_(ls).select(ls.source_name, ls.details).run(as_dict=True):
		# Prepare the insert query with IGNORE
		insert_query = frappe.qb.into(ms).ignore().columns(ms.name, ms.description)

		# Add values for each Lead Source
		for source in lead_sources:
			insert_query = insert_query.insert(source.source_name, Coalesce(source.details, ""))

		# Execute the insert query
		insert_query.run()

	frappe.delete_doc("DocType", "Lead Source", ignore_missing=True)

	campaign = frappe.qb.DocType("Campaign")
	create_marketgin_campagin_custom_fields()
	marketing_campaign = frappe.qb.DocType("UTM Campaign")

	# Fetch all Campaigns
	if campaigns := (
		frappe.qb.from_(campaign).select(campaign.campaign_name, campaign.description).run(as_dict=True)
	):
		# Prepare the insert query with IGNORE
		insert_query = (
			frappe.qb.into(marketing_campaign)
			.ignore()
			.columns(
				marketing_campaign.name,
				marketing_campaign.campaign_description,
				marketing_campaign.crm_campaign,
			)
		)

		# Add values for each Campaign
		for camp in campaigns:
			insert_query = insert_query.insert(
				camp.campaign_name, Coalesce(camp.description, ""), camp.campaign_name
			)

		# Execute the insert query
		insert_query.run()

	click.secho(
		f"Inserted {len(lead_sources)} Lead Sources into UTM Sources and deleted Lead Source.\n"
		f"Inserted {len(campaigns)} Campaigns into UTM Campaigns.\n"
		"You can also make use of the new UTM Medium for analytics, now.",
		fg="green",
	)
