# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	bean = webnotes.bean("Website Settings")
	for company in webnotes.conn.sql_list("select name from `tabCompany`"):
		if bean.doc.banner_html == ("""<h3 style='margin-bottom: 20px;'>""" + company + "</h3>"):
			bean.doc.banner_html = None
			if not bean.doc.brand_html:
				bean.doc.brand_html = company

			bean.save()
			break