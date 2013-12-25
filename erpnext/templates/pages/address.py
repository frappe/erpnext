# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint

no_cache = True

def get_context():
	def _get_fields(fieldnames):
		return [webnotes._dict(zip(["label", "fieldname", "fieldtype", "options"], 
				[df.label, df.fieldname, df.fieldtype, df.options]))
			for df in webnotes.get_doctype("Address", processed=True).get({"fieldname": ["in", fieldnames]})]
	
	bean = None
	if webnotes.form_dict.name:
		bean = webnotes.bean("Address", webnotes.form_dict.name)
	
	return {
		"doc": bean.doc if bean else None,
		"meta": webnotes._dict({
			"left_fields": _get_fields(["address_title", "address_type", "address_line1", "address_line2",
				"city", "state", "pincode", "country"]),
			"right_fields": _get_fields(["email_id", "phone", "fax", "is_primary_address",
				"is_shipping_address"])
		}),
		"cint": cint
	}
	
