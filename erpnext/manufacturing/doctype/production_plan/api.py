import frappe


@frappe.whitelist(allow_guest=True)
def delete_job_cards(production_plan, reason, delete_all_job_cards, production_line=None, item_code=None):
	mixing_work_orders = get_mixing_work_orders(production_plan, delete_all_job_cards, production_line, item_code)
	deleted_count_limit = get_open_mixing_job_cards_count(mixing_work_orders)

	if not deleted_count_limit:
		frappe.throw("No Open Mixing Job Cards found to delete")

	target_work_orders = get_target_work_orders(production_plan, production_line, item_code)
	job_cards_to_delete = get_open_job_cards_for_deletion(target_work_orders, deleted_count_limit)

	if not job_cards_to_delete:
		frappe.throw("No Open Job Cards found to delete")

	for job_card in job_cards_to_delete:
		frappe.delete_doc("Job Card", job_card.name)

	if production_line:
		line_name = frappe.db.get_value("Production Line", production_line, "line_name")
	else:
		line_name = "All Production Lines"
	update_production_plan_and_log_comment(production_plan, reason, len(job_cards_to_delete), line_name, item_code)

	return {
		"status": "success",
		"is_deleted": True,
		"deleted_count": len(job_cards_to_delete),
		"reason": reason,
	}


def get_mixing_work_orders(production_plan, delete_all_job_cards, production_line, item_code):
	filters = {
		"production_plan": production_plan,
		"wip_warehouse": ["like", "%Mixing%"],
	}

	if delete_all_job_cards != 1:
		if production_line:
			filters["production_line"] = production_line
		if item_code:
			filters["production_item"] = ["like", f"%{item_code}%"]

	return frappe.get_all("Work Order", filters=filters)


def get_open_mixing_job_cards_count(work_orders):
	if not work_orders:
		return 0

	mixing_job_cards = frappe.get_list(
		"Job Card",
		filters={
			"work_order": ["in", [wo.name for wo in work_orders]],
			"operation": ["like", "%Mixing%"],
			"status": "Open",
		},
	)
	return len(mixing_job_cards)


def get_target_work_orders(production_plan, production_line, item_code):
	filters = {"production_plan": production_plan}
	if item_code:
		filters["production_item"] = ["like", f"%{item_code}%"]
	if production_line:
		filters["production_line"] = production_line

	return frappe.get_all("Work Order", fields=["name"], filters=filters)


def get_open_job_cards_for_deletion(work_orders, limit_per_operation):
	all_open_job_cards = []
	for wo in work_orders:
		# Get distinct operations for this work order that have open job cards
		operations = frappe.get_all(
			"Job Card", filters={"work_order": wo.name, "status": "Open"}, fields=["operation"], distinct=True
		)
		for op_row in operations:
			job_cards = frappe.get_all(
				"Job Card",
				fields=["name"],
				filters={
					"work_order": wo.name,
					"operation": op_row.operation,
					"status": "Open",
				},
				limit=limit_per_operation,
			)
			all_open_job_cards.extend(job_cards)
	return all_open_job_cards


def update_production_plan_and_log_comment(production_plan, reason, deleted_count, line_name, item_code):
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
