import click
import frappe

from erpnext.manufacturing.doctype.production_line.constants import CHILD_LINES, PARENT_LINES
from erpnext.manufacturing.doctype.production_line.production_line import ProductionLine


def execute():
	create_production_lines()

def create_production_lines():
	parent_production_lines = PARENT_LINES
	child_production_lines = CHILD_LINES

	click.secho("Creating production lines...", fg="green")
	for line in parent_production_lines:
		new_parent_line:ProductionLine = frappe.new_doc("Production Line")  # pyright: ignore[reportAssignmentType]
		new_parent_line.line_name = line["line_name"]
		new_parent_line.line_code = line["line_code"]
		new_parent_line.is_active = True
		new_parent_line.is_group = True
		new_parent_line.save()
		click.secho(f"Created line {new_parent_line.name}({new_parent_line.line_code})", fg="blue")

	for line in child_production_lines:
		new_child_line:ProductionLine = frappe.new_doc("Production Line")  # pyright: ignore[reportAssignmentType]
		new_child_line.line_name = line["line_name"]
		new_child_line.line_code = line["line_code"]
		new_child_line.is_active = True
		new_child_line.is_group = False
		new_child_line.parent_line = line["parent_line"]
		new_child_line.save()
		click.secho(f"Created line {new_child_line.name}({new_child_line.line_code}) under {new_child_line.parent_line}", fg="blue")

	click.secho("Created all production lines...", fg="green")
