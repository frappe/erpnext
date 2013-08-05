# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	from webnotes.utils import cstr
	from webnotes.model.code import get_obj
	
	fy_list = webnotes.conn.sql("""select name from `tabFiscal Year` 
		where docstatus < 2 order by year_start_date desc""")
	series_list = []
	for fy in fy_list:
		series_list.append("PRO/" + cstr(fy[0][2:5]) + cstr(fy[0][7:9]) + "/")
	
	naming_series_obj = get_obj("Naming Series")
	naming_series_obj.doc.user_must_always_select = 1
	naming_series_obj.set_series_for("Production Order", series_list)