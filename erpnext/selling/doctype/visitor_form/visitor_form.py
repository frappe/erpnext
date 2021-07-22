# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class VisitorForm(Document):
	def on_submit(self):
		lead_doc=frappe.new_doc('Lead')
		lead_doc.update(
			{
				'lead_name':self.name_of_visitor,
				'company_name':self.company_name,
				'address_title':self.office_address,
				'address_line1':self.office_no,
				'address_line2':self.office_address,
				'city':self.city,
				'email_id' : self.email_id,
				'mobile_no':self.mobile__no,
				'trader':self.trader,
				'oem':self.oem,
				'appl_customer':self.appl_customer,
				'adhesive_supplier':self.adhesive_supplier,
				'packaging':self.packaging,
				'stationery':self.stationery,
				'corrugation':self.corrugation,
				'construction':self.construction,
				'_paint_and_inks':self.paint_and_inks,
				'labels_and_tapes':self.labels_and_tapes,
				'other':self.other,
				'segment':self.segment,
				'end_use_of_product_':self.end_use_of_product,
				'wet_lamination':self.wet_lamination,
				'folder_gluer_side_pasting':self.folder_gluer_side_pasting,
				'aqueous_opm':self.aqueous_opm,
				'blister_opm_pet_pvc':self.blister_opm_pet_pvc,
				'note_books_diaries__file_mfg':self.note_books_diaries__file_mfg,
				'dry_lamination':self.dry_lamination,
				'labeling':self.labeling,
				'corrugated_boxes':self.corrugated_boxes,
				'envelope_making':self.envelope_making,
				'others':self.others,
				'manual_gluing':self.manual_gluing,
				'type_of_cartons':self.type_of_cartons,
				'uv_opm':self.uv_opm
			}).save()