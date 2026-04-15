import frappe


@frappe.whitelist(allow_guest=True)
def delete_job_cards(production_plan, reason, delete_all_job_cards, production_line=None, item_code=None):
	is_deleted = False
	deleted_count = 0
	line_name = None

	filters = {
		"production_plan": production_plan,
		"wip_warehouse": ["like", "%Mixing%"],
	}

	if delete_all_job_cards != 1:
		if production_line:
			filters["production_line"] = production_line
			line_name = frappe.db.get_value("Production Line", production_line, "line_name")
		if item_code:
			filters["production_item"] = ["like", f"%{item_code}%"]

	mixing_work_orders = frappe.get_all(
		"Work Order",
		filters=filters,
	)

	mixing_job_cards = frappe.get_all(
		"Job Card",
		fields=["name", "status"],
		filters={
			"work_order": ["in", [wo.name for wo in mixing_work_orders]],
			"operation": ["like", "%Mixing%"],
			"status": "Open",
		},
	)

	deleted_count = len(mixing_job_cards)

	for job_card in mixing_job_cards:
		frappe.delete_doc("Job Card", job_card.name)
		is_deleted = True

	if not is_deleted:
		frappe.throw("No Open Job Cards found to delete")

	frappe.db.set_value(
		"Production Plan",
		production_plan,
		{"reason_for_deletion_of_job_cards": reason, "deleted_job_card_count": deleted_count},
	)

	message = f"""{deleted_count} job card{"s" if deleted_count > 1 else ""} were deleted from this production plan from {line_name or "All Production Lines"} """
	if item_code:
		message += f"for item {item_code} "
	message += f"""with the reason: "{reason}" """

	doc = frappe.get_doc("Production Plan", production_plan)
	doc.add_comment("Comment", message)

	return {"status": "success", "is_deleted": is_deleted, "deleted_count": deleted_count, "reason": reason}
