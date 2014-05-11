# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""
Import chart of accounts from OpenERP sources
"""
from __future__ import unicode_literals

import os, json
from xml.etree import ElementTree as ET
from webnotes.utils.datautils import read_csv_content
from webnotes.utils import cstr

path = "/Users/rmehta/Downloads/openerp/openerp/addons"
chart_roots = []

accounts = {}
charts = {}
types = {}

def go():
	find_charts()
	make_maps()
	make_trees()
	make_charts()

def make_charts():
	"""write chart files in app/setup/doctype/company/charts"""
	for chart_id in charts:
		src = charts[chart_id]
		
		if not src.get("name") or not src.get("account_root_id"):
			continue
			
		if not src["account_root_id"] in accounts:
			continue

		filename = src["id"][5:] + "_" + chart_id
		
		print "building " + filename
		chart = {}
		chart["name"] = src["name"]
		chart["root"] = accounts[src["account_root_id"]]
		
		with open(os.path.join("app", "setup", "doctype", "company", 
			"charts", filename + ".json"), "w") as chartfile:
			chartfile.write(json.dumps(chart, indent=1, sort_keys=True))

def make_trees():
	"""build tree hierarchy"""
	print "making trees..."
	for id in accounts.keys():
		account = accounts[id]
		if account.get("parent_id") and accounts[account["parent_id"]]:
			accounts[account["parent_id"]]["children"].append(account)
			del account["parent_id"]

	# remove empty children
	for id in accounts.keys():
		if "children" in accounts[id] and not accounts[id].get("children"):
			del accounts[id]["children"]

def make_maps():
	"""make maps for `charts` and `accounts`"""
	print "making maps..."
	for root in chart_roots:
		for node in root[0].findall("record"):
			if node.get("model")=="account.account.template":
				data = {}
				for field in node.findall("field"):
					if field.get("name")=="name":
						data["name"] = field.text
					if field.get("name")=="parent_id":
						data["parent_id"] = field.get("ref")
					if field.get("name")=="user_type":
						value = field.get("ref")
						if types.get(value, {}).get("root_type"):
							data["root_type"] = types[value]["root_type"]
						else:
							if "asset" in value: data["root_type"] = "Asset"
							if "liability" in value: data["root_type"] = "Liability"
							if "income" in value: data["root_type"] = "Income"
							if "expense" in value: data["root_type"] = "Expense"
					
				data["children"] = []
					
				accounts[node.get("id")] = data
	
			if node.get("model")=="account.chart.template":
				data = {}
				for field in node.findall("field"):
					if field.get("name")=="name":
						data["name"] = field.text
					if field.get("name")=="account_root_id":
						data["account_root_id"] = field.get("ref")
					data["id"] = root.get("folder")
				charts.setdefault(node.get("id"), {}).update(data)
			
			if node.get("model")=="account.account.type":
				data = {}
				for field in node.findall("field"):
					if field.get("name")=="report_type":
						data["root_type"] = field.text.title()
				types[node.get("id")] = data
					
def find_charts():
	print "finding charts..."
	for basepath, folders, files in os.walk(path):
		basename = os.path.basename(basepath)
		if basename.startswith("l10n"):
			for fname in files:
				fname = cstr(fname)
				filepath = os.path.join(basepath, fname)
				if fname.endswith(".xml"):
					tree = ET.parse(filepath)
					root = tree.getroot()
					for node in root[0].findall("record"):
						if node.get("model") in ["account.account.template", 
							"account.chart.template", "account.account.type"]:
							chart_roots.append(root)
							root.set("folder", basename)
							break
				
				if fname.endswith(".csv"):
					with open(filepath, "r") as csvfile:
						try:
							content = read_csv_content(csvfile.read())
						except Exception, e:
							continue
					
					if content[0][0]=="id":
						for row in content[1:]:
							data = dict(zip(content[0], row))
							account = {
								"name": data.get("name"),
								"parent_id": data.get("parent_id:id"),
								"children": []
							}
							accounts[data.get("id")] = account
							if not account.get("parent_id"):
								chart_id = data.get("chart_id:id")
								charts.setdefault(chart_id, {}).update({
									"account_root_id": data.get("id")})

if __name__=="__main__":
	go()