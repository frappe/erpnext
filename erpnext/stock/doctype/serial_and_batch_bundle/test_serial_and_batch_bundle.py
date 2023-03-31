# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.serial_batch_bundle import get_batch_nos, get_serial_nos


class TestSerialandBatchBundle(FrappeTestCase):
	pass


def get_batch_from_bundle(bundle):
	batches = get_batch_nos(bundle)

	return list(batches.keys())[0]


def get_serial_nos_from_bundle(bundle):
	return sorted(get_serial_nos(bundle))


def make_serial_batch_bundle(kwargs):
	from erpnext.stock.serial_batch_bundle import SerialBatchCreation

	sb = SerialBatchCreation(
		{
			"item_code": kwargs.item_code,
			"warehouse": kwargs.warehouse,
			"voucher_type": kwargs.voucher_type,
			"voucher_no": kwargs.voucher_no,
			"posting_date": kwargs.posting_date,
			"posting_time": kwargs.posting_time,
			"qty": kwargs.qty,
			"avg_rate": kwargs.rate,
			"batches": kwargs.batches,
			"serial_nos": kwargs.serial_nos,
			"type_of_transaction": "Inward" if kwargs.qty > 0 else "Outward",
			"company": kwargs.company or "_Test Company",
			"do_not_submit": kwargs.do_not_submit,
		}
	)

	if not kwargs.get("do_not_save"):
		return sb.make_serial_and_batch_bundle()

	return sb
