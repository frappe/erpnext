# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from typing import TYPE_CHECKING, Dict, Optional, Union

if TYPE_CHECKING:
	from erpnext.manufacturing.doctype.bom_update_log.bom_update_log import BOMUpdateLog

import frappe
from frappe.model.document import Document
<<<<<<< HEAD
from frappe.utils import cstr, flt
from six import string_types
=======
>>>>>>> f3715ab382 (fix: Test, Sider and Added button to access log from Tool)

from erpnext.manufacturing.doctype.bom.bom import get_boms_in_bottom_up_order


class BOMUpdateTool(Document):
<<<<<<< HEAD
	def replace_bom(self):
		unit_cost = get_new_bom_unit_cost(self.new_bom)
		self.update_new_bom(unit_cost)

		frappe.cache().delete_key("bom_children")
		bom_list = self.get_parent_boms(self.new_bom)

		with click.progressbar(bom_list) as bom_list:
			pass
		for bom in bom_list:
			try:
				bom_obj = frappe.get_cached_doc("BOM", bom)
				# this is only used for versioning and we do not want
				# to make separate db calls by using load_doc_before_save
				# which proves to be expensive while doing bulk replace
				bom_obj._doc_before_save = bom_obj
				bom_obj.update_new_bom(self.current_bom, self.new_bom, unit_cost)
				bom_obj.update_exploded_items()
				bom_obj.calculate_cost()
				bom_obj.update_parent_cost()
				bom_obj.db_update()
				if bom_obj.meta.get("track_changes") and not bom_obj.flags.ignore_version:
					bom_obj.save_version()
			except Exception:
				frappe.log_error(frappe.get_traceback())

<<<<<<< HEAD
	def validate_bom(self):
		if cstr(self.current_bom) == cstr(self.new_bom):
			frappe.throw(_("Current BOM and New BOM can not be same"))

		if frappe.db.get_value("BOM", self.current_bom, "item") != frappe.db.get_value(
			"BOM", self.new_bom, "item"
		):
			frappe.throw(_("The selected BOMs are not for the same item"))

=======
>>>>>>> 4283a13e5a (feat: BOM Update Log)
	def update_new_bom(self, unit_cost):
		frappe.db.sql(
			"""update `tabBOM Item` set bom_no=%s,
			rate=%s, amount=stock_qty*%s where bom_no = %s and docstatus < 2 and parenttype='BOM'""",
			(self.new_bom, unit_cost, unit_cost, self.current_bom),
		)

	def get_parent_boms(self, bom, bom_list=None):
		if bom_list is None:
			bom_list = []
		data = frappe.db.sql(
			"""SELECT DISTINCT parent FROM `tabBOM Item`
			WHERE bom_no = %s AND docstatus < 2 AND parenttype='BOM'""",
			bom,
		)

		for d in data:
			if self.new_bom == d[0]:
				frappe.throw(_("BOM recursion: {0} cannot be child of {1}").format(bom, self.new_bom))

			bom_list.append(d[0])
			self.get_parent_boms(d[0], bom_list)

		return list(set(bom_list))


def get_new_bom_unit_cost(bom):
	new_bom_unitcost = frappe.db.sql(
		"""SELECT `total_cost`/`quantity`
		FROM `tabBOM` WHERE name = %s""",
		bom,
	)

	return flt(new_bom_unitcost[0][0]) if new_bom_unitcost else 0
=======
	pass
>>>>>>> cff91558d4 (chore: Polish error handling and code sepration)


@frappe.whitelist()
<<<<<<< HEAD
def enqueue_replace_bom(args):
	if isinstance(args, string_types):
		args = json.loads(args)

<<<<<<< HEAD
	frappe.enqueue(
		"erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.replace_bom",
		args=args,
		timeout=40000,
	)
=======
	create_bom_update_log(boms=args)
>>>>>>> 4283a13e5a (feat: BOM Update Log)
	frappe.msgprint(_("Queued for replacing the BOM. It may take a few minutes."))
=======
def enqueue_replace_bom(boms: Optional[Union[Dict, str]] = None, args: Optional[Union[Dict, str]] = None) -> "BOMUpdateLog":
	"""Returns a BOM Update Log (that queues a job) for BOM Replacement."""
	boms = boms or args
	if isinstance(boms, str):
		boms = json.loads(boms)
>>>>>>> cff91558d4 (chore: Polish error handling and code sepration)

	update_log = create_bom_update_log(boms=boms)
	return update_log

@frappe.whitelist()
<<<<<<< HEAD
def enqueue_update_cost():
<<<<<<< HEAD
	frappe.enqueue(
		"erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.update_cost", timeout=40000
	)
	frappe.msgprint(
		_("Queued for updating latest price in all Bill of Materials. It may take a few minutes.")
	)

=======
	create_bom_update_log(update_type="Update Cost")
	frappe.msgprint(_("Queued for updating latest price in all Bill of Materials. It may take a few minutes."))
>>>>>>> 4283a13e5a (feat: BOM Update Log)
=======
def enqueue_update_cost() -> "BOMUpdateLog":
	"""Returns a BOM Update Log (that queues a job) for BOM Cost Updation."""
	update_log = create_bom_update_log(update_type="Update Cost")
	return update_log
>>>>>>> cff91558d4 (chore: Polish error handling and code sepration)


def auto_update_latest_price_in_all_boms() -> None:
	"""Called via hooks.py."""
	if frappe.db.get_single_value("Manufacturing Settings", "update_bom_costs_automatically"):
		update_cost()

<<<<<<< HEAD
<<<<<<< HEAD

def replace_bom(args):
	try:
		frappe.db.auto_commit_on_many_writes = 1
		args = frappe._dict(args)
		doc = frappe.get_doc("BOM Update Tool")
		doc.current_bom = args.current_bom
		doc.new_bom = args.new_bom
		doc.replace_bom()
	except Exception:
		frappe.log_error(
			msg=frappe.get_traceback(),
			title=_("BOM Update Tool Error")
		)
	finally:
		frappe.db.auto_commit_on_many_writes = 0


def update_cost():
	try:
		frappe.db.auto_commit_on_many_writes = 1
		bom_list = get_boms_in_bottom_up_order()
		for bom in bom_list:
			frappe.get_doc("BOM", bom).update_cost(update_parent=False, from_child_bom=True)
	except Exception:
		frappe.log_error(
			msg=frappe.get_traceback(),
			title=_("BOM Update Tool Error")
		)
	finally:
		frappe.db.auto_commit_on_many_writes = 0
=======
def create_bom_update_log(boms=None, update_type="Replace BOM"):
	"Creates a BOM Update Log that handles the background job."
	current_bom = boms.get("current_bom") if boms else None
	new_bom = boms.get("new_bom") if boms else None
	log_doc = frappe.get_doc({
		"doctype": "BOM Update Log",
		"current_bom": current_bom,
		"new_bom": new_bom,
		"update_type": update_type
	})
	log_doc.submit()
>>>>>>> 4283a13e5a (feat: BOM Update Log)
=======
def update_cost() -> None:
	"""Updates Cost for all BOMs from bottom to top."""
	bom_list = get_boms_in_bottom_up_order()
	for bom in bom_list:
		frappe.get_doc("BOM", bom).update_cost(update_parent=False, from_child_bom=True)

def create_bom_update_log(boms: Optional[Dict] = None, update_type: str = "Replace BOM") -> "BOMUpdateLog":
	"""Creates a BOM Update Log that handles the background job."""
	boms = boms or {}
	current_bom = boms.get("current_bom")
	new_bom = boms.get("new_bom")
	return frappe.get_doc({
		"doctype": "BOM Update Log",
		"current_bom": current_bom,
		"new_bom": new_bom,
		"update_type": update_type,
	}).submit()
>>>>>>> cff91558d4 (chore: Polish error handling and code sepration)
