import json

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.manufacturing.doctype.bom.bom import BOM
from erpnext.manufacturing.doctype.job_card.job_card import (
	make_stock_entry as jc_make_stock_entry,
)
from erpnext.manufacturing.doctype.job_card.job_card import (
	make_time_log,
)
from erpnext.manufacturing.doctype.operation.api import _get_slab_template_from_bom, get_open_job_cards
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry as wo_make_stock_entry
from erpnext.setup.doctype.employee.api import get_current_user_context
from erpnext.setup.doctype.mahi_granites_settings.mahi_granites_settings import MahiGranitesSettings


@frappe.whitelist()
def check_distribution_status(production_line):
	distribution_cards = get_open_job_cards(
		process="Distribution",
		line=production_line,
		include_wip=True,
		include_material_transferred=True,
	)

	return {"busy": len(distribution_cards) > 0}


@frappe.whitelist()
def get_mixer_station_context():
	user_context = get_current_user_context()
	mahi_settings: MahiGranitesSettings = frappe.get_doc("Mahi Granites Settings")
	return {
		"current_user": user_context,
		"show_job_card_queue": mahi_settings.show_job_card_queue_to_mixer_operators,
	}


@frappe.whitelist()
def get_mixing_queue(production_line):
	"""Return open mixing job cards, filtering Completed cards to only those
	with sufficient qty to transfer (display_qty >= bom_qty)."""
	all_cards = get_open_job_cards(
		process="Mixing",
		line=production_line,
		include_wip=True,
		include_material_transferred=True,
	)

	result = []
	for card in all_cards:
		status = card.get("status")
		# Non-completed cards are always visible in the queue
		if status != "Completed":
			result.append(card)
			continue

		# For completed cards, check if there is still qty available to transfer
		try:
			state = get_mixer_state(card["name"])
			display_qty = flt(state.get("display_qty", 0), 3)
			bom_data = get_next_process_bom_qty(frappe.db.get_value("Job Card", card["name"], "work_order"))
			bom_qty = flt(bom_data.get("bom_qty", 0), 2)
			if display_qty >= bom_qty and bom_qty > 0:
				result.append(card)
		except Exception:
			# If we can't determine qty, include the card to be safe
			result.append(card)

	return result


@frappe.whitelist()
def get_mixer_state(job_card):
	if not job_card:
		return {}

	jc = frappe.get_doc("Job Card", job_card)
	wo = frappe.get_doc("Work Order", jc.work_order) if jc.work_order else None

	next_bom = get_next_process_bom_qty(jc.work_order)
	next_wo = next_bom.get("next_work_order")

	transferred_qty_to_next = 0
	if next_wo:
		transferred_qty_to_next = flt(
			frappe.db.sql(
				"""
				SELECT COALESCE(SUM(sle.actual_qty), 0)
				FROM `tabStock Ledger Entry` sle
				INNER JOIN `tabStock Entry` se ON sle.voucher_no = se.name
				WHERE se.work_order = %s
				AND sle.item_code = %s
				AND se.purpose = 'Material Transfer for Manufacture'
				AND sle.actual_qty > 0
				AND sle.is_cancelled = 0
			""",
				(next_wo, jc.production_item),
			)[0][0]
			or 0,
			3,
		)

	prepared_qty = wo.produced_qty if wo else jc.total_completed_qty
	display_qty = flt(prepared_qty - transferred_qty_to_next, 3)

	return {
		"status": jc.status,
		"docstatus": jc.docstatus,
		"mixer_materials_confirmed": jc.transferred_qty > 0,
		"mixer_started": 1 if jc.time_logs else 0,
		"mixer_start_time": jc.started_time,
		"mixer_finished": jc.current_time or 0,
		"job_card_submitted": jc.status == "Completed",
		"job_card_completed": jc.total_completed_qty > 0,
		"prepared_qty": prepared_qty,
		"stock_entry_name": wo.produced_qty > 0 and "MFG-SE-*" or "",
		"work_order_status": wo.get_status() if wo else "Draft",
		"additional_ingredients_added": jc.additional_ingredients_added,
		"mixer_number": jc.mixer_number,
		"transferred_qty_to_next": transferred_qty_to_next,
		"display_qty": display_qty,
		"transfer_complete": display_qty <= 0.001,
	}


@frappe.whitelist()
def get_mixer_ingredients(job_card):
	jc = frappe.get_doc("Job Card", job_card)
	if not jc.bom_no:
		frappe.throw(_("No BOM set on Job Card {0}").format(job_card))

	jc.reload()

	bom_doc = frappe.get_doc("BOM", jc.bom_no)
	bom_by_code = {row.item_code: row for row in bom_doc.items}
	ingredients = []
	for row in jc.items:
		bom_row = bom_by_code.get(row.item_code)
		if not bom_row:
			continue

		qty = flt(row.required_qty) or flt(bom_row.stock_qty)

		# qty = flt(row.stock_qty)
		ingredients.append(
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"stock_uom": row.stock_uom,
				"stock_uom_qty": qty,
				"additional_ingredients_added": jc.additional_ingredients_added,
				"jc_bom_uom": bom_doc.uom,
			}
		)

	return ingredients


@frappe.whitelist()
def confirm_and_start_mixing(job_card, ingredients, bom_uom):
	"""Create Stock Entry from mixer quantities and mark Job Card ready."""
	try:
		frappe.db.begin()
		ingredients = json.loads(ingredients)
		jc = frappe.get_doc("Job Card", job_card)

		qty_by_code = {ing["item_code"]: flt(ing["qty"]) for ing in ingredients}

		for row in jc.items:
			if row.item_code in qty_by_code:
				row.required_qty = qty_by_code[row.item_code]
				# row.additional_ingredients_added = added_by_code.get(row.item_code, 0)

		total_qty = 1
		if jc.for_quantity != 1 and bom_uom != "Nos":
			total_qty = sum(row.required_qty for row in jc.items if row.required_qty > 0)
			jc.for_quantity = total_qty
			jc.additional_ingredients_added = 1
			jc.save(ignore_permissions=True)

		se = jc_make_stock_entry(job_card)
		if not se.items:
			frappe.throw(_("No remaining quantity to transfer for Job Card {0}.").format(job_card))

		se.insert()
		se.submit()

		start_mixing(job_card)
		frappe.db.commit()
		return {
			"stock_entry": se.name,
			"total_for_quantity": total_qty,
			"additional_ingredients_added": jc.additional_ingredients_added,
			"status": jc.status,
			"mixer_started": jc.job_started,
			"mixer_start_time": jc.started_time,
			"current_time": jc.current_time,
		}
	except Exception as e:
		frappe.db.rollback()
		frappe.throw(f"Failed to confirm and start mixing: {e}")


# def confirm_materials(job_card, ingredients, bom_uom):
# 	"""Create Stock Entry from mixer quantities and mark Job Card ready."""
# 	ingredients = json.loads(ingredients)
# 	jc = frappe.get_doc("Job Card", job_card)

# 	qty_by_code = {ing["item_code"]: flt(ing["qty"]) for ing in ingredients}

# 	for row in jc.items:
# 		if row.item_code in qty_by_code:
# 			row.required_qty = qty_by_code[row.item_code]
# 			# row.additional_ingredients_added = added_by_code.get(row.item_code, 0)

# 	total_qty = 1
# 	if jc.for_quantity != 1 and bom_uom != "Nos":
# 		total_qty = sum(row.required_qty for row in jc.items if row.required_qty > 0)
# 		jc.for_quantity = total_qty
# 		jc.additional_ingredients_added = 1
# 		jc.save(ignore_permissions=True)

# 	se = jc_make_stock_entry(job_card)
# 	if not se.items:
# 		frappe.throw(_("No remaining quantity to transfer for Job Card {0}.").format(job_card))

# 	se.insert()
# 	se.submit()
# 	return {
# 		"stock_entry": se.name,
# 		"total_for_quantity": total_qty,
# 		"additional_ingredients_added": jc.additional_ingredients_added,
# 	}


def start_mixing(job_card):
	"""Start the Job Card when mixing starts."""
	jc = frappe.get_doc("Job Card", job_card)
	start_time = frappe.utils.now_datetime()
	args = {
		"job_card_id": jc.name,
		"start_time": start_time,
		"status": "Work In Progress",
	}

	make_time_log(args)
	jc.reload()
	jc.job_started = 1
	jc.save(ignore_permissions=True)
	return {
		"status": jc.status,
		"mixer_started": jc.job_started,
		"mixer_start_time": jc.started_time,
		"current_time": jc.current_time,
	}


@frappe.whitelist()
def finish_mixing(job_card, completed_qty):
	"""Complete the Job Card when mixing is finished."""
	jc = frappe.get_doc("Job Card", job_card)
	job_card_qty = flt(jc.for_quantity or 0, 3)
	args = {
		"job_card_id": jc.name,
		"complete_time": frappe.utils.now_datetime(),
		"completed_qty": job_card_qty,
		"status": "Completed",
	}

	make_time_log(args)
	jc.reload()
	jc.status = "Completed"
	jc.completed_qty = job_card_qty
	jc.job_started = 0
	if jc.docstatus == 0:
		jc.submit()
	else:
		jc.save(ignore_permissions=True)

	jc.reload()
	jc.db_set("status", "Completed")  # Direct DB update
	jc.reload()

	work_order = jc.work_order
	wo = frappe.get_doc("Work Order", work_order)

	se_doc = wo_make_stock_entry(work_order, "Manufacture", qty=job_card_qty)
	if isinstance(se_doc, dict):
		se = frappe.get_doc(se_doc)
	else:
		se = se_doc

	se.fg_completed_qty = job_card_qty
	se.for_quantity = job_card_qty
	fg_item = next((item for item in se.items if item.is_finished_item), None)
	if fg_item:
		fg_item.qty = job_card_qty
		fg_item.stock_qty = job_card_qty
	se.save()
	se.submit()

	wo.update_work_order_qty()
	wo.reload()
	wo_status = wo.get_status()
	next_bom_data = get_next_process_bom_qty(work_order)
	mixer_state = get_mixer_state(job_card)

	return {
		"status": wo_status,
		"work_order_status": wo_status,
		"work_order": work_order,
		"job_card_qty": job_card_qty,
		"produced_qty": wo.produced_qty,
		"total_qty": wo.qty,
		"stock_entry": se.name,
		"bom_qty": next_bom_data["bom_qty"],
		"next_work_order": next_bom_data["next_work_order"],
		"display_qty": mixer_state["display_qty"],
		"transfer_complete": mixer_state["transfer_complete"],
		"message": f"SE {se.name} ({job_card_qty} qty). WO: {wo_status}",
	}


@frappe.whitelist()
def quick_add_raw_materials(job_card, raw_material, qty):
	"""Dialog → Creates Doctype record + Stock Entry."""
	add_doc = frappe.new_doc("Add Raw Materials")
	add_doc.job_card = job_card
	add_doc.raw_material = raw_material
	add_doc.qty = float(qty)
	add_doc.insert()
	add_doc.submit()

	jc = frappe.get_doc("Job Card", job_card)
	target_row = next((row for row in jc.items if row.item_code == raw_material), None)
	if not target_row:
		frappe.throw(_("No Job Card Item matches <b>{0}</b>").format(raw_material))
	if not target_row.source_warehouse:
		frappe.throw(_("No Source Warehouse for {0}").format(raw_material))

	target_row.required_qty += float(qty)

	total_qty = sum(row.required_qty for row in jc.items if row.required_qty > 0)
	jc.for_quantity = total_qty

	jc.flags.ignore_validate = True
	jc.save(ignore_permissions=True)

	se = frappe.new_doc("Stock Entry")
	se.job_card = job_card
	se.work_order = jc.work_order
	se.purpose = "Material Transfer for Manufacture"
	se.from_bom = 1

	se_item = se.append("items", {})
	se_item.item_code = raw_material
	se_item.item_name = target_row.item_name
	se_item.description = target_row.description or ""
	se_item.s_warehouse = target_row.source_warehouse
	se_item.qty = float(qty)
	se_item.uom = target_row.uom
	se_item.stock_uom = target_row.stock_uom
	se_item.job_card_item = target_row.name
	se_item.t_warehouse = jc.wip_warehouse or jc.warehouse
	if not se_item.conversion_factor:
		se_item.conversion_factor = 1

	se.set_missing_values()
	se.set_stock_entry_type()
	# se.get_item_details()

	if not se.items:
		frappe.throw(_("No quantity to transfer"))

	se.insert()
	se.submit()

	jc = frappe.get_doc("Job Card", job_card)
	for row in jc.items:
		row.transferred_qty = row.required_qty
	jc.transferred_qty = total_qty

	jc.flags.ignore_validate = True
	jc.flags.ignore_validate_update_after_submit = True
	jc.save(ignore_permissions=True)

	frappe.db.commit()

	return {
		"success": True,
		"stock_entry": se.name,
		"add_raw_doc": add_doc.name,
		"source_wh": target_row.source_warehouse,
		"new_item_qty": target_row.required_qty,
		"total_for_quantity": total_qty,
		"items_count": len(jc.items),
	}


@frappe.whitelist()
def get_next_process_bom_qty(mixing_work_order):
	"""Get BOM qty required for NEXT process"""
	mixing_wo: WorkOrder = frappe.get_doc("Work Order", mixing_work_order)  # pyright: ignore[reportAssignmentType]
	current_process = mixing_wo.operations[0].operation if mixing_wo.operations else ""

	process_mapping = {
		"Mixing": "Distribution",
		"Mixing Operation - SJ": "Distribution",
		"Distribution": "Pressing",
		"Pressing": "Heating",
		"Heating": "Cooling",
		"Cooling": "Trimming",
		"Trimming": "Calibration",
		"Calibration": "Polishing",
		"Polishing": "Quality Check",
	}

	next_process = process_mapping.get(current_process)
	bom_doc: BOM = frappe.get_doc("BOM", mixing_wo.bom_no)  # pyright: ignore[reportAssignmentType]

	slab_template = _get_slab_template_from_bom(bom_doc)

	next_wos = frappe.db.get_list(
		"Work Order",
		filters={
			"production_plan": mixing_wo.production_plan,
			"docstatus": ["<", 2],
			"production_item": ["like", f"%{slab_template}%"],
			"production_line": mixing_wo.production_line,
		},
		fields=["name"],
		ignore_permissions=True,
	)

	wo_names = [wo.name for wo in next_wos]
	wo_ops = frappe.db.get_list(
		"Work Order Operation",
		filters={
			"parent": ["in", wo_names],
			"operation": ["=", next_process],
		},
		fields=["parent"],
		ignore_permissions=True,
	)

	next_wo = wo_ops[0].parent if wo_ops else None

	if not next_wo:
		next_wo = frappe.db.get_value(
			"Work Order",
			{
				"production_plan": mixing_wo.production_plan,
				"item_name": ["like", f"%{next_process}%"],
				"docstatus": ["<", 2],
				"production_item": ["like", f"%{slab_template}%"],
				"production_line": mixing_wo.production_line,
			},
			"name",
		)

	if not next_wo:
		return {"bom_qty": 0}

	next_wo_doc = frappe.get_doc("Work Order", next_wo)
	next_bom_doc = frappe.get_doc("BOM", next_wo_doc.bom_no)
	fg_item = mixing_wo.production_item

	for bom_item in next_bom_doc.items:
		if bom_item.item_code == fg_item:
			return {
				"bom_qty": flt(bom_item.stock_qty),
				"next_work_order": next_wo,
				"next_process": next_process,
			}

	return {"bom_qty": 0}


@frappe.whitelist()
def get_all_mixers(production_line=None):
	# Check if the current user has the role of Administrator
	user_roles = frappe.get_roles()
	is_admin = "Administrator" in user_roles or "Floor Manager" in user_roles

	production_line_names: list[str] = []
	production_lines = frappe.get_all("Production Line", fields=["name", "is_group", "parent_line"])
	if is_admin and not production_line:
		production_line_names = [line.name for line in production_lines if not line.is_group]

	elif production_line:
		# Get all the production lines
		parent_line = None
		for line in production_lines:
			if line.name == production_line:
				if line.is_group:
					parent_line = line.name
				else:
					parent_line = line.parent_line

		production_line_names = [line.name for line in production_lines if line.parent_line == parent_line]

	filters = [
		["workstation_type", '=', "Mixing"],
		["production_line", 'in', production_line_names if production_line_names else ['']]
	]

	mixers_list = frappe.get_all("Workstation", filters=filters, fields=["name", "production_line"], order_by="name asc")

	active_job_cards = frappe.get_all(
		"Job Card",
		filters={"job_started": 1, "status": ("!=", "Completed"), "workstation": ("is", "set"), "workstation_type": "Mixing"},
		fields=["name", "workstation", "workstation_type"]
	)

	active_names = {d.workstation: d.name for d in active_job_cards if d.workstation}

	queue_cards = get_mixing_queue(production_line)
	finished_names = {card.get("workstation"): card.get("name") for card in queue_cards if card.get("status") == "Completed" and card.get("workstation")}

	for m in mixers_list:
		if m.name in finished_names:
			m.status = "Finished"
			m.active_job_card = finished_names[m.name]
		elif m.name in active_names:
			m.status = "In Progress"
			m.active_job_card = active_names[m.name]
		else:
			m.status = "Idle"
			m.active_job_card = None

	return mixers_list


@frappe.whitelist()
def assign_mixer_to_job_card(job_card, mixer):
	jc = frappe.get_doc("Job Card", job_card)
	jc.mixer_number = mixer
	jc.save(ignore_permissions=True)
	frappe.db.commit()

	return {"status": "success", "mixer_number": jc.mixer_number}


@frappe.whitelist()
def get_mixer_polling_data(production_line=None, fetch_queue=0, fetch_status=0, fetch_mixers=0):
	"""Consolidated endpoint for polling queue, distribution status, and mixers"""
	result = {}

	fetch_queue_bool = frappe.utils.cint(fetch_queue)
	fetch_status_bool = frappe.utils.cint(fetch_status)
	fetch_mixers_bool = frappe.utils.cint(fetch_mixers)

	if fetch_status_bool:
		result["distribution_status"] = check_distribution_status(production_line)

	if fetch_queue_bool:
		result["queue"] = get_mixing_queue(production_line)

	if fetch_mixers_bool:
		result["mixers"] = get_all_mixers(production_line)

	return result
