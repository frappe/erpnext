# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections.abc import Mapping

from frappe.utils import flt


def get_minimum_material_coverage_fraction(
	required_qty: Mapping[str, float], transferred_qty: Mapping[str, float], precision: int
) -> float:
	"""Return the least-covered component ratio at the configured precision."""
	coverage = []
	for item_code, required in required_qty.items():
		transferred = flt(transferred_qty.get(item_code))
		if flt(transferred, precision) == flt(required, precision):
			coverage.append(1.0)
		else:
			coverage.append(transferred / required)

	return min(coverage, default=0.0)
