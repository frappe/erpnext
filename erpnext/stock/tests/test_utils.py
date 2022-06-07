import json

import frappe


class StockTestMixin:
	"""Mixin to simplfy stock ledger tests, useful for all stock transactions."""

	def make_item(self, item_code=None, properties=None, *args, **kwargs):
		from erpnext.stock.doctype.item.test_item import make_item

		return make_item(item_code, properties, *args, **kwargs)

	def assertSLEs(self, doc, expected_sles, sle_filters=None):
		"""Compare sorted SLEs, useful for vouchers that create multiple SLEs for same line"""

		filters = {"voucher_no": doc.name, "voucher_type": doc.doctype, "is_cancelled": 0}
		if sle_filters:
			filters.update(sle_filters)
		sles = frappe.get_all(
			"Stock Ledger Entry",
			fields=["*"],
			filters=filters,
			order_by="timestamp(posting_date, posting_time), creation",
		)

		for exp_sle, act_sle in zip(expected_sles, sles):
			for k, v in exp_sle.items():
				act_value = act_sle[k]
				if k == "stock_queue":
					act_value = json.loads(act_value)
					if act_value and act_value[0][0] == 0:
						# ignore empty fifo bins
						continue

				self.assertEqual(v, act_value, msg=f"{k} doesn't match \n{exp_sle}\n{act_sle}")

	def assertGLEs(self, doc, expected_gles, gle_filters=None, order_by=None):
		filters = {"voucher_no": doc.name, "voucher_type": doc.doctype, "is_cancelled": 0}

		if gle_filters:
			filters.update(gle_filters)
		actual_gles = frappe.get_all(
			"GL Entry",
			fields=["*"],
			filters=filters,
			order_by=order_by or "posting_date, creation",
		)

		for exp_gle, act_gle in zip(expected_gles, actual_gles):
			for k, exp_value in exp_gle.items():
				act_value = act_gle[k]
				self.assertEqual(exp_value, act_value, msg=f"{k} doesn't match \n{exp_gle}\n{act_gle}")
