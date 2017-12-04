from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.setup.utils import insert_record

def setup_agriculture():
	records = [
		dict(
			doctype="Land Unit",
			land_unit_name="All Land Units",
			is_group=1,
			is_container=1),
		dict(
			doctype='Item Group',
			item_group_name='Fertilizer',
			is_group=0,
			parent_item_group=_('All Item Groups')),
		dict(
			doctype='Item Group',
			item_group_name='Seed',
			is_group=0,
			parent_item_group=_('All Item Groups')),
		dict(
			doctype='Item Group',
			item_group_name='By-product',
			is_group=0,
			parent_item_group=_('All Item Groups')),
		dict(
			doctype='Item Group',
			item_group_name='Produce',
			is_group=0,
			parent_item_group=_('All Item Groups'))
	] 
	insert_record(records)