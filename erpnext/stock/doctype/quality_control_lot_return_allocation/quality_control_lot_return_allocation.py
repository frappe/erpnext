# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

from frappe.model.document import Document


class QualityControlLotReturnAllocation(Document):
	"""What a purchase return actually took from a Quality Control Lot.

	A return carries no lot link, so allocation is decided at submission by
	walking the item's lots. Recording the outcome is what makes the reversal
	honest: cancelling gives back the quantities this voucher row took, from the
	lots it took them from, instead of re-running the allocator over totals that
	other returns have since changed.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		batch_no: DF.Link | None
		qty: DF.Float
		quality_control_lot: DF.Link
		serial_no: DF.SmallText | None
		voucher_detail_no: DF.Data | None
		voucher_no: DF.DynamicLink
		voucher_type: DF.Link
	# end: auto-generated types
