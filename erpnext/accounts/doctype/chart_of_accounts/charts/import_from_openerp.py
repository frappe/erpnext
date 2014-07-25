# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""
Import chart of accounts from OpenERP sources
"""
from __future__ import unicode_literals

import os, json
import ast
from xml.etree import ElementTree as ET
from frappe.utils.csvutils import read_csv_content
from frappe.utils import cstr
import frappe


path = "/Users/nabinhait/Documents/openerp/openerp/addons"

accounts = {}
charts = {}
all_account_types = []

def go():
	global accounts, charts
	default_account_types = get_default_account_types()
	
	country_dirs = []
	for basepath, folders, files in os.walk(path):
		basename = os.path.basename(basepath)
		if basename.startswith("l10n_"):
			country_dirs.append(basename)
	
	for country_dir in country_dirs:
		accounts, charts = {}, {}
		country_path = os.path.join(path, country_dir)
		manifest = ast.literal_eval(open(os.path.join(country_path, "__openerp__.py")).read())
		data_files = manifest.get("data", []) + manifest.get("init_xml", []) + \
			manifest.get("update_xml", [])
		files_path = [os.path.join(country_path, d) for d in data_files]
		xml_roots = get_xml_roots(files_path)
		csv_content = get_csv_contents(files_path)
		prefix = country_dir if csv_content else None
		account_types = get_account_types(xml_roots.get("account.account.type", []), 
			csv_content.get("account.account.type", []), prefix)
		account_types.update(default_account_types)
		
		if xml_roots:
			make_maps_for_xml(xml_roots, account_types, country_dir)

		if csv_content:
			make_maps_for_csv(csv_content, account_types, country_dir)
		make_account_trees()
		make_charts()
		
def get_default_account_types():
	default_types_root = []
	for file in ["data_account_type.xml"]:
		default_types_root.append(ET.parse(os.path.join(path, "account", "data", 
			"data_account_type.xml")).getroot())
	return get_account_types(default_types_root, None, prefix="account")
					
def get_xml_roots(files_path):
	xml_roots = frappe._dict()
	for filepath in files_path:
		fname = os.path.basename(filepath)
		if fname.endswith(".xml"):
			tree = ET.parse(filepath)
			root = tree.getroot()
			for node in root[0].findall("record"):
				if node.get("model") in ["account.account.template", 
					"account.chart.template", "account.account.type"]:
					xml_roots.setdefault(node.get("model"), []).append(root)
					break
	return xml_roots
	
def get_csv_contents(files_path):
	csv_content = {}
	for filepath in files_path:
		fname = os.path.basename(filepath)
		for file_type in ["account.account.template", "account.account.type", 
				"account.chart.template"]:
			if fname.startswith(file_type) and fname.endswith(".csv"):
				with open(filepath, "r") as csvfile:
					try:
						csv_content.setdefault(file_type, [])\
							.append(read_csv_content(csvfile.read()))
					except Exception, e:
						continue
	return csv_content
	
def get_account_types(root_list, csv_content, prefix=None):
	types = {}
	account_type_map = {
		'cash': 'Cash', 
		'bank': 'Bank', 
		'tr_cash': 'Cash', 
		'tr_bank': 'Bank',
		'receivable': 'Receivable', 
		'tr_receivable': 'Receivable',
		'account rec': 'Receivable',
		'payable': 'Payable', 
		'tr_payable': 'Payable', 
		'equity': 'Equity', 
		'stocks': 'Stock', 
		'stock': 'Stock', 
		'tax': 'Tax', 
		'tr_tax': 'Tax', 
		'tax-out': 'Tax', 
		'tax-in': 'Tax',
		'charges_personnel': 'Chargeable', 
		'fixed asset': 'Fixed Asset',
		'cogs': 'Cost of Goods Sold',

	}
	for root in root_list:
		for node in root[0].findall("record"):
			if node.get("model")=="account.account.type":
				data = {}
				for field in node.findall("field"):
					if field.get("name")=="report_type" and field.text.lower() != "none":
						data["report_type"] = get_report_type(field.text.title())
					if field.get("name")=="code" and field.text.lower() != "none" \
						and account_type_map.get(field.text):
							data["account_type"] = account_type_map[field.text]
						
				node_id = prefix + "." + node.get("id") if prefix else node.get("id")
				types[node_id] = data
				
	if csv_content and csv_content[0][0]=="id":
		for row in csv_content[1:]:
			row_dict = dict(zip(csv_content[0], row))
			data = {}
			if row_dict.get("report_type"):
				data["report_type"] = get_report_type(row_dict.get("report_type"))
			if row_dict.get("code") and account_type_map.get(row_dict["code"]):
				data["account_type"] = account_type_map[row_dict["code"]]
			if data and data.get("id"):
				node_id = prefix + "." + data.get("id") if prefix else data.get("id")
				types[node_id] = data
	return types
	
def get_report_type(report_type):
	report_type_map = {
		"asset": "Balance Sheet",
		"liability": "Balance Sheet",
		"equity": "Balance Sheet",
		"expense": "Profit and Loss",
		"income": "Profit and Loss"
	}
	
	for d in report_type_map:
		if d in report_type.lower():
			return report_type_map[d]
	
def make_maps_for_xml(xml_roots, account_types, country_dir):
	"""make maps for `charts` and `accounts`"""	
	for model, root_list in xml_roots.iteritems():
		for root in root_list:
			for node in root[0].findall("record"):
				if node.get("model")=="account.account.template":
					data = {}
					for field in node.findall("field"):
						if field.get("name")=="name":
							data["name"] = field.text
						if field.get("name")=="parent_id":
							parent_id = field.get("ref") or field.get("eval")
							data["parent_id"] = parent_id
							
						if field.get("name")=="user_type":
							value = field.get("ref")
							if account_types.get(value, {}).get("report_type"):
								data["report_type"] = account_types[value]["report_type"]
								
							if account_types.get(value, {}).get("account_type"):
								data["account_type"] = account_types[value]["account_type"]
								if data["account_type"] not in all_account_types:
									all_account_types.append(data["account_type"])

					data["children"] = []
					accounts[node.get("id")] = data
				
				if node.get("model")=="account.chart.template":
					data = {}
					for field in node.findall("field"):
						if field.get("name")=="name":
							data["name"] = field.text
						if field.get("name")=="account_root_id":
							data["account_root_id"] = field.get("ref")
						data["id"] = country_dir
					charts.setdefault(node.get("id"), {}).update(data)

def make_account_trees():
	"""build tree hierarchy"""
	for id in accounts.keys():
		account = accounts[id]
		if account.get("parent_id"):
			if accounts.get(account["parent_id"]):
				accounts[account["parent_id"]]["children"].append(account)
			del account["parent_id"]

	# remove empty children
	for id in accounts.keys():
		if "children" in accounts[id] and not accounts[id].get("children"):
			del accounts[id]["children"]
	
def make_maps_for_csv(csv_content, account_types, country_dir):
	for content in csv_content.get("account.account.template", []):
		for row in content[1:]:
			data = dict(zip(content[0], row))
			account = {
				"name": data.get("name"),
				"parent_id": data.get("parent_id:id") or data.get("parent_id/id"),
				"children": []
			}
			user_type = data.get("user_type/id") or data.get("user_type:id")
			if account_types.get(user_type, {}).get("report_type"):
				account["report_type"] = account_types[user_type]["report_type"]
				
			if account_types.get(user_type, {}).get("account_type"):
				account["account_type"] = account_types[user_type]["account_type"]
				if account["account_type"] not in all_account_types:
					all_account_types.append(account["account_type"])
				
			accounts[data.get("id")] = account
			if not account.get("parent_id") and data.get("chart_template_id:id"):
				chart_id = data.get("chart_template_id:id")
				charts.setdefault(chart_id, {}).update({"account_root_id": data.get("id")})
					
	for content in csv_content.get("account.chart.template", []):
		for row in content[1:]:
			if row:
				data = dict(zip(content[0], row))
				charts.setdefault(data.get("id"), {}).update({
					"account_root_id": data.get("account_root_id:id") or \
						data.get("account_root_id/id"),
					"name": data.get("name"),
					"id": country_dir
				})
		
					
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
		
		with open(os.path.join("erpnext", "accounts", "doctype", "chart_of_accounts", 
			"charts", filename + ".json"), "w") as chartfile:
			chartfile.write(json.dumps(chart, indent=1, sort_keys=True))

if __name__=="__main__":
	go()