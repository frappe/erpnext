# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AssetsSetting(Document):
	pass

@frappe.whitelist(allow_guest=True)
def get_scrapped_assets(sc_date,settings):
	import datetime
	import time
	from datetime import datetime
	from datetime import timedelta
	import dateutil.parser
	assetss=frappe.get_all("Asset", fields=["name"])
	dep=[]
	for m in assetss:
		m2=frappe.get_doc("Asset",m.name)
		if m2.freeze ==0:
			schedules=frappe.get_all("Depreciation Schedule",['name'],filters={'parent':m.name})
			if schedules:
				for l in schedules:
					sch=frappe.get_doc("Depreciation Schedule",l.name)
					if sch.schedule_date==datetime.combine((datetime.strptime(sc_date,'%Y-%m-%d')),datetime.min.time()).date():
						if not sch.journal_entry:
							dep.append({
								'asset_name':m.name,
								'depreciation_amount':sch.depreciation_amount,
								'accumulated_depreciation_amount':sch.accumulated_depreciation_amount,
								'journal_entry':sch.journal_entry,
								'expected_value_after_useful_life':m2.expected_value_after_useful_life
								})
		

	return dep
	
