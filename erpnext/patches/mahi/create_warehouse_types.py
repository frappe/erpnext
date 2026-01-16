import click
import frappe

from erpnext.stock.doctype.warehouse_type.constants import ALL_WAREHOUSE_TYPES


def execute():
	create_warehouse_types()


def create_warehouse_types():
	click.secho("Creating warehouse types...", fg="green")
	for warehouse_type_name in ALL_WAREHOUSE_TYPES: # Create all warehouse types including Silos, and Finished Goods
		warehouse_type = frappe.new_doc("Warehouse Type")
		warehouse_type.name = warehouse_type_name
		warehouse_type.save()
		click.secho(f"Created warehouse type for {warehouse_type_name}...", fg="blue")
