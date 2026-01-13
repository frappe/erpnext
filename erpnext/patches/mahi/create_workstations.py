import re

import click
import frappe

from erpnext.manufacturing.doctype.manufacturing_process.constants import (
	ALL_MFG_PROCESSES,
	CALIBRATION_PROCESS,
	COOLING_PROCESS,
	DISTRIBUTION_PROCESS,
	HEATING_PROCESS,
	MIXING_PROCESS,
	POLISHING_PROCESS,
	PRESSING_PROCESS,
	QUALITY_CHECK_PROCESS,
	TRIMMING_PROCESS,
)
from erpnext.manufacturing.doctype.workstation.workstation import Workstation
from erpnext.manufacturing.doctype.workstation_type.workstation_type import WorkstationType
from erpnext.stock.doctype.warehouse.warehouse import Warehouse


def execute():
	create_workstation_types()
	create_workstations()


def create_workstation_types():
	click.secho("Creating Workstation Types...", fg="green")
	# Iterate over ALL_WAREHOUSE_TYPES and create a new Workstation Type for each type
	for process_name in ALL_MFG_PROCESSES:
		new_workstation_type: WorkstationType = frappe.new_doc("Workstation Type")  # pyright: ignore[reportAssignmentType]
		new_workstation_type.workstation_type = process_name
		new_workstation_type.save()
		click.secho(f"Created Workstation Type {process_name}...", fg="blue")

	click.secho("Created all Workstation Types...", fg="green")


@frappe.whitelist(allow_guest=True)
def create_workstations():
	# Get all the lines
	lines = frappe.get_all("Production Line", fields=["name", "line_name", "line_code"])

	# Get all the Warehouses
	warehouses: list[Warehouse] = frappe.get_all("Warehouse", fields=["name", "warehouse_name", "mfg_process_type", "production_line"])

	process_workstation_map = get_process_workstation_map()

	click.secho("Creating Workstations...", fg="green")
	# Iterate over the Warehouses and create workstations
	for warehouse in warehouses:
		process = warehouse.mfg_process_type or ""
		current_line = next((l for l in lines if l.name == warehouse.production_line), None)
		workstation_type_name = process_workstation_map.get(process, None)

		if not workstation_type_name or not current_line:
			continue

		workstation_count = re.findall(r"\s\d\s", warehouse.warehouse_name)
		workstation_count_text = f" {workstation_count[0]}" if workstation_count else ""
		workstation_name = f"{workstation_type_name}{workstation_count_text} ({current_line.line_name})"
		new_workstation: Workstation = frappe.new_doc("Workstation")  # pyright: ignore[reportAssignmentType]
		new_workstation.production_line = current_line.name
		new_workstation.warehouse = warehouse.name
		new_workstation.workstation_name = workstation_name
		new_workstation.workstation_type = process
		new_workstation.save()
		click.secho(f"Created workstation {workstation_name} successfully", fg="blue")

	click.secho("Created all Workstations...", fg="green")

def get_process_workstation_map():
	return {
		MIXING_PROCESS: "Mixer",
		DISTRIBUTION_PROCESS: "Distributor",
		PRESSING_PROCESS: "Presser",
		HEATING_PROCESS: "Heater",
		COOLING_PROCESS: "Cooler",
		TRIMMING_PROCESS: "Trimmer",
		CALIBRATION_PROCESS: "Calibrator",
		POLISHING_PROCESS: "Polisher",
		QUALITY_CHECK_PROCESS: "Quality Checker",
	}
