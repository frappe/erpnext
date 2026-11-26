import frappe
from frappe import _, bold
from frappe.model.naming import NamingSeries, parse_naming_series
from frappe.utils import cint, flt, getdate, now

from erpnext.stock.serial_batch_bundle.bundle_entries import get_serial_nos_batch
from erpnext.stock.serial_batch_identity import SerialBatchIdentity


class SerialBatchCreation:
	def __init__(self, args):
		self.set(args)
		self.set_item_details()
		self.set_other_details()

	def set(self, args):
		self.__dict__ = {}
		for key, value in args.items():
			setattr(self, key, value)
			self.__dict__[key] = value

	def get(self, key):
		return self.__dict__.get(key)

	def set_item_details(self):
		fields = [
			"has_batch_no",
			"has_serial_no",
			"item_name",
			"item_group",
			"serial_no_series",
			"create_new_batch",
			"batch_number_series",
			"description",
		]

		item_details = frappe.get_cached_value("Item", self.item_code, fields, as_dict=1)
		for key, value in item_details.items():
			setattr(self, key, value)

		self.__dict__.update(item_details)

	def set_other_details(self):
		from erpnext.stock.utils import get_combine_datetime

		if not self.get("posting_datetime"):
			if self.get("posting_date") and self.get("posting_time"):
				self.posting_datetime = get_combine_datetime(self.posting_date, self.posting_time)

		if not self.get("posting_datetime"):
			self.posting_datetime = now()
			self.__dict__["posting_datetime"] = self.posting_datetime

		if not self.get("actual_qty"):
			qty = self.get("qty") or self.get("total_qty")

			self.actual_qty = qty
			self.__dict__["actual_qty"] = self.actual_qty

		if not hasattr(self, "use_serial_batch_fields"):
			self.use_serial_batch_fields = 0

	def duplicate_package(self):
		if not self.serial_and_batch_bundle:
			return

		id = self.serial_and_batch_bundle
		package = frappe.get_doc("Serial and Batch Bundle", id)
		new_package = frappe.copy_doc(package, ignore_no_copy=False)

		if self.get("returned_serial_nos"):
			self.remove_returned_serial_nos(new_package)

		new_package.docstatus = 0
		new_package.warehouse = self.warehouse
		new_package.voucher_no = ""
		new_package.posting_datetime = self.posting_datetime if hasattr(self, "posting_datetime") else now()
		new_package.type_of_transaction = self.type_of_transaction
		new_package.returned_against = self.get("returned_against")

		if self.get("do_not_save"):
			return new_package

		new_package.save()

		self.serial_and_batch_bundle = new_package.name

	def remove_returned_serial_nos(self, package):
		remove_list = []
		for d in package.entries:
			if d.serial_no in self.returned_serial_nos:
				remove_list.append(d)

		for d in remove_list:
			package.remove(d)

	def make_serial_and_batch_bundle(
		self, serial_nos=None, batch_nos=None
	):  # passing None instead of [] due to ruff linter error B006
		serial_nos = serial_nos or []
		batch_nos = batch_nos or []

		doc = frappe.new_doc("Serial and Batch Bundle")
		valid_columns = doc.meta.get_valid_columns()
		for key, value in self.__dict__.items():
			if key in valid_columns:
				doc.set(key, value)

		if serial_nos:
			self.serial_nos = serial_nos
		if batch_nos:
			self.batches = batch_nos

		if self.type_of_transaction == "Outward":
			self.set_auto_serial_batch_entries_for_outward()
		elif self.type_of_transaction == "Inward":
			self.set_auto_serial_batch_entries_for_inward()
			self.add_serial_nos_for_batch_item()

		if hasattr(self, "via_landed_cost_voucher") and self.via_landed_cost_voucher:
			doc.flags.via_landed_cost_voucher = self.via_landed_cost_voucher

		self.set_serial_batch_entries(doc)
		if not doc.get("entries"):
			return frappe._dict({})

		if doc.voucher_no and frappe.get_cached_value(doc.voucher_type, doc.voucher_no, "docstatus") == 2:
			doc.voucher_no = ""

		doc.flags.ignore_validate_serial_batch = False
		if self.get("make_bundle_from_sle") and self.type_of_transaction == "Inward":
			doc.flags.ignore_validate_serial_batch = True

		if not hasattr(self, "do_not_submit") or not self.do_not_submit:
			doc.flags.ignore_voucher_validation = True
			if self.get("sle"):
				doc.flags.ignore_validate = True
				doc.save()
				self.sle.db_set("serial_and_batch_bundle", doc.name, update_modified=False)

			if doc.flags.ignore_validate:
				doc.flags.ignore_validate = False

			doc.submit()
		else:
			if self.get("ignore_sabb_validation"):
				doc.flags.ignore_validate = True

			doc.save()

		self.validate_qty(doc)

		return doc

	def add_serial_nos_for_batch_item(self):
		if not (self.has_serial_no and self.has_batch_no):
			return

		if not self.get("serial_nos") and self.get("batches"):
			batches = list(self.get("batches").keys())
			if len(batches) == 1:
				self.batch_no = batches[0]
				self.serial_nos = self.get_auto_created_serial_nos()

	def update_serial_and_batch_entries(
		self, serial_nos=None, batch_nos=None
	):  # passing None instead of [] due to ruff linter error B006
		serial_nos = serial_nos or []
		batch_nos = batch_nos or []

		doc = frappe.get_doc("Serial and Batch Bundle", self.serial_and_batch_bundle)
		doc.type_of_transaction = self.type_of_transaction
		doc.set("entries", [])

		if serial_nos:
			self.serial_nos = serial_nos
		if batch_nos:
			self.batches = batch_nos

		self.set_auto_serial_batch_entries_for_outward()
		self.set_serial_batch_entries(doc)
		if not doc.get("entries"):
			return frappe._dict({})

		doc.save()
		return doc

	def validate_qty(self, doc):
		if doc.type_of_transaction == "Outward" and self.actual_qty and doc.total_qty:
			precision = doc.precision("total_qty")

			total_qty = flt(abs(doc.total_qty), precision)
			required_qty = flt(abs(self.actual_qty), precision)

			if required_qty - total_qty > 0:
				msg = _(
					"For the item {0}, the Available qty {1} is less than the Required Qty {2} in the warehouse {3}. Please add sufficient qty in the warehouse."
				).format(bold(doc.item_code), bold(total_qty), bold(required_qty), bold(doc.warehouse))
				frappe.throw(msg, title=_("Insufficient Stock"))

	def set_auto_serial_batch_entries_for_outward(self):
		from erpnext.stock.doctype.batch.batch import get_available_batches
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos_for_outward

		kwargs = frappe._dict(
			{
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"company": self.get("company"),
				"qty": abs(self.actual_qty) if self.actual_qty else 0,
				"based_on": frappe.get_single_value("Stock Settings", "pick_serial_and_batch_based_on"),
			}
		)

		if self.get("ignore_serial_nos"):
			kwargs["ignore_serial_nos"] = self.ignore_serial_nos

		if self.get("already_picked_batches"):
			kwargs["already_picked_batches"] = self.already_picked_batches
			if self.get("voucher_type") == "POS Invoice":
				# a submitted POS Invoice's own reserved batch qty is already in already_picked_batches
				kwargs["ignore_voucher_nos"] = [self.voucher_no]

		kwargs.update(self.get_reservation_kwargs())

		if (
			self.has_serial_no
			and self.has_batch_no
			and not self.get("serial_nos")
			and self.get("batches")
			and len(self.get("batches")) == 1
		):
			# If only one batch is available and no serial no is available
			kwargs["batches"] = next(iter(self.get("batches").keys()))
			self.serial_nos = get_serial_nos_for_outward(kwargs)
		elif self.has_serial_no and not self.get("serial_nos"):
			self.serial_nos = get_serial_nos_for_outward(kwargs)
		elif not self.has_serial_no and self.has_batch_no and not self.get("batches"):
			if self.get("posting_datetime"):
				kwargs["posting_datetime"] = self.get("posting_datetime")

			self.batches = get_available_batches(kwargs)

	def get_reservation_kwargs(self):
		if self.get("voucher_type") not in ("Delivery Note", "Sales Invoice", "POS Invoice"):
			return {}

		return {
			"pick_reserved_items": True,
			"sabb_voucher_type": self.voucher_type,
			"sabb_voucher_no": self.get("voucher_no"),
			"sabb_voucher_detail_no": self.get("voucher_detail_no"),
		}

	def set_auto_serial_batch_entries_for_inward(self):
		if (self.get("batches") and self.has_batch_no) or (self.get("serial_nos") and self.has_serial_no):
			return

		self.batch_no = None
		if self.has_batch_no:
			self.batch_no = self.create_batch()

		if self.has_serial_no:
			self.serial_nos = self.get_auto_created_serial_nos()
		else:
			self.batches = frappe._dict({self.batch_no: abs(self.actual_qty)})

	def set_serial_batch_entries(self, doc):
		incoming_rate = self.get("incoming_rate")

		standard_rate = self.get_standard_cost_rate()
		if standard_rate is not None:
			# Standard Cost values every serial/batch at the same rate, so the bundle entries
			# must carry the standard rate (not the document/billed rate) to stay consistent
			# with the standard-valued Stock Ledger Entry.
			incoming_rate = standard_rate
			self.serial_nos_valuation = None
			self.batches_valuation = None

		precision = frappe.get_precision("Serial and Batch Entry", "qty")
		if self.get("serial_nos"):
			serial_no_wise_batch = frappe._dict({})
			if self.has_batch_no:
				serial_no_wise_batch = get_serial_nos_batch(self.serial_nos)

			qty = -1 if self.type_of_transaction == "Outward" else 1
			for serial_no in self.serial_nos:
				if self.get("serial_nos_valuation"):
					incoming_rate = self.get("serial_nos_valuation").get(serial_no)

				doc.append(
					"entries",
					{
						"serial_no": serial_no,
						"qty": qty,
						"batch_no": serial_no_wise_batch.get(serial_no) or self.get("batch_no"),
						"incoming_rate": incoming_rate,
					},
				)

		elif self.get("batches"):
			for batch_no, batch_qty in self.batches.items():
				if self.get("batches_valuation"):
					incoming_rate = self.get("batches_valuation").get(batch_no)

				doc.append(
					"entries",
					{
						"batch_no": batch_no,
						"qty": flt(batch_qty, precision)
						* (-1 if self.type_of_transaction == "Outward" else 1),
						"incoming_rate": incoming_rate,
					},
				)

	def get_standard_cost_rate(self):
		"""Return the standard valuation rate for the item if its valuation method is
		Standard Cost, else None — used to value bundle entries at standard."""
		from erpnext.stock.doctype.item_standard_cost.item_standard_cost import get_item_standard_rate
		from erpnext.stock.utils import get_valuation_method

		company = self.get("company")
		if not company and self.get("warehouse"):
			company = frappe.get_cached_value("Warehouse", self.warehouse, "company")

		if not company or get_valuation_method(self.item_code, company) != "Standard Cost":
			return None

		posting_date = self.get("posting_date")
		if not posting_date and self.get("posting_datetime"):
			posting_date = getdate(self.posting_datetime)

		return get_item_standard_rate(self.item_code, company, posting_date)

	def create_batch(self):
		from erpnext.stock.doctype.batch.batch import make_batch

		if hasattr(self, "is_rejected") and self.is_rejected:
			bundle = frappe.db.get_value(
				"Serial and Batch Bundle",
				{
					"voucher_no": self.voucher_no,
					"voucher_type": self.voucher_type,
					"voucher_detail_no": self.voucher_detail_no,
					"is_rejected": 0,
					"docstatus": 1,
					"is_cancelled": 0,
				},
				"name",
			)

			if bundle:
				if batch_no := frappe.db.get_value("Serial and Batch Entry", {"parent": bundle}, "batch_no"):
					return batch_no

		return make_batch(
			frappe._dict(
				{
					"item": self.get("item_code"),
					"reference_doctype": self.get("voucher_type"),
					"reference_name": self.get("voucher_no"),
				}
			)
		)

	def get_auto_created_serial_nos(self):
		sr_nos = []
		serial_nos_details = []

		if not self.serial_no_series:
			frappe.throw(
				_(
					"Please set Serial No Series in the item {0} or create Serial and Batch Bundle manually."
				).format(self.item_code)
			)

		voucher_no = ""
		if self.get("voucher_no"):
			voucher_no = self.get("voucher_no")

		voucher_type = ""
		if self.get("voucher_type"):
			voucher_type = self.get("voucher_type")

		serial_no_values = frappe._dict(
			warehouse=self.warehouse,
			company=self.company,
			item_code=self.item_code,
			item_name=self.item_name,
			description=self.description,
			status="Active",
			reference_doctype=voucher_type,
			reference_name=voucher_no,
			posting_date=frappe.db.get_value(voucher_type, voucher_no, "posting_date"),
			batch_no=self.batch_no,
		)

		obj = NamingSeries(self.serial_no_series)
		current_value = obj.get_current_value(serial_no_values)

		def get_series(partial_series, digits):
			return f"{current_value:0{digits}d}"

		serial_ids = SerialBatchIdentity("Serial No").get_new_names(abs(cint(self.actual_qty)))
		for serial_id in serial_ids:
			current_value += 1
			serial_no = parse_naming_series(
				self.serial_no_series, doc=serial_no_values, number_generator=get_series
			)

			sr_nos.append(serial_id)
			serial_nos_details.append(
				(
					serial_id,
					serial_no,
					now(),
					now(),
					frappe.session.user,
					frappe.session.user,
					*serial_no_values.values(),
				)
			)

		if serial_nos_details:
			fields = [
				"name",
				"serial_no",
				"creation",
				"modified",
				"owner",
				"modified_by",
				*serial_no_values,
			]

			try:
				frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))
			except Exception as error:
				SerialBatchIdentity("Serial No").raise_duplicate(
					error,
					self.item_code,
					message=_(
						"A naming series conflict occurred while creating serial numbers. Please change the naming series for the item {0}."
					).format(bold(self.item_code)),
				)
				raise

		obj.update_counter(current_value, serial_no_values)

		return sr_nos
