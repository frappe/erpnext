import click
import frappe

from erpnext.manufacturing.doctype.manufacturing_process.constants import (
	CALIBRATION_PROCESS,
	COOLING_PROCESS,
	DISTRIBUTION_PROCESS,
	HEATING_PROCESS,
	MIXING_PROCESS,
	POLISHING_PROCESS,
	PRESSING_PROCESS,
	QUALITY_CHECK_PROCESS,
	QUARANTINE_PROCESS,
	TRIMMING_PROCESS,
)
from erpnext.manufacturing.doctype.manufacturing_process_map.manufacturing_process_map import (
	ManufacturingProcessMap,
)
from erpnext.manufacturing.doctype.process_warehouse_map.process_warehouse_map import ProcessWarehouseMap
from erpnext.manufacturing.doctype.production_line.constants import CHILD_LINES, PARENT_LINES
from erpnext.patches.mahi.create_mahi_settings import get_company
from erpnext.stock.doctype.warehouse.constants import (
	CALIBRATION_WAREHOUSE,
	COOLING_WAREHOUSE,
	DISTRIBUTION_WAREHOUSE,
	FINISHED_GOODS_WAREHOUSE,
	HEATING_WAREHOUSE,
	MIXING_WAREHOUSE,
	POLISHING_WAREHOUSE,
	PRESSING_WAREHOUSE,
	QUALITY_CHECK_WAREHOUSE,
	# QUARANTINE_WAREHOUSE,
	SILOS_WAREHOUSE,
	TRIMMING_WAREHOUSE,
)


def execute():
	create_mfg_process_map()
	create_process_warehouse_maps()
	pass


def create_mfg_process_map():
	mfg_process_map = get_mfg_process_map()

	click.secho("Creating Manufacturing Process Maps...", fg="green")
	for process, next_process in mfg_process_map.items():
		new_mfg_process_map: ManufacturingProcessMap = frappe.new_doc("Manufacturing Process Map")  # pyright: ignore[reportAssignmentType]
		new_mfg_process_map.source_process = process
		new_mfg_process_map.target_process = next_process
		new_mfg_process_map.save()
		click.secho(f"Created Process Map: {process} -> {next_process}", fg="blue")

	click.secho("Created all Manufacturing Process Maps...", fg="green")


def create_process_warehouse_maps():
	wh_map = get_process_warehouse_type_map()
	parent_lines = {line["line_code"]: line for line in PARENT_LINES}
	company = get_company()

	click.secho("Creating Process Warehouse Maps...", fg="green")
	for line in CHILD_LINES:
		for process, wh_types in wh_map.items():

			# warehouse_type is the process name (e.g. "Mixing")
			wip_warehouses = frappe.get_all(
				"Warehouse",
				filters={"mfg_process_type": process, "production_line": line["line_code"], "company": company.name},
				fields=["name", "warehouse_name"],
			)

			if not wip_warehouses:
				wip_warehouses = frappe.get_all(
					"Warehouse",
					filters={"mfg_process_type": process, "production_line": line["parent_line"], "company": company.name},
					fields=["name", "warehouse_name"],
				)

			for wip_wh in wip_warehouses:
				source_whs = resolve_warehouse(wh_types["source_warehouse"], line, parent_lines, company, wip_wh.name, True)
				fg_wh = resolve_warehouse(wh_types["fg_warehouse"], line, parent_lines, company, wip_wh.name)[0]

				if source_whs and fg_wh:
					if not frappe.db.exists(
						"Process Warehouse Map",
						{"production_line": line["line_code"], "process_name": process, "wip_warehouse": wip_wh.name},
					):
						for src_wh in source_whs:
							doc: ProcessWarehouseMap = frappe.new_doc("Process Warehouse Map")  # pyright: ignore[reportAssignmentType]
							doc.production_line = line["line_code"]
							doc.process_name = process
							doc.source_warehouse = src_wh
							doc.wip_warehouse = wip_wh.name
							doc.fg_warehouse = fg_wh
							doc.save()
							click.secho(f"Created Map for {wip_wh.name}", fg="blue")


def get_mfg_process_map():
	return {
		MIXING_PROCESS: DISTRIBUTION_PROCESS,
		DISTRIBUTION_PROCESS: PRESSING_PROCESS,
		PRESSING_PROCESS: HEATING_PROCESS,
		HEATING_PROCESS: QUARANTINE_PROCESS,
		QUARANTINE_PROCESS: COOLING_PROCESS,
		COOLING_PROCESS: TRIMMING_PROCESS,
		TRIMMING_PROCESS: CALIBRATION_PROCESS,
		CALIBRATION_PROCESS: POLISHING_PROCESS,
		POLISHING_PROCESS: QUALITY_CHECK_PROCESS,
		QUALITY_CHECK_PROCESS: MIXING_PROCESS,
	}


def get_process_warehouse_type_map():
	return {
			MIXING_PROCESS: {
				"source_warehouse": SILOS_WAREHOUSE,
				"wip_warehouse": MIXING_WAREHOUSE,
				"fg_warehouse": MIXING_WAREHOUSE,
			},
			DISTRIBUTION_PROCESS: {
				"source_warehouse": MIXING_WAREHOUSE,
				"wip_warehouse": DISTRIBUTION_WAREHOUSE,
				"fg_warehouse": PRESSING_WAREHOUSE,
			},
			PRESSING_PROCESS: {
				"source_warehouse": PRESSING_WAREHOUSE,
				"wip_warehouse": PRESSING_WAREHOUSE,
				"fg_warehouse": HEATING_WAREHOUSE,
			},
			HEATING_PROCESS: {
				"source_warehouse": HEATING_WAREHOUSE,
				"wip_warehouse": HEATING_WAREHOUSE,
				"fg_warehouse": COOLING_WAREHOUSE,
			},
			COOLING_PROCESS: {
				"source_warehouse": COOLING_WAREHOUSE,
				"wip_warehouse": COOLING_WAREHOUSE,
				"fg_warehouse": TRIMMING_WAREHOUSE,
			},
			TRIMMING_PROCESS: {
				"source_warehouse": TRIMMING_WAREHOUSE, "wip_warehouse": TRIMMING_WAREHOUSE,
				"fg_warehouse": CALIBRATION_WAREHOUSE,
			},
			CALIBRATION_PROCESS: {
				"source_warehouse": CALIBRATION_WAREHOUSE,
				"wip_warehouse": CALIBRATION_WAREHOUSE,
				"fg_warehouse": POLISHING_WAREHOUSE,
			},
			POLISHING_PROCESS: {
				"source_warehouse": POLISHING_WAREHOUSE,
				"wip_warehouse": POLISHING_WAREHOUSE,
				"fg_warehouse": QUALITY_CHECK_WAREHOUSE,
			},
			QUALITY_CHECK_PROCESS: {
				"source_warehouse": QUALITY_CHECK_WAREHOUSE,
				"wip_warehouse": QUALITY_CHECK_WAREHOUSE,
				"fg_warehouse": FINISHED_GOODS_WAREHOUSE,
			},
		}


def resolve_warehouse(base_type, line, parent_lines, company, current_wip, resolve_multiple = False):
	# If the base type is contained in current WIP name (e.g. Mixing -> Mixing 1), return current WIP
	# Check simple containment of the base type string (e.g. "Mixing Warehouse")
	if base_type in current_wip:
		return [current_wip]

	names = []
	# 1. Try exact match on current line
	name = f"{base_type} ({line['line_name']}) - {company.abbr}"
	if frappe.db.exists("Warehouse", name):
		if not resolve_multiple:
			return [name]

		names.append(name)

	# 2. Try with " 1" suffix on current line
	name = f"{base_type} 1 ({line['line_name']}) - {company.abbr}"
	if frappe.db.exists("Warehouse", name):
		if not resolve_multiple:
			return [name]

		names.append(name)

	# 3. Try with " 2" suffix on current line
	name = f"{base_type} 2 ({line['line_name']}) - {company.abbr}"
	if frappe.db.exists("Warehouse", name):
		if not resolve_multiple:
			return [name]

		names.append(name)

	# 4. Try Parent Line
	if line.get("parent_line") and line["parent_line"] in parent_lines:
		parent = parent_lines[line["parent_line"]]
		name = f"{base_type} ({parent['line_name']}) - {company.abbr}"
		if frappe.db.exists("Warehouse", name):
			if not resolve_multiple:
				return [name]

			names.append(name)

	return names
