# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.utils import (
	_check_batch_availability_warn,
	_check_credit_limit_warn,
	_check_packed_qty_warn,
	_check_serial_no_availability_warn,
	_check_stock_availability_warn,
	_check_stock_conditions_warn,
)
from erpnext.selling.doctype.customer.test_customer import (
	get_customer_dict,
	set_credit_limit,
)
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
CREDIT_LIMIT = 100.0
OVER = 200.0
UNDER = 50.0


def _make_customer(name):
	if not frappe.db.exists("Customer", name):
		frappe.get_doc({**get_customer_dict(name), "customer_name": name}).insert()
	return name


def _get_orange_warnings():
	return [m for m in frappe.message_log if m.get("indicator") == "orange"]


class _CreditLimitBase(ERPNextTestSuite):
	CUSTOMER = "_Pre Submit Test Customer"

	def setUp(self):
		_make_customer(self.CUSTOMER)
		set_credit_limit(self.CUSTOMER, COMPANY, CREDIT_LIMIT)
		frappe.message_log.clear()


class TestCreditLimitWarnSalesInvoice(_CreditLimitBase):
	def _make_si(self, amount, is_return=0):
		"""Build an in-memory (unsaved) draft SI."""
		si = frappe.new_doc("Sales Invoice")
		si.company = COMPANY
		si.customer = self.CUSTOMER
		si.is_return = is_return
		si.base_grand_total = amount
		si.append("items", {"item_code": "_Test Item", "qty": 1, "rate": amount})
		return si

	def test_warns_when_amount_exceeds_credit_limit(self):
		"""Orange warning must appear when base_grand_total > credit_limit."""
		si = self._make_si(OVER)
		_check_credit_limit_warn(si)
		self.assertTrue(_get_orange_warnings(), "Expected an orange credit-limit warning")

	def test_no_warning_when_amount_within_credit_limit(self):
		"""No warning when base_grand_total is safely within the credit limit."""
		si = self._make_si(UNDER)
		_check_credit_limit_warn(si)
		self.assertFalse(_get_orange_warnings())

	def test_no_warning_for_return_invoices(self):
		"""Credit limit check is skipped entirely for return transactions."""
		si = self._make_si(OVER, is_return=1)
		_check_credit_limit_warn(si)
		self.assertFalse(_get_orange_warnings())

	def test_no_warning_when_customer_has_no_credit_limit(self):
		"""If the customer has no credit limit configured, no warning is shown."""
		frappe.db.delete("Customer Credit Limit", {"parent": self.CUSTOMER})
		si = self._make_si(OVER)
		_check_credit_limit_warn(si)
		self.assertFalse(_get_orange_warnings())

	def test_no_warning_when_all_items_linked_to_so_or_dn(self):
		"""
		When every item on the SI already has a sales_order or delivery_note
		reference, the check is skipped (the SO/DN already counted this amount).
		"""
		si = self._make_si(OVER)
		si.items[0].sales_order = "SO-TEST-0001"
		_check_credit_limit_warn(si)
		self.assertFalse(_get_orange_warnings())


class TestCreditLimitWarnSalesOrder(_CreditLimitBase):
	def _make_so(self, amount):
		"""Build an in-memory (unsaved) draft SO."""
		so = frappe.new_doc("Sales Order")
		so.company = COMPANY
		so.customer = self.CUSTOMER
		so.base_grand_total = amount
		so.append("items", {"item_code": "_Test Item", "qty": 1, "rate": amount})
		return so

	def test_warns_on_first_save_when_limit_exceeded(self):
		so = self._make_so(OVER)
		self.assertTrue(so.is_new(), "Doc should be new (not yet in DB)")
		_check_credit_limit_warn(so)
		self.assertTrue(_get_orange_warnings())

	def test_warns_when_amount_exceeds_credit_limit(self):
		so = self._make_so(OVER)
		_check_credit_limit_warn(so)
		self.assertTrue(_get_orange_warnings())

	def test_no_warning_when_amount_within_credit_limit(self):
		so = self._make_so(UNDER)
		_check_credit_limit_warn(so)
		self.assertFalse(_get_orange_warnings())

	def test_no_warning_when_bypass_is_set(self):
		"""
		When bypass_credit_limit_check=1 on the Customer Credit Limit row,
		SO's check_credit_limit skips entirely.
		"""
		frappe.db.set_value(
			"Customer Credit Limit",
			{"parent": self.CUSTOMER, "company": COMPANY},
			"bypass_credit_limit_check",
			1,
		)
		so = self._make_so(OVER)
		_check_credit_limit_warn(so)
		self.assertFalse(_get_orange_warnings())


class TestCreditLimitWarnDeliveryNote(_CreditLimitBase):
	def _make_dn(self, amount, bypass=False, against_sales_order=None, against_sales_invoice=None):
		"""Build an in-memory (unsaved) draft DN."""
		dn = frappe.new_doc("Delivery Note")
		dn.company = COMPANY
		dn.customer = self.CUSTOMER
		dn.base_grand_total = amount
		dn.base_net_total = amount
		item = {
			"item_code": "_Test Item",
			"qty": 1,
			"rate": amount,
			"amount": amount,
			"base_amount": amount,
		}
		if against_sales_order:
			item["against_sales_order"] = against_sales_order
		if against_sales_invoice:
			item["against_sales_invoice"] = against_sales_invoice
		dn.append("items", item)

		if bypass:
			frappe.db.set_value(
				"Customer Credit Limit",
				{"parent": self.CUSTOMER, "company": COMPANY},
				"bypass_credit_limit_check",
				1,
			)

		return dn

	# bypass=False (default) ------------------------------------------------

	def test_bypass_false_warns_for_existing_draft(self):
		"""bypass=False, existing draft: proportional extra_amount path still applies."""
		dn = self._make_dn(OVER)
		_check_credit_limit_warn(dn)
		self.assertTrue(_get_orange_warnings())

	def test_bypass_false_no_warning_when_under_limit(self):
		dn = self._make_dn(UNDER)
		_check_credit_limit_warn(dn)
		self.assertFalse(_get_orange_warnings())

	def test_bypass_false_no_warning_when_all_items_linked_to_so(self):
		"""
		Items fully linked to a SO are excluded from unlinked_net.
		extra_amount becomes 0 → check is skipped.
		"""
		dn = self._make_dn(OVER, against_sales_order="SO-TEST-0001")
		_check_credit_limit_warn(dn)
		self.assertFalse(_get_orange_warnings())

	def test_bypass_false_partial_link_warns_proportionally(self):
		"""
		Two items: one linked to SO, one unlinked.
		Only the unlinked portion should count toward the credit limit check.
		"""
		dn = frappe.new_doc("Delivery Note")
		dn.company = COMPANY
		dn.customer = self.CUSTOMER
		dn.append("items", {"item_code": "_Test Item", "qty": 1, "rate": 60, "amount": 60, "base_amount": 60})
		dn.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"rate": 50,
				"amount": 50,
				"base_amount": 50,
				"against_sales_order": "SO-TEST-0001",
			},
		)
		dn.base_net_total = 110
		dn.base_grand_total = 110

		_check_credit_limit_warn(dn)
		self.assertFalse(_get_orange_warnings(), "60 < 100 credit limit, should not warn")

	# bypass=True -----------------------------------------------------------

	def test_bypass_true_warns_on_first_save_new_doc(self):
		"""
		bypass=True: existing doc.check_credit_limit() handles extra_amount
		internally (base_grand_total for items not against SI).
		"""
		dn = self._make_dn(OVER, bypass=True)
		self.assertTrue(dn.is_new())
		_check_credit_limit_warn(dn)
		self.assertTrue(_get_orange_warnings())

	def test_bypass_true_no_warning_when_all_items_billed(self):
		"""
		bypass=True: items already linked to a SI are excluded from extra_amount.
		If all items have against_sales_invoice set, extra_amount=0 → no check.
		"""
		dn = self._make_dn(OVER, bypass=True, against_sales_invoice="SINV-TEST-0001")
		_check_credit_limit_warn(dn)
		self.assertFalse(_get_orange_warnings())


# ---------------------------------------------------------------------------
# Shared base for all stock-related tests
# ---------------------------------------------------------------------------

_ITEM = "_Test Item"
_WAREHOUSE = "_Test Warehouse - _TC"
_LARGE_QTY = 9999  # reliably exceeds any seeded test stock


class _StockDocBase(ERPNextTestSuite):
	"""Factory methods shared by all stock pre-submit test classes."""

	def setUp(self):
		frappe.message_log.clear()
		frappe.db.set_value("Stock Settings", "Stock Settings", "allow_negative_stock", 0)

	def _make_dn(self, qty=5, is_return=0, **item_fields):
		dn = frappe.new_doc("Delivery Note")
		dn.company = COMPANY
		dn.customer = "_Test Customer"
		dn.is_return = is_return
		dn.append(
			"items",
			{
				"item_code": _ITEM,
				"qty": qty,
				"stock_qty": qty,
				"warehouse": _WAREHOUSE,
				"rate": 100,
				**item_fields,
			},
		)
		return dn

	def _make_si(self, qty=5, update_stock=1, is_return=0, **item_fields):
		si = frappe.new_doc("Sales Invoice")
		si.company = COMPANY
		si.customer = "_Test Customer"
		si.update_stock = update_stock
		si.is_return = is_return
		si.append(
			"items",
			{
				"item_code": _ITEM,
				"qty": qty,
				"stock_qty": qty,
				"warehouse": _WAREHOUSE,
				"rate": 100,
				**item_fields,
			},
		)
		return si

	def _make_pr(self, qty=5, is_return=0, **item_fields):
		pr = frappe.new_doc("Purchase Receipt")
		pr.company = COMPANY
		pr.supplier = "_Test Supplier"
		pr.is_return = is_return
		pr.append(
			"items",
			{
				"item_code": _ITEM,
				"qty": qty,
				"stock_qty": qty,
				"warehouse": _WAREHOUSE,
				"rate": 100,
				**item_fields,
			},
		)
		return pr

	def _make_serial_no(self, warehouse=None):
		sn = frappe.get_doc(
			{
				"doctype": "Serial No",
				"serial_no": f"TEST-PSV-{frappe.generate_hash(length=8)}",
				"item_code": _ITEM,
				"company": COMPANY,
			}
		).insert(ignore_permissions=True)
		target = warehouse or _WAREHOUSE
		frappe.db.set_value("Serial No", sn.name, "warehouse", target)
		sn.warehouse = target
		return sn

	def _make_batch(self, expiry_date=None):
		frappe.db.set_value("Item", _ITEM, "has_batch_no", 1)
		batch = frappe.get_doc(
			{
				"doctype": "Batch",
				"batch_id": f"TEST-PSV-{frappe.generate_hash(length=8)}",
				"item": _ITEM,
			}
		)
		if expiry_date:
			batch.expiry_date = expiry_date
		return batch.insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Packed Qty
# ---------------------------------------------------------------------------


class TestPackedQtyWarn(_StockDocBase):
	def test_no_warning_for_new_doc(self):
		"""New doc has no packing slip in DB, so validate_packed_qty is skipped."""
		dn = self._make_dn(qty=2, amount=200, base_amount=200)
		_check_packed_qty_warn(dn)
		self.assertFalse(_get_orange_warnings())

	def test_warns_when_packed_qty_mismatches(self):
		"""When validate_packed_qty raises, an orange warning is produced."""
		dn = self._make_dn()
		with patch.object(
			dn,
			"validate_packed_qty",
			side_effect=frappe.ValidationError("Packed Qty must be equal to qty"),
		):
			_check_packed_qty_warn(dn)
		self.assertTrue(_get_orange_warnings())

	def test_no_warning_when_packed_qty_matches(self):
		"""When validate_packed_qty passes silently, no warning is produced."""
		dn = self._make_dn()
		with patch.object(dn, "validate_packed_qty", return_value=None):
			_check_packed_qty_warn(dn)
		self.assertFalse(_get_orange_warnings())


# ---------------------------------------------------------------------------
# Stock Availability
# ---------------------------------------------------------------------------


class TestStockAvailabilityWarn(_StockDocBase):
	# --- DN ---

	def test_dn_no_warning_when_sufficient_stock(self):
		make_stock_entry(item_code=_ITEM, target=_WAREHOUSE, qty=9999, basic_rate=100)
		_check_stock_availability_warn(self._make_dn(qty=10))
		self.assertFalse(_get_orange_warnings())

	def test_dn_warns_when_insufficient_stock(self):
		_check_stock_availability_warn(self._make_dn(qty=_LARGE_QTY))
		self.assertTrue(_get_orange_warnings())

	def test_dn_return_skipped(self):
		"""Return DNs add stock back — no availability check."""
		_check_stock_availability_warn(self._make_dn(qty=_LARGE_QTY, is_return=1))
		self.assertFalse(_get_orange_warnings())

	def test_dn_skipped_when_negative_stock_allowed(self):
		frappe.db.set_value("Stock Settings", "Stock Settings", "allow_negative_stock", 1)
		_check_stock_availability_warn(self._make_dn(qty=_LARGE_QTY))
		self.assertFalse(_get_orange_warnings())

	# --- SI ---

	def test_si_warns_when_update_stock_and_insufficient(self):
		_check_stock_availability_warn(self._make_si(qty=_LARGE_QTY, update_stock=1))
		self.assertTrue(_get_orange_warnings())

	def test_si_skipped_when_no_update_stock(self):
		_check_stock_availability_warn(self._make_si(qty=_LARGE_QTY, update_stock=0))
		self.assertFalse(_get_orange_warnings())

	def test_si_return_skipped(self):
		_check_stock_availability_warn(self._make_si(qty=_LARGE_QTY, update_stock=1, is_return=1))
		self.assertFalse(_get_orange_warnings())

	# --- PR return ---

	def test_pr_return_warns_when_insufficient_stock(self):
		"""PR return takes stock back out of the warehouse."""
		_check_stock_availability_warn(self._make_pr(qty=_LARGE_QTY, is_return=1))
		self.assertTrue(_get_orange_warnings())

	def test_pr_normal_skipped(self):
		_check_stock_availability_warn(self._make_pr(qty=_LARGE_QTY, is_return=0))
		self.assertFalse(_get_orange_warnings())


# ---------------------------------------------------------------------------
# Stock Conditions (freeze, warehouse, batch expiry)
# ---------------------------------------------------------------------------


class TestStockConditionsWarn(_StockDocBase):
	def setUp(self):
		super().setUp()
		frappe.db.set_value("Stock Settings", "Stock Settings", "stock_frozen_upto", None)
		frappe.db.set_value("Stock Settings", "Stock Settings", "stock_frozen_upto_days", 0)

	def test_no_warning_when_stock_not_frozen(self):
		_check_stock_conditions_warn(self._make_dn())
		self.assertFalse(_get_orange_warnings())

	def test_warns_when_posting_date_before_frozen_upto(self):
		"""Freeze date in the future, auth role cleared so any user is blocked."""
		frappe.db.set_value("Stock Settings", "Stock Settings", "stock_frozen_upto", "2099-12-31")
		frappe.db.set_value("Stock Settings", "Stock Settings", "stock_auth_role", "")
		_check_stock_conditions_warn(self._make_dn())
		self.assertTrue(_get_orange_warnings())

	def test_warns_for_group_warehouse(self):
		group_wh = frappe.db.get_value("Warehouse", {"is_group": 1, "company": COMPANY}, "name")
		if not group_wh:
			return
		_check_stock_conditions_warn(self._make_dn(warehouse=group_wh))
		self.assertTrue(_get_orange_warnings())

	def test_warns_for_disabled_warehouse(self):
		frappe.db.set_value("Warehouse", _WAREHOUSE, "disabled", 1)
		_check_stock_conditions_warn(self._make_dn())
		self.assertTrue(_get_orange_warnings())

	def test_no_warning_for_enabled_warehouse(self):
		_check_stock_conditions_warn(self._make_dn())
		self.assertFalse(_get_orange_warnings())

	def test_warns_when_batch_expired(self):
		batch = self._make_batch(expiry_date="2000-01-01")
		_check_stock_conditions_warn(self._make_dn(batch_no=batch.name))
		self.assertTrue(_get_orange_warnings())

	def test_no_warning_when_batch_not_expired(self):
		batch = self._make_batch(expiry_date="2099-12-31")
		_check_stock_conditions_warn(self._make_dn(batch_no=batch.name))
		self.assertFalse(_get_orange_warnings())

	def test_batch_expiry_skipped_for_inbound_pr(self):
		"""PR receives stock — batch expiry is only checked for outbound."""
		batch = self._make_batch(expiry_date="2000-01-01")
		_check_stock_conditions_warn(self._make_pr(batch_no=batch.name))
		self.assertFalse(_get_orange_warnings())

	def test_skipped_for_non_stock_doc(self):
		so = frappe.new_doc("Sales Order")
		so.company = COMPANY
		_check_stock_conditions_warn(so)
		self.assertFalse(_get_orange_warnings())


# ---------------------------------------------------------------------------
# Serial No Availability
# ---------------------------------------------------------------------------


class TestSerialNoAvailabilityWarn(_StockDocBase):
	def test_warns_when_serial_no_in_wrong_warehouse(self):
		sn = self._make_serial_no(warehouse="_Test Warehouse 1 - _TC")
		_check_serial_no_availability_warn(self._make_dn(qty=1, serial_no=sn.name))
		self.assertTrue(_get_orange_warnings())

	def test_no_warning_when_serial_no_in_correct_warehouse(self):
		sn = self._make_serial_no(warehouse=_WAREHOUSE)
		_check_serial_no_availability_warn(self._make_dn(qty=1, serial_no=sn.name))
		self.assertFalse(_get_orange_warnings())

	def test_skipped_for_inbound_pr(self):
		"""Normal PR adds stock — serial no availability is irrelevant."""
		sn = self._make_serial_no(warehouse="_Test Warehouse 1 - _TC")
		_check_serial_no_availability_warn(self._make_pr(qty=1, serial_no=sn.name))
		self.assertFalse(_get_orange_warnings())

	def test_no_warning_when_no_serial_no_on_items(self):
		_check_serial_no_availability_warn(self._make_dn(qty=1))
		self.assertFalse(_get_orange_warnings())


# ---------------------------------------------------------------------------
# Batch Availability
# ---------------------------------------------------------------------------


class TestBatchAvailabilityWarn(_StockDocBase):
	def test_warns_when_batch_qty_insufficient(self):
		"""Batch exists but no stock added → get_batch_qty returns 0 → warn."""
		batch = self._make_batch()
		_check_batch_availability_warn(self._make_dn(qty=5, batch_no=batch.name))
		self.assertTrue(_get_orange_warnings())

	def test_no_warning_when_batch_qty_sufficient(self):
		frappe.db.set_value("Item", _ITEM, "has_batch_no", 1)
		batch = self._make_batch()
		make_stock_entry(item_code=_ITEM, target=_WAREHOUSE, qty=50, basic_rate=100, batch_no=batch.name)
		_check_batch_availability_warn(self._make_dn(qty=10, batch_no=batch.name))
		self.assertFalse(_get_orange_warnings())

	def test_skipped_for_inbound_pr(self):
		"""Normal PR receives stock — batch availability check skipped."""
		batch = self._make_batch()
		_check_batch_availability_warn(self._make_pr(qty=5, batch_no=batch.name))
		self.assertFalse(_get_orange_warnings())

	def test_no_warning_when_no_batch_on_items(self):
		_check_batch_availability_warn(self._make_dn(qty=5))
		self.assertFalse(_get_orange_warnings())
