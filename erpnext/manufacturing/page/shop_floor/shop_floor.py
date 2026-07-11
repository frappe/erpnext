import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Count, Date
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime, time_diff_in_seconds
from pypika.terms import ExistsCriterion

from erpnext.manufacturing.doctype.workstation.workstation import (
	get_status_color,
	get_time_logs,
)
from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
	get_template_details,
)

JOB_CARD_FIELDS = [
	"name",
	"docstatus",
	"production_item",
	"work_order",
	"operation",
	"total_completed_qty",
	"for_quantity",
	"process_loss_qty",
	"finished_good",
	"transferred_qty",
	"status",
	"expected_start_date",
	"expected_end_date",
	"time_required",
	"wip_warehouse",
	"skip_material_transfer",
	"backflush_from_wip_warehouse",
	"is_paused",
	"manufactured_qty",
	"is_subcontracted",
	"workstation",
	"sequence_id",
	"bom_no",
	"operation_id",
	"quality_inspection",
	"quality_inspection_template",
]

TODAY_SESSION_FIELDS = [
	"name",
	"docstatus",
	"production_item",
	"finished_good",
	"operation",
	"total_completed_qty",
	"for_quantity",
	"process_loss_qty",
	"total_time_in_mins",
	"status",
	"modified",
]

# Roles that unlock the Shop Floor manager board (work-order overview). Anyone else gets the
# operator view. System Manager is included so admins always see the full picture.
MANAGER_ROLES = {"Shop Floor Manager", "Manufacturing Manager", "System Manager"}

# Maps the manager buckets to the underlying Work Order statuses. "open" spans pending AND
# in-progress: starting a job card flips the Work Order to In Process, and separate tabs made
# it jump tabs on the next refresh — the operator would lose the card they were working on.
WORK_ORDER_STATUS_GROUPS = {
	"open": ["In Process", "Not Started", "Submitted", "Stock Reserved", "Stock Partially Reserved"],
	"completed": ["Completed"],
}

WORK_ORDER_FIELDS = [
	"name",
	"production_item",
	"item_name",
	"qty",
	"produced_qty",
	"status",
	"planned_start_date",
	"sales_order",
	"bom_no",
]


@frappe.whitelist()
def submit_job_card(job_card: str):
	"""Submit a draft job card whose quantity has already been recorded via End Session."""
	frappe.has_permission("Job Card", "submit", throw=True)
	jc = frappe.get_doc("Job Card", job_card)
	if jc.docstatus == 0:
		jc.submit()
	return {"name": jc.name, "docstatus": jc.docstatus}


def _record_session(job_card, qty, for_quantity, pending_qty, process_loss_qty, end_time):
	"""Record the session qty + close the active time log via Job Card's complete_job_card.

	auto_submit=0 so the backend doesn't auto-create+submit a Manufacture Stock Entry — that's
	a separate manual step driven by the post-submit prompt. Returns the reloaded doc.
	"""
	frappe.has_permission("Job Card", "write", throw=True)

	doc = frappe.get_doc("Job Card", job_card)
	doc.run_method(
		"complete_job_card",
		qty=flt(qty),
		for_quantity=flt(for_quantity),
		pending_qty=flt(pending_qty),
		process_loss_qty=flt(process_loss_qty),
		end_time=end_time,
		auto_submit=0,
	)
	doc.reload()
	return doc


@frappe.whitelist()
def save_and_continue(
	job_card: str,
	qty: float,
	for_quantity: float,
	pending_qty: float,
	process_loss_qty: float,
	end_time: str,
):
	"""Record the session qty + close the time log, then mark the JC as paused
	so the MES keeps it in the active slot for the next session."""
	frappe.has_permission("Job Card", "write", throw=True)
	doc = _record_session(job_card, qty, for_quantity, pending_qty, process_loss_qty, end_time)
	if doc.docstatus == 0:
		doc.db_set("is_paused", 1)
	return {"name": doc.name}


@frappe.whitelist()
def complete_and_submit(
	job_card: str,
	qty: float,
	for_quantity: float,
	pending_qty: float,
	process_loss_qty: float,
	end_time: str,
):
	"""Record the session qty + close the time log + submit the JC."""
	frappe.has_permission("Job Card", "submit", throw=True)
	doc = _record_session(job_card, qty, for_quantity, pending_qty, process_loss_qty, end_time)
	if doc.docstatus == 0:
		doc.submit()
	return {"name": doc.name, "finished_good": doc.finished_good}


@frappe.whitelist()
def make_manufacture_stock_entry(job_card: str):
	"""Build a "Manufacture" Stock Entry for the finished goods and save as draft.

	Mirrors the Job Card form's "Make Stock Entry" button — uses the doc's own
	make_stock_entry_for_semi_fg_item (purpose="Manufacture", job card linked) rather than
	the generic make_stock_entry, which would produce a "Material Transfer for Manufacture".
	Returns the draft SE name so the client can open it in a new tab.
	"""
	frappe.has_permission("Job Card", "read", throw=True)
	frappe.has_permission("Stock Entry", "submit", throw=True)
	doc = frappe.get_doc("Job Card", job_card)
	se = doc.make_stock_entry_for_semi_fg_item(auto_submit=False)
	return {"name": se.get("name")}


@frappe.whitelist()
def get_quality_inspection_checklist(job_card: str):
	"""Template parameters for the inline quality check an operator fills before submitting a
	job card. Returns the resolved template, its parameter rows, any already-linked inspection,
	and the item being inspected.
	"""
	frappe.has_permission("Job Card", "read", throw=True)

	jc = frappe.db.get_value(
		"Job Card",
		job_card,
		[
			"quality_inspection",
			"quality_inspection_template",
			"operation",
			"production_item",
			"finished_good",
		],
		as_dict=True,
	)
	if not jc:
		frappe.throw(_("Job Card {0} not found").format(job_card))

	template = jc.quality_inspection_template
	if not template and jc.operation:
		template = frappe.get_cached_value("Operation", jc.operation, "quality_inspection_template")

	parameters = []
	for p in get_template_details(template):
		parameters.append(
			{
				"specification": p.specification,
				"value": p.value,
				"numeric": cint(p.numeric),
				"min_value": p.min_value,
				"max_value": p.max_value,
				"formula_based_criteria": cint(p.formula_based_criteria),
				"acceptance_formula": p.acceptance_formula,
			}
		)

	return {
		"template": template,
		"parameters": parameters,
		"existing": jc.quality_inspection,
		"item_code": jc.finished_good or jc.production_item,
	}


@frappe.whitelist()
def submit_quality_inspection(job_card: str, readings: str | None = None):
	"""Create + submit an In-Process Quality Inspection for the job card and link it back, so the
	standard Job Card.validate_inspection() gate passes when the card is submitted.

	`readings` is a JSON list of {specification, status, reading_value} captured inline. For numeric
	/ formula parameters the measured value is stored and the Quality Inspection auto-evaluates
	pass/fail against min/max (or the formula); for qualitative parameters the operator's explicit
	Accepted/Rejected is taken as authoritative (manual_inspection). The QI's own validation then
	sets the overall Accepted/Rejected status.
	"""
	frappe.has_permission("Job Card", "write", throw=True)
	frappe.has_permission("Quality Inspection", "submit", throw=True)

	jc = frappe.get_doc("Job Card", job_card)

	# Idempotent: if a submitted inspection is already linked, don't create another.
	if jc.quality_inspection:
		existing = frappe.db.get_value(
			"Quality Inspection", jc.quality_inspection, ["status", "docstatus"], as_dict=True
		)
		if existing and existing.docstatus == 1:
			return {"name": jc.quality_inspection, "status": existing.status}

	template = jc.quality_inspection_template
	if not template and jc.operation:
		template = frappe.get_cached_value("Operation", jc.operation, "quality_inspection_template")
	if not template:
		frappe.throw(_("No Quality Inspection Template is configured for this operation."))

	reading_map = {r.get("specification"): r for r in (frappe.parse_json(readings) or [])}

	qi = frappe.new_doc("Quality Inspection")
	qi.inspection_type = "In Process"
	qi.reference_type = "Job Card"
	qi.reference_name = job_card
	qi.item_code = jc.finished_good or jc.production_item
	qi.bom_no = jc.bom_no
	qi.quality_inspection_template = template
	qi.inspected_by = frappe.session.user
	qi.get_item_specification_details()  # load readings from the template

	for reading in qi.readings:
		entry = reading_map.get(reading.specification)
		if not entry:
			continue
		value = entry.get("reading_value")
		if reading.numeric or reading.formula_based_criteria:
			# Measured value → let the Quality Inspection judge it against min/max or the formula.
			if value not in (None, ""):
				reading.reading_value = value
				reading.reading_1 = value
		else:
			# Qualitative check → the operator's explicit pass/fail wins.
			reading.manual_inspection = 1
			reading.status = entry.get("status") or "Accepted"
			if value not in (None, ""):
				reading.reading_value = value

	qi.insert()
	qi.submit()  # validate() → inspect_and_set_status() sets the overall Accepted/Rejected status

	# Link explicitly: the QI's own back-reference matches on production_item, which can differ
	# from the operation's finished_good, so we set it directly to be safe.
	jc.db_set("quality_inspection", qi.name)
	return {"name": qi.name, "status": qi.status}


@frappe.whitelist()
def get_shop_floor_context():
	"""Which experience to render — the manager board or the operator view — plus the
	signed-in operator's Employee (so Start Job can pre-fill them)."""
	roles = set(frappe.get_roles())
	can_manage = bool(roles & MANAGER_ROLES)
	return {
		"role_view": "manager" if can_manage else "operator",
		"can_manage": can_manage,
		"user_employee": frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name"),
	}


@frappe.whitelist()
def get_work_orders(
	status_group: str,
	start: int = 0,
	page_length: int = 20,
	search: str | None = None,
	with_job_cards_only: bool | int = 0,
):
	"""Paginated Work Orders for one manager bucket (open / completed),
	each decorated with a job-card status breakdown for the card's progress chip.

	When `with_job_cards_only` is set, only Work Orders that have at least one (non-cancelled)
	Job Card are returned — the board's opt-in "With job cards only" toggle.
	"""
	frappe.has_permission("Work Order", "read", throw=True)

	if status_group not in WORK_ORDER_STATUS_GROUPS:
		frappe.throw(_("Invalid status group: {0}").format(status_group))

	start = cint(start)
	page_length = cint(page_length) or 20
	with_job_cards_only = cint(with_job_cards_only)

	# Active buckets show the oldest-planned first (work the floor next); completed shows newest first.
	order = Order.desc if status_group == "completed" else Order.asc

	wo = frappe.qb.DocType("Work Order")
	query = _apply_work_order_filters(frappe.qb.from_(wo), wo, status_group, search, with_job_cards_only)
	work_orders = (
		query.select(*[wo[field] for field in WORK_ORDER_FIELDS])
		.orderby(wo.planned_start_date, order=order)
		.limit(page_length)
		.offset(start)
	).run(as_dict=True)

	total = _count_work_orders(status_group, search, with_job_cards_only)

	_enrich_work_orders(work_orders)

	return {
		"work_orders": work_orders,
		"total": cint(total),
		"start": start,
		"page_length": page_length,
	}


def _has_job_cards_criterion(wo, docstatus):
	jc = frappe.qb.DocType("Job Card")
	return ExistsCriterion(
		frappe.qb.from_(jc).select(jc.name).where((jc.work_order == wo.name) & (jc.docstatus == docstatus))
	)


def _bucket_criterion(wo, status_group):
	"""The floor is done with a Work Order once every job card is submitted, even though the
	Work Order stays "In Process" until the finished goods are received. Such operationally
	complete orders belong on the Completed tab — not stranded under Pending / In Progress."""
	open_statuses = WORK_ORDER_STATUS_GROUPS["open"]
	all_job_cards_done = _has_job_cards_criterion(wo, 1) & _has_job_cards_criterion(wo, 0).negate()
	if status_group == "completed":
		return (wo.status == "Completed") | (wo.status.isin(open_statuses) & all_job_cards_done)
	return wo.status.isin(open_statuses) & (
		_has_job_cards_criterion(wo, 1).negate() | _has_job_cards_criterion(wo, 0)
	)


def _apply_work_order_filters(query, wo, status_group, search, with_job_cards_only):
	"""Shared WHERE clauses for the board's row + count queries (bucket, search, job-card toggle)."""
	query = query.where((wo.docstatus == 1) & _bucket_criterion(wo, status_group))
	if search:
		like = f"%{search}%"
		query = query.where(wo.name.like(like) | wo.production_item.like(like) | wo.item_name.like(like))
	if with_job_cards_only:
		jc = frappe.qb.DocType("Job Card")
		wo_with_job_cards = frappe.qb.from_(jc).select(jc.work_order).where(jc.docstatus < 2)
		query = query.where(wo.name.isin(wo_with_job_cards))
	return query


def _count_work_orders(status_group: str, search: str | None, with_job_cards_only: int = 0) -> int:
	"""Total Work Orders in a bucket (drives pagination), honouring the same filters as the rows."""
	wo = frappe.qb.DocType("Work Order")
	query = _apply_work_order_filters(frappe.qb.from_(wo), wo, status_group, search, with_job_cards_only)
	return cint(query.select(Count("*")).run()[0][0])


def _enrich_work_orders(work_orders: list[dict]) -> None:
	"""Attach item/workstation image, status colour, % complete and a job-card breakdown to each row."""
	wo_names = [row.name for row in work_orders]
	jc_counts = _get_job_card_status_counts(wo_names)
	workstation_map = _get_current_workstation_map(wo_names)
	for row in work_orders:
		row.item_image = (
			frappe.get_cached_value("Item", row.production_item, "image") if row.production_item else None
		)
		row.status_colour = get_status_color(row.status)
		row.per_completed = round(flt(row.produced_qty) / flt(row.qty) * 100, 1) if flt(row.qty) else 0
		counts = jc_counts.get(row.name, {})
		row.job_card_status = counts.get("by_status", {})
		row.total_operations = counts.get("total", 0)
		row.completed_operations = counts.get("completed", 0)
		row.in_progress_operations = counts.get("in_progress", 0)
		# Two segments for the card's progress bar: green (done) + orange (in progress); the rest
		# of the track stays grey (pending / not started).
		row.per_operations = (
			round(row.completed_operations / row.total_operations * 100, 1) if row.total_operations else 0
		)
		row.per_in_progress = (
			round(row.in_progress_operations / row.total_operations * 100, 1) if row.total_operations else 0
		)
		# Current/active operation's workstation (name + Active-Status image) for the card header.
		workstation = workstation_map.get(row.name, {})
		row.workstation = workstation.get("workstation")
		row.workstation_name = workstation.get("workstation_name")
		row.workstation_image = workstation.get("image")
		row.current_operation = workstation.get("operation")


def _get_current_workstation_map(wo_names: list[str]) -> dict[str, dict]:
	"""Map each Work Order to its current operation's workstation (name + Active-Status image).

	The "current" operation is the first not-yet-completed operation in the routing (by idx);
	if every operation is complete, the last one is used so finished cards still show a workstation.
	"""
	if not wo_names:
		return {}

	operations = frappe.get_all(
		"Work Order Operation",
		filters={"parent": ["in", wo_names]},
		fields=["parent", "idx", "operation", "status", "workstation"],
		order_by="parent, idx",
	)

	ops_by_wo: dict[str, list] = {}
	for op in operations:
		ops_by_wo.setdefault(op.parent, []).append(op)

	chosen_by_wo = {}
	workstations = set()
	for wo_name, ops in ops_by_wo.items():
		current = next((op for op in ops if (op.status or "") != "Completed"), ops[-1])
		if current.workstation:
			chosen_by_wo[wo_name] = current
			workstations.add(current.workstation)

	ws_details = {}
	if workstations:
		for ws in frappe.get_all(
			"Workstation",
			filters={"name": ["in", list(workstations)]},
			fields=["name", "workstation_name", "on_status_image"],
		):
			ws_details[ws.name] = ws

	result = {}
	for wo_name, op in chosen_by_wo.items():
		detail = ws_details.get(op.workstation, {})
		result[wo_name] = {
			"workstation": op.workstation,
			"workstation_name": detail.get("workstation_name") or op.workstation,
			"image": detail.get("on_status_image"),
			"operation": op.operation,
		}
	return result


def _get_job_card_status_counts(wo_names: list[str]) -> dict[str, dict]:
	"""One batched query → {work_order: {by_status: {status: n}, total, completed}} for the WO cards."""
	if not wo_names:
		return {}

	rows = frappe.get_all(
		"Job Card",
		filters={"work_order": ["in", wo_names], "docstatus": ["<", 2]},
		fields=["work_order", "status"],
	)
	result: dict[str, dict] = {}
	for row in rows:
		entry = result.setdefault(
			row.work_order, {"by_status": {}, "total": 0, "completed": 0, "in_progress": 0}
		)
		status = "Not Started" if (row.status or "Open") == "Open" else row.status
		entry["by_status"][status] = entry["by_status"].get(status, 0) + 1
		entry["total"] += 1
		# "To Manufacture" = operation done, only the Manufacture Stock Entry is pending — count it
		# as completed so the work order's progress bar reflects the finished operation.
		if status in ("Completed", "Submitted", "To Manufacture"):
			entry["completed"] += 1
		elif status == "Work In Progress":
			entry["in_progress"] += 1
	return result


@frappe.whitelist()
def get_data(workstation: str | None = None, work_order: str | None = None):
	"""
	Returns job-card data for the Shop Floor page.

	When `work_order` is set it wins over `workstation` and the result spans every
	operation of that Work Order (including subcontracted job cards). When only
	`workstation` is set, the result is the open + in-progress job cards for that
	workstation, excluding subcontracted.
	"""
	if not (workstation or work_order):
		return {"job_cards": [], "capacity": 1, "mode": None}
	if not frappe.has_permission("Job Card", "read"):
		return {"job_cards": [], "capacity": 1, "mode": None}

	filters, mode = _build_job_card_filters(workstation, work_order)
	jc_data = _fetch_job_cards(filters, mode)
	_enrich_job_cards(jc_data)

	capacity, oee = 1, None
	if mode == "workstation":
		capacity = frappe.db.get_value("Workstation", workstation, "production_capacity") or 1
		oee = get_workstation_oee(workstation)

	return {
		"job_cards": jc_data,
		"capacity": capacity,
		"mode": mode,
		"oee": oee,
		"user_employee": frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name"),
		"today_sessions": get_today_sessions(workstation, work_order),
	}


def _build_job_card_filters(workstation, work_order):
	"""Filters + mode for the job-card query. work_order spans all ops; workstation is operator view."""
	filters = {"docstatus": ("<", 2)}
	if work_order:
		filters["work_order"] = work_order
		return filters, "work_order"

	filters["workstation"] = workstation
	filters["is_subcontracted"] = 0
	filters["status"] = ["!=", "Stopped"]
	return filters, "workstation"


def _fetch_job_cards(filters, mode):
	"""Job cards matching filters. In workstation mode only drafts matter — submitted JCs are
	done from MES's perspective and missed ones are picked up via the standard Job Card list.

	In work_order mode the whole routing is shown (incl. completed/submitted job cards), ordered
	by the operation sequence so the operator reads them in manufacturing order.
	"""
	order_by = (
		"sequence_id asc, expected_start_date, expected_end_date"
		if mode == "work_order"
		else "expected_start_date, expected_end_date"
	)
	# Drafts are the operator's working set; submitted "To Manufacture" cards are also kept so
	# the station shows what still needs a Manufacture Stock Entry (its own section, client-side).
	# This must be part of the query, not a post-filter: a busy workstation's history would
	# otherwise fill the row limit with old submitted cards and hide the active drafts.
	or_filters = [["docstatus", "=", 0], ["status", "=", "To Manufacture"]] if mode == "workstation" else None
	return frappe.get_all(
		"Job Card",
		fields=JOB_CARD_FIELDS,
		filters=filters,
		or_filters=or_filters,
		order_by=order_by,
		limit=50,
	)


def _enrich_job_cards(jc_data):
	"""Decorate every row with display + material-availability data for the page."""
	job_card_names = [row.name for row in jc_data]
	time_logs = get_time_logs(job_card_names) if job_card_names else {}
	allow_excess_transfer = frappe.db.get_single_value("Manufacturing Settings", "job_card_excess_transfer")
	for row in jc_data:
		_enrich_job_card_row(row, time_logs, allow_excess_transfer)


def _enrich_job_card_row(row, time_logs, allow_excess_transfer):
	"""Attach status label, item image/uom, time logs and material availability to one row."""
	if row.status == "Open":
		row.status = "Not Started"

	item_code = row.finished_good or row.production_item
	row.fg_uom = frappe.get_cached_value("Item", item_code, "stock_uom") if item_code else None
	row.item_image = frappe.get_cached_value("Item", item_code, "image") if item_code else None
	row.status_colour = get_status_color(row.status)
	row.time_logs = time_logs.get(row.name, [])
	row.make_material_request = bool(row.for_quantity > row.transferred_qty or allow_excess_transfer)
	# Required vs transferred + on-hand in source — operator sees shortages before starting work.
	row.materials = get_job_card_materials(row.name)
	# Guided execution: per-operation work instructions + quality-check state for the card.
	row.instructions = _get_operation_instructions(row.operation)
	row.qc = _get_job_card_qc(row)


def _get_operation_instructions(operation: str | None) -> dict | None:
	"""Description + rich Work Instructions from the Operation master, for the card's
	Instructions panel. Returns None when the operation has neither, so the panel stays hidden.

	`work_instruction` is a Text Editor field (HTML) — Frappe bleach-sanitizes it on save, so it
	is safe to render as-is on the client. `description` is plain text and must be escaped there.
	"""
	if not operation:
		return None

	op = frappe.get_cached_value("Operation", operation, ["description", "work_instruction"], as_dict=True)
	if not op:
		return None

	description = (op.description or "").strip()
	work_instruction = (op.work_instruction or "").strip()
	if not description and not work_instruction:
		return None
	return {"description": description, "work_instruction": work_instruction}


def _get_job_card_qc(row) -> dict:
	"""Quality-check state for a job card row: whether an inspection is required before submit,
	which template to use, and any inspection already linked (name + status + docstatus).

	"Required" mirrors Job Card.validate_inspection() — BOM inspection_required AND the Work Order
	Operation's quality_inspection_required. When only a template is configured the check is
	offered but not enforced.
	"""
	required = bool(
		row.get("bom_no")
		and frappe.get_cached_value("BOM", row.bom_no, "inspection_required")
		and row.get("operation_id")
		and frappe.db.get_value("Work Order Operation", row.operation_id, "quality_inspection_required")
	)

	template = row.get("quality_inspection_template")
	if not template and row.get("operation"):
		template = frappe.get_cached_value("Operation", row.operation, "quality_inspection_template")

	info = {
		"required": required,
		"template": template,
		"has_checklist": bool(template),
		"name": None,
		"status": None,
		"docstatus": None,
	}
	if row.get("quality_inspection"):
		qi = frappe.db.get_value(
			"Quality Inspection", row.quality_inspection, ["name", "status", "docstatus"], as_dict=True
		)
		if qi:
			info.update({"name": qi.name, "status": qi.status, "docstatus": qi.docstatus})
	return info


def get_job_card_materials(job_card: str) -> list[dict]:
	"""Required vs transferred + on-hand stock for each raw material in the source warehouse.

	Powers the active-job Materials side panel — operator sees shortages before starting work.
	"""
	items = frappe.get_all(
		"Job Card Item",
		filters={"parent": job_card},
		fields=["item_code", "item_name", "source_warehouse", "required_qty", "transferred_qty", "uom"],
		order_by="idx",
	)
	if not items:
		return []

	on_hand_map = _get_on_hand_map(items)
	return [_build_material_row(it, on_hand_map) for it in items]


def _get_on_hand_map(items) -> dict[tuple[str, str], float]:
	"""Map (item_code, warehouse) → on-hand qty via batched Bin lookups."""
	pairs = {(it.item_code, it.source_warehouse) for it in items if it.source_warehouse}
	if not pairs:
		return {}

	bin_rows = frappe.get_all(
		"Bin",
		filters={
			"item_code": ["in", list({p[0] for p in pairs})],
			"warehouse": ["in", list({p[1] for p in pairs})],
		},
		fields=["item_code", "warehouse", "actual_qty"],
	)
	return {(b.item_code, b.warehouse): flt(b.actual_qty) for b in bin_rows}


def _build_material_row(it, on_hand_map) -> dict:
	"""One material entry with shortage + status pill for the side panel."""
	required = flt(it.required_qty)
	transferred = flt(it.transferred_qty)
	on_hand = on_hand_map.get((it.item_code, it.source_warehouse), 0.0)
	shortage = max(required - transferred, 0.0)
	if transferred >= required:
		status = "ready"
	elif on_hand >= shortage:
		status = "available"
	else:
		status = "short"
	return {
		"item_code": it.item_code,
		"item_name": it.item_name or it.item_code,
		"source_warehouse": it.source_warehouse,
		"required_qty": required,
		"transferred_qty": transferred,
		"on_hand_qty": on_hand,
		"shortage": shortage,
		"uom": it.uom or "",
		"status": status,
	}


def get_today_sessions(workstation: str | None, work_order: str | None) -> list[dict]:
	"""Submitted job cards finalized today — used for the bottom 'Today's Sessions' strip.

	Filtered on docstatus=1 only (draft/cancelled excluded). The status pill follows the
	job card's own status (e.g. Work In Progress → orange, Completed → green).
	"""
	filters = _today_sessions_filters(workstation, work_order)
	if filters is None:
		return []

	rows = frappe.get_all(
		"Job Card",
		filters=filters,
		fields=TODAY_SESSION_FIELDS,
		order_by="modified desc",
		limit=10,
	)
	for r in rows:
		item_code = r.finished_good or r.production_item
		r.item_image = frappe.get_cached_value("Item", item_code, "image") if item_code else None
		r.status_colour = get_status_color(r.status)
	return rows


def _today_sessions_filters(workstation, work_order) -> dict | None:
	"""Submitted-today filter scoped to a work order or workstation; None if neither given.

	"To Manufacture" cards are excluded — they aren't finalized yet (Manufacture Stock Entry
	pending) and get their own section, so they shouldn't appear among finished sessions.
	"""
	filters = {
		"docstatus": 1,
		"modified": [">=", get_datetime(f"{getdate()} 00:00:00")],
		"status": ["!=", "To Manufacture"],
	}
	if work_order:
		filters["work_order"] = work_order
	elif workstation:
		filters["workstation"] = workstation
	else:
		return None
	return filters


def get_workstation_oee(workstation: str) -> dict | None:
	"""
	OEE = Availability X Performance X Quality, computed for today only.

	Caveat: without a downtime-reason capture step, Availability is just
	(actual_run_time / scheduled_time) — it cannot distinguish planned breaks
	from unplanned breakdowns. The number is directional, not audit-grade.
	"""
	today = getdate()
	scheduled_min = flt(frappe.db.get_value("Workstation", workstation, "total_working_hours")) * 60
	actual_run_min, ideal_min = _get_run_and_ideal_minutes(workstation, today)
	completed_jcs = _get_completed_jcs_today(workstation, today)

	# No activity at all today — nothing to display.
	if actual_run_min == 0 and not completed_jcs:
		return None
	return _build_oee(scheduled_min, actual_run_min, ideal_min, completed_jcs)


def _get_run_and_ideal_minutes(workstation, today) -> tuple[float, float]:
	"""Sum actual run minutes (clipped to today) and the ideal minutes for produced qty."""
	today_start = get_datetime(f"{today} 00:00:00")
	today_end = get_datetime(f"{today} 23:59:59")
	now = now_datetime()
	actual_run_min = 0.0
	ideal_min = 0.0
	for log in _get_oee_time_logs(workstation, today_start, today_end):
		# Clip the log's interval to today's window for fair attribution.
		start = max(get_datetime(log.from_time), today_start)
		end = min(get_datetime(log.to_time) if log.to_time else now, today_end)
		if end > start:
			actual_run_min += time_diff_in_seconds(end, start) / 60
		if log.completed_qty and log.for_quantity and log.time_required:
			ideal_min += (flt(log.time_required) / flt(log.for_quantity)) * flt(log.completed_qty)
	return actual_run_min, ideal_min


def _get_oee_time_logs(workstation, today_start, today_end) -> list[dict]:
	"""Job Card time logs whose interval overlaps today's window."""
	tl = frappe.qb.DocType("Job Card Time Log")
	jc = frappe.qb.DocType("Job Card")
	return (
		frappe.qb.from_(tl)
		.inner_join(jc)
		.on(jc.name == tl.parent)
		.select(tl.from_time, tl.to_time, tl.completed_qty, jc.for_quantity, jc.time_required)
		.where(jc.workstation == workstation)
		.where(jc.docstatus < 2)
		.where(tl.from_time <= today_end)
		.where(tl.to_time.isnull() | (tl.to_time >= today_start))
	).run(as_dict=True)


def _get_completed_jcs_today(workstation, today) -> list[dict]:
	"""Job cards completed/submitted today — process loss is finalized at submission."""
	jc = frappe.qb.DocType("Job Card")
	return (
		frappe.qb.from_(jc)
		.select(jc.total_completed_qty, jc.process_loss_qty)
		.where(jc.workstation == workstation)
		.where(jc.status.isin(["Completed", "Submitted"]))
		.where(Date(jc.modified) == today)
	).run(as_dict=True)


def _build_oee(scheduled_min, actual_run_min, ideal_min, completed_jcs) -> dict:
	"""Combine the three OEE factors into the response payload."""
	total_completed = sum(flt(j.total_completed_qty) for j in completed_jcs)
	total_loss = sum(flt(j.process_loss_qty) for j in completed_jcs)
	availability = min(actual_run_min / scheduled_min, 1.0) if scheduled_min > 0 else None
	performance = min(ideal_min / actual_run_min, 1.0) if actual_run_min > 0 else 0.0
	quality = max(total_completed - total_loss, 0.0) / total_completed if total_completed > 0 else 1.0
	# OEE requires all three factors; without a schedule, Availability is unknown.
	oee_val = round(availability * performance * quality * 100, 1) if availability is not None else None
	return {
		"oee": oee_val,
		"availability": round(availability * 100, 1) if availability is not None else None,
		"performance": round(performance * 100, 1),
		"quality": round(quality * 100, 1),
	}
