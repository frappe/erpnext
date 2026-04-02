import frappe

from erpnext.manufacturing.page.mixer_station.mixer_station import get_mixer_state


@frappe.whitelist()
def delete_job_cards(production_plan, reason):
	is_deleted = False
	deleted_count = 0

	mixing_work_orders = frappe.get_all(
		"Work Order", filters={"production_plan": production_plan, "production_item": ["like", "%Mixing%"]}
	)

	mixing_job_cards = frappe.get_all(
		"Job Card",
		fields=["name", "status"],
		filters={"work_order": ["in", [wo.name for wo in mixing_work_orders]]},
	)

	for job_card in mixing_job_cards:
		if job_card.status == "Open":
			frappe.delete_doc("Job Card", job_card.name)
			is_deleted = True
			deleted_count += 1

	if not is_deleted:
		frappe.throw("No Open Job Cards found to delete")

	frappe.db.set_value(
		"Production Plan",
		production_plan,
		{"reason_for_deletion_of_job_cards": reason, "deleted_job_card_count": deleted_count},
	)

	message = f"""{deleted_count} job card{"s" if deleted_count > 1 else ""} were deleted from this production plan with the reason: "{reason}" """

	doc = frappe.get_doc("Production Plan", production_plan)
	doc.add_comment("Comment", message)

	return {"status": "success", "is_deleted": is_deleted, "deleted_count": deleted_count, "reason": reason}
