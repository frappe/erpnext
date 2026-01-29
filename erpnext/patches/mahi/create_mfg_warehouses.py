from enum import EnumType

import click
import frappe
from frappe.types.DF import HTMLEditor

from erpnext.manufacturing.doctype.manufacturing_process.constants import (
	ALL_MFG_PROCESSES,
	DISTRIBUTION_PROCESS,
	MIXING_PROCESS,
)
from erpnext.manufacturing.doctype.production_line.constants import CHILD_LINES, PARENT_LINES
from erpnext.patches.mahi.create_mahi_settings import get_company
from erpnext.stock.doctype.warehouse.constants import FINISHED_GOODS_WAREHOUSE, SILOS_WAREHOUSE
from erpnext.stock.doctype.warehouse.warehouse import Warehouse


def execute():
	create_mfg_warehouses()


def create_mfg_warehouses():
	mfg_warehouses = generate_mfg_warehouses()
	company = get_company()

	click.secho(f"Creating warehouses for {company.name}...", fg="green")
	for warehouse in mfg_warehouses:
		exists = frappe.db.exists("Warehouse", {"warehouse_name": warehouse["warehouse_name"], "company": company.name})
		if exists:
			click.secho(f"Warehouse {warehouse['warehouse_name']} already exists in {company.name}", fg="yellow")
			continue

		all_lines = [*PARENT_LINES, *CHILD_LINES]

		# Find the line using the code
		line = next((l for l in all_lines if l['line_code'] == warehouse['production_line']), all_lines[0])
		parent_line = next((l for l in PARENT_LINES if l['line_code'] == line.get('parent_line')), None)
		parent_warehouse = f"All Warehouses ({parent_line['line_name']}) - {company.abbr}" if parent_line else None

		new_warehouse: Warehouse = frappe.new_doc("Warehouse")  # pyright: ignore[reportAssignmentType]
		new_warehouse.company = company.name
		new_warehouse.production_line = warehouse["production_line"]
		new_warehouse.warehouse_name = warehouse["warehouse_name"]
		new_warehouse.warehouse_type = warehouse["warehouse_type"]
		new_warehouse.mfg_process_type = warehouse.get("process", None)
		new_warehouse.parent_warehouse = parent_warehouse if "All" not in warehouse["warehouse_name"] else None
		new_warehouse.is_group = True if "All" in warehouse["warehouse_name"] else False
		new_warehouse.save()
		click.secho(f"Created warehouse {warehouse['warehouse_name']} successfully", fg="blue")

	click.secho("Created all the required warehouses...", fg="green")

	frappe.db.commit()

# This method returns the configuration object using which the final warehouse list is generated.
def get_warehouse_config():
	return {
		MIXING_PROCESS: [1, 1, 1, 1, 1], # Two for the first two child lines, one per rest of the child lines.,
		DISTRIBUTION_PROCESS: [1] * 5 # One per child line,
	}


# Generate all the warehouses for all the lines based on the configuration.
def generate_mfg_warehouses():
	warehouses = []
	wh_config = get_warehouse_config()

	for line in PARENT_LINES:
		warehouses.append({
			"warehouse_name": f"All Warehouses ({line['line_name']})",
			"production_line": line['line_code'],
			"warehouse_type": None,
		})

		warehouses.append({
			"warehouse_name": f"{SILOS_WAREHOUSE} ({line['line_name']})",
			"production_line": line['line_code'],
			"warehouse_type": "Silos",
		})

		warehouses.append({
			"warehouse_name": f"{FINISHED_GOODS_WAREHOUSE} ({line['line_name']})",
			"production_line": line['line_code'],
			"warehouse_type": "Finished Goods",
		})

	for process in ALL_MFG_PROCESSES:
		config = wh_config.get(process)
		required_lines = CHILD_LINES if config else PARENT_LINES
		for index, line in enumerate(required_lines):
			count = config[index] if config else 1
			for i in range(count):
				suffix = f"{i + 1}" if count > 1 else ''
				wh_name = f"{process} Warehouse {suffix}".strip()
				warehouses.append({
					"warehouse_name": f"{wh_name} ({line['line_name']})",
					"production_line": line['line_code'],
					"warehouse_type": process,
					"process": process,
				})

	return warehouses
