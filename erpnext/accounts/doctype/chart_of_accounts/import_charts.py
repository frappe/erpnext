# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, os, json

def import_charts():
	print "Importing Chart of Accounts"
	frappe.db.sql("""delete from `tabChart of Accounts`""")
	charts_dir = os.path.join(os.path.dirname(__file__), "charts")
	for fname in os.listdir(charts_dir):
		if fname.endswith(".json"):
			with open(os.path.join(charts_dir, fname), "r") as f:
				chart = json.loads(f.read())
				country = frappe.db.get_value("Country", {"code": fname.split("_", 1)[0]})
				if country:
					doc = frappe.get_doc({
						"doctype":"Chart of Accounts",
						"chart_name": chart.get("name"),
						"source_file": fname,
						"country": country
					}).insert()
					#print doc.name.encode("utf-8")
				#else:
					#print "No chart for: " + chart.get("name").encode("utf-8")

	frappe.db.commit()
