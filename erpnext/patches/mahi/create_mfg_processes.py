from webbrowser import get

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
from erpnext.manufacturing.doctype.manufacturing_process.manufacturing_process import (
	ManufacturingProcess,
)


def execute():
	create_mfg_processes()


def create_mfg_processes():
	mfg_processes = [
		MIXING_PROCESS,
		DISTRIBUTION_PROCESS,
		PRESSING_PROCESS,
		HEATING_PROCESS,
		QUARANTINE_PROCESS,
		COOLING_PROCESS,
		TRIMMING_PROCESS,
		CALIBRATION_PROCESS,
		POLISHING_PROCESS,
		QUALITY_CHECK_PROCESS,
	]

	click.secho("Creating Manufacturing Processes...", fg="green")
	for process in mfg_processes:
		mfg_process: ManufacturingProcess= frappe.new_doc("Manufacturing Process")  # pyright: ignore[reportAssignmentType]
		mfg_process.process_name = process
		mfg_process.save()
		click.secho(f"Created Process: {process}", fg="blue")

	frappe.db.commit()
	click.secho("Created all Manufacturing Processes...", fg="green")
