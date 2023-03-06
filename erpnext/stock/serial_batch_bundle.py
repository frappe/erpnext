import frappe
from frappe.model.naming import make_autoname
from frappe.query_builder.functions import CombineDatetime, Sum
from frappe.utils import cint, cstr, flt, now

from erpnext.stock.valuation import round_off_if_near_zero


class SerialBatchBundle:
	def __init__(self, **kwargs):
		for key, value in kwargs.iteritems():
			setattr(self, key, value)

		self.set_item_details()

	def process_serial_and_batch_bundle(self):
		if self.item_details.has_serial_no:
			self.process_serial_no
		elif self.item_details.has_batch_no:
			self.process_batch_no

	def set_item_details(self):
		fields = [
			"has_batch_no",
			"has_serial_no",
			"item_name",
			"item_group",
			"serial_no_series",
			"create_new_batch",
			"batch_number_series",
		]

		self.item_details = frappe.get_cached_value("Item", self.sle.item_code, fields, as_dict=1)

	def process_serial_no(self):
		if (
			not self.sle.is_cancelled
			and not self.sle.serial_and_batch_bundle
			and self.sle.actual_qty > 0
			and self.item_details.has_serial_no == 1
			and self.item_details.serial_no_series
		):
			sr_nos = self.auto_create_serial_nos()
			self.make_serial_no_bundle(sr_nos)

	def auto_create_serial_nos(self):
		sr_nos = []
		serial_nos_details = []

		for i in range(cint(self.sle.actual_qty)):
			serial_no = make_autoname(self.item_details.serial_no_series, "Serial No")
			sr_nos.append(serial_no)
			serial_nos_details.append(
				(
					serial_no,
					serial_no,
					now(),
					now(),
					frappe.session.user,
					frappe.session.user,
					self.warehouse,
					self.company,
					self.item_code,
					self.item_details.item_name,
					self.item_details.description,
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
				"warehouse",
				"company",
				"item_code",
				"item_name",
				"description",
			]

			frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))

		return sr_nos

	def make_serial_no_bundle(self, serial_nos=None):
		sn_doc = frappe.new_doc("Serial and Batch Bundle")
		sn_doc.item_code = self.item_code
		sn_doc.item_name = self.item_details.item_name
		sn_doc.item_group = self.item_details.item_group
		sn_doc.has_serial_no = self.item_details.has_serial_no
		sn_doc.has_batch_no = self.item_details.has_batch_no
		sn_doc.voucher_type = self.sle.voucher_type
		sn_doc.voucher_no = self.sle.voucher_no
		sn_doc.flags.ignore_mandatory = True
		sn_doc.flags.ignore_validate = True
		sn_doc.total_qty = self.sle.actual_qty
		sn_doc.avg_rate = self.sle.incoming_rate
		sn_doc.total_amount = flt(self.sle.actual_qty) * flt(self.sle.incoming_rate)
		sn_doc.insert()

		batch_no = ""
		if self.item_details.has_batch_no:
			batch_no = self.create_batch()

		if serial_nos:
			self.add_serial_no_to_bundle(sn_doc, serial_nos, batch_no)
		elif self.item_details.has_batch_no:
			self.add_batch_no_to_bundle(sn_doc, batch_no)
			sn_doc.save()

		sn_doc.load_from_db()
		sn_doc.flags.ignore_validate = True
		sn_doc.flags.ignore_mandatory = True

		sn_doc.submit()

		self.sle.serial_and_batch_bundle = sn_doc.name

	def add_serial_no_to_bundle(self, sn_doc, serial_nos, batch_no=None):
		ledgers = []

		fields = [
			"name",
			"serial_no",
			"batch_no",
			"warehouse",
			"item_code",
			"qty",
			"incoming_rate",
			"parent",
			"parenttype",
			"parentfield",
		]

		for serial_no in serial_nos:
			ledgers.append(
				(
					frappe.generate_hash("Serial and Batch Ledger", 10),
					serial_no,
					batch_no,
					self.warehouse,
					self.item_details.item_code,
					1,
					self.sle.incoming_rate,
					sn_doc.name,
					sn_doc.doctype,
					"ledgers",
				)
			)

		frappe.db.bulk_insert("Serial and Batch Ledger", fields=fields, values=set(ledgers))

	def add_batch_no_to_bundle(self, sn_doc, batch_no):
		sn_doc.append(
			"ledgers",
			{
				"batch_no": batch_no,
				"qty": self.sle.actual_qty,
				"incoming_rate": self.sle.incoming_rate,
			},
		)

	def create_batch(self):
		from erpnext.stock.doctype.batch.batch import make_batch

		return make_batch(
			frappe._dict(
				{
					"item": self.item_code,
					"reference_doctype": self.sle.voucher_type,
					"reference_name": self.sle.voucher_no,
				}
			)
		)

	def process_batch_no(self):
		if (
			not self.sle.is_cancelled
			and not self.sle.serial_and_batch_bundle
			and self.sle.actual_qty > 0
			and self.item_details.has_batch_no == 1
			and self.item_details.create_new_batch
			and self.item_details.batch_number_series
		):
			self.make_serial_no_bundle()


class RepostSerialBatchBundle:
	def __init__(self, **kwargs):
		for key, value in kwargs.iteritems():
			setattr(self, key, value)

	def get_valuation_rate(self):
		if self.sle.actual_qty > 0:
			self.sle.incoming_rate = self.sle.valuation_rate

		if self.sle.actual_qty < 0:
			self.sle.outgoing_rate = self.sle.valuation_rate

	def get_valuation_rate_for_serial_nos(self):
		serial_nos = self.get_serial_nos()

		subquery = f"""
			SELECT
				MAX(ledger.posting_date), name
			FROM
				ledger
			WHERE
				ledger.serial_no IN {tuple(serial_nos)}
				AND ledger.is_outward = 0
				AND ledger.warehouse = {frappe.db.escape(self.sle.warehouse)}
				AND ledger.item_code = {frappe.db.escape(self.sle.item_code)}
				AND (
					ledger.posting_date < '{self.sle.posting_date}'
					OR (
						ledger.posting_date = '{self.sle.posting_date}'
						AND ledger.posting_time <= '{self.sle.posting_time}'
					)
				)
		"""

		frappe.db.sql(
			"""
			SELECT
				serial_no, incoming_rate
			FROM
				`tabSerial and Batch Ledger` AS ledger,
				({subquery}) AS SubQuery
			WHERE
				ledger.name = SubQuery.name
			GROUP BY
				ledger.serial_no
		"""
		)

	def get_serial_nos(self):
		ledgers = frappe.get_all(
			"Serial and Batch Ledger",
			fields=["serial_no"],
			filters={"parent": self.sle.serial_and_batch_bundle, "is_outward": 1},
		)

		return [d.serial_no for d in ledgers]


class DeprecatedRepostSerialBatchBundle(RepostSerialBatchBundle):
	def get_serialized_values(self, sle):
		incoming_rate = flt(sle.incoming_rate)
		actual_qty = flt(sle.actual_qty)
		serial_nos = cstr(sle.serial_no).split("\n")

		if incoming_rate < 0:
			# wrong incoming rate
			incoming_rate = self.wh_data.valuation_rate

		stock_value_change = 0
		if actual_qty > 0:
			stock_value_change = actual_qty * incoming_rate
		else:
			# In case of delivery/stock issue, get average purchase rate
			# of serial nos of current entry
			if not sle.is_cancelled:
				outgoing_value = self.get_incoming_value_for_serial_nos(sle, serial_nos)
				stock_value_change = -1 * outgoing_value
			else:
				stock_value_change = actual_qty * sle.outgoing_rate

		new_stock_qty = self.wh_data.qty_after_transaction + actual_qty

		if new_stock_qty > 0:
			new_stock_value = (
				self.wh_data.qty_after_transaction * self.wh_data.valuation_rate
			) + stock_value_change
			if new_stock_value >= 0:
				# calculate new valuation rate only if stock value is positive
				# else it remains the same as that of previous entry
				self.wh_data.valuation_rate = new_stock_value / new_stock_qty

		if not self.wh_data.valuation_rate and sle.voucher_detail_no:
			allow_zero_rate = self.check_if_allow_zero_valuation_rate(
				sle.voucher_type, sle.voucher_detail_no
			)
			if not allow_zero_rate:
				self.wh_data.valuation_rate = self.get_fallback_rate(sle)

	def get_incoming_value_for_serial_nos(self, sle, serial_nos):
		# get rate from serial nos within same company
		all_serial_nos = frappe.get_all(
			"Serial No", fields=["purchase_rate", "name", "company"], filters={"name": ("in", serial_nos)}
		)

		incoming_values = sum(flt(d.purchase_rate) for d in all_serial_nos if d.company == sle.company)

		# Get rate for serial nos which has been transferred to other company
		invalid_serial_nos = [d.name for d in all_serial_nos if d.company != sle.company]
		for serial_no in invalid_serial_nos:
			incoming_rate = frappe.db.sql(
				"""
				select incoming_rate
				from `tabStock Ledger Entry`
				where
					company = %s
					and actual_qty > 0
					and is_cancelled = 0
					and (serial_no = %s
						or serial_no like %s
						or serial_no like %s
						or serial_no like %s
					)
				order by posting_date desc
				limit 1
			""",
				(sle.company, serial_no, serial_no + "\n%", "%\n" + serial_no, "%\n" + serial_no + "\n%"),
			)

			incoming_values += flt(incoming_rate[0][0]) if incoming_rate else 0

		return incoming_values

	def update_batched_values(self, sle):
		incoming_rate = flt(sle.incoming_rate)
		actual_qty = flt(sle.actual_qty)

		self.wh_data.qty_after_transaction = round_off_if_near_zero(
			self.wh_data.qty_after_transaction + actual_qty
		)

		if actual_qty > 0:
			stock_value_difference = incoming_rate * actual_qty
		else:
			outgoing_rate = get_batch_incoming_rate(
				item_code=sle.item_code,
				warehouse=sle.warehouse,
				batch_no=sle.batch_no,
				posting_date=sle.posting_date,
				posting_time=sle.posting_time,
				creation=sle.creation,
			)
			if outgoing_rate is None:
				# This can *only* happen if qty available for the batch is zero.
				# in such case fall back various other rates.
				# future entries will correct the overall accounting as each
				# batch individually uses moving average rates.
				outgoing_rate = self.get_fallback_rate(sle)
			stock_value_difference = outgoing_rate * actual_qty

		self.wh_data.stock_value = round_off_if_near_zero(
			self.wh_data.stock_value + stock_value_difference
		)
		if self.wh_data.qty_after_transaction:
			self.wh_data.valuation_rate = self.wh_data.stock_value / self.wh_data.qty_after_transaction


def get_batch_incoming_rate(
	item_code, warehouse, batch_no, posting_date, posting_time, creation=None
):

	sle = frappe.qb.DocType("Stock Ledger Entry")

	timestamp_condition = CombineDatetime(sle.posting_date, sle.posting_time) < CombineDatetime(
		posting_date, posting_time
	)
	if creation:
		timestamp_condition |= (
			CombineDatetime(sle.posting_date, sle.posting_time)
			== CombineDatetime(posting_date, posting_time)
		) & (sle.creation < creation)

	batch_details = (
		frappe.qb.from_(sle)
		.select(Sum(sle.stock_value_difference).as_("batch_value"), Sum(sle.actual_qty).as_("batch_qty"))
		.where(
			(sle.item_code == item_code)
			& (sle.warehouse == warehouse)
			& (sle.batch_no == batch_no)
			& (sle.is_cancelled == 0)
		)
		.where(timestamp_condition)
	).run(as_dict=True)

	if batch_details and batch_details[0].batch_qty:
		return batch_details[0].batch_value / batch_details[0].batch_qty
