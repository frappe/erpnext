# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from erpnext.stock.services.base_stock_gl_composer import BaseStockGLComposer


class DeliveryNoteGLComposer(BaseStockGLComposer):
	"""GL composer for Delivery Note.

	Delivery Note posts the standard stock ↔ expense (COGS) entries produced by
	the base stock GL loop and adds no voucher-specific rows. It only relaxes the
	expense-account rule: the delivery difference may land on a balance-sheet
	account (e.g. the target warehouse account on an internal customer transfer),
	so P&L enforcement is off.
	"""

	enforce_pl_expense_account = False
