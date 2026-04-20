import frappe

from erpnext.manufacturing.doctype.slab.slab import Slab
from erpnext.manufacturing.doctype.slab_quality_report.slab_quality_report import SlabQualityReport


def create_slab_quality_report(slab_name: str, slab_qc: SlabQualityReport):
	slab: Slab = frappe.get_doc("Slab", slab_name)  # pyright: ignore[reportAssignmentType]
	slab.reload()

	if not slab_qc.name:
		slab_qc.insert(ignore_permissions=True)
		slab_qc.submit()
		slab.reload()

	last_history_item = next((h for h in slab.slab_history if h.station == "Quality Check"), None)
	if not last_history_item:
		raise Exception("Slab is not in quality check.")

	if last_history_item and not last_history_item.quality_report_name:
		last_history_item.quality_report_name = slab_qc.name
		slab.save(ignore_permissions=True)
		slab.reload()

	slab.grade = slab_qc.grade
	slab.quality_assessment = slab_qc.name
	slab.save(ignore_permissions=True)

	return slab_qc
