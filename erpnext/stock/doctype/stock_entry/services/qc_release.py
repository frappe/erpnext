# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from .material_transfer import MaterialTransferStockEntry


class QCReleaseStockEntry(MaterialTransferStockEntry):
	"""Release quarantined stock out of a Quality (QC) warehouse.

	Behaves exactly like a Material Transfer — source and target warehouse,
	stock value carried over, no GL impact — but is a distinct purpose so it can
	be the only stock movement whitelisted to issue stock out of a Quality
	warehouse. QC-specific validation (e.g. requiring a linked, passed Quality
	Inspection) is layered on in a later step.
	"""

	pass
