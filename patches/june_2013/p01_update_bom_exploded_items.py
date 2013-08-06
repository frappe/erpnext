# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	updated_bom = []
	for bom in webnotes.conn.sql("select name from tabBOM where docstatus < 2"):
		if bom[0] not in updated_bom:
			try:
				bom_obj = webnotes.get_obj("BOM", bom[0], with_children=1)
				updated_bom += bom_obj.update_cost_and_exploded_items(bom[0])
				webnotes.conn.commit()
			except:
				pass