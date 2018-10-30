# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class QualityReview(Document):	

	@frappe.whitelist()
	def create_action(self):
		if self.measurable == "Yes":
			print("In measurable yes if")
			if self.goal:
				problem = ''
				for value in self.values:
					if int(value.achieved) < int(value.target):
						problem = problem + 'In '+ value.objective +', the Achieved Value '+ str(value.achieved) +' is less than the Target Value '+ str(value.target) +'\n'

				if(problem != ''):
					problem = filter(None, problem.split("\n"))
					doc = frappe.get_doc({
						'doctype': 'Quality Action',
						'action': 'Corrective',
						'type': 'Quality Review',
						'review': ''+ self.name +'',
						'date': ''+ frappe.utils.nowdate() +'',
						'procedure': ''+ self.procedure +''
					})
					for data in problem:
						doc.append("description",{
							'problem': data,
							'status': 'Open'
						})
					doc.insert()
					frappe.db.commit()
					return "Action Initialized"
				else:
					print("In measurable yes else")
					return "Action Not Initialized"
		else:
			if self.goal:
				print("In non measurable yes if")
				problem = ''
				for value in self.values:
					if value.yes_no == "No":
						problem = problem + 'In '+ value.objective +', is set to "no".\n'

				if(problem != ''):
					problem = filter(None, problem.split("\n"))
					doc = frappe.get_doc({
						'doctype': 'Quality Action',
						'action': 'Corrective',
						'type': 'Quality Review',
						'review': ''+ self.name +'',
						'date': ''+ frappe.utils.nowdate() +'',
						'procedure': ''+ self.procedure +''
					})
					for data in problem:
						doc.append("description",{
							'problem': data,
							'status': 'Open'
						})
					doc.insert()
					frappe.db.commit()
					return "Action Initialized"
				else:
					print("In non measurable yes else")
					return "Action Not Initialized"

	def validate(self):
		if self.measurable == "Yes":
			if self.goal:
				problem = ''
				for value in self.values:
					if int(value.achieved) < int(value.target):
						problem = 'set'
						break

				if problem == 'set':
					self.action = 'Action Initialised'
				else:
					self.action = 'No Action'
		else:
			if self.goal:
				problem = ''
				for value in self.values:
					if value.yes_no == "No":
						problem = 'set'

				if problem == 'set':
					self.action = 'Action Initialised'
				else:
					self.action = 'No Action'
			
"""	def after_insert(self):
		if self.measurable == "Yes":
			if self.goal:
				problem = ''
				for value in self.values:
					if int(value.achieved) < int(value.target):
						problem = problem + 'In '+ value.objective +', the Achieved Value '+ str(value.achieved) +' is less than the Target Value '+ str(value.target) +'\n'

				if(problem != ''):
					problem = filter(None, problem.split("\n"))
					doc = frappe.get_doc({
						'doctype': 'Quality Action',
						'action': 'Corrective',
						'type': 'Quality Review',
						'review': ''+ self.name +'',
						'date': ''+ frappe.utils.nowdate() +'',
						'procedure': ''+ self.procedure +''
					})
					for data in problem:
						doc.append("description",{
							'problem': data,
							'status': 'Open'
						})
					doc.insert()
					frappe.db.commit()
		else:
			if self.goal:
				problem = ''
				for value in self.values:
					if value.yes_no == "No":
						problem = problem + 'In '+ value.objective +', is set to "no".\n'

				if(problem != ''):
					problem = filter(None, problem.split("\n"))
					doc = frappe.get_doc({
						'doctype': 'Quality Action',
						'action': 'Corrective',
						'type': 'Quality Review',
						'review': ''+ self.name +'',
						'date': ''+ frappe.utils.nowdate() +'',
						'procedure': ''+ self.procedure +''
					})
					for data in problem:
						doc.append("description",{
							'problem': data,
							'status': 'Open'
						})
					doc.insert()
					frappe.db.commit()

	def on_update(self):
		if self.measurable == "Yes":
			if self.goal:
				problem = ''
				for value in self.values:
					if int(value.achieved) < int(value.target):
						problem = problem + 'In '+ value.objective +', the Achieved Value '+ str(value.achieved) +' is less than the Target Value '+ str(value.target) +'\n'

				if problem != '':
					problem = filter(None, problem.split("\n"))
					query = frappe.get_list("Quality Action", filters={"review":""+ self.name +""})
					if len(query) == 0:
						doc = frappe.get_doc({
							'doctype': 'Quality Action',
							'action': 'Corrective',
							'type': 'Quality Review',
							'review': ''+ self.name +'',
							'date': ''+ frappe.utils.nowdate() +'',
							'procedure': ''+ self.procedure +''
						})
						for data in problem:
							doc.append("description",{
								'problem': data,
								'status': 'Open'
							})
						doc.insert()
						frappe.db.commit()
					else:
						child_table = frappe.get_list("Quality Action Table", filters={'parent': ''+ query[0].name +''})
						for child in child_table:
							frappe.delete_doc("Quality Action Table", ""+ child.name +"")
						doc = frappe.get_doc("Quality Action", ""+ query[0].name +"")
						for data in problem:
							
							doc.append("description",{
								'problem': data,
								'status': 'Open'
							})
						doc.save()
						frappe.db.commit()
				else:
					query = frappe.get_list("Quality Action", filters={"review":""+ self.name +""})
					if len(query) != 0:
						frappe.delete_doc("Quality Action", ""+ query[0].name +"")
					else:
						pass
		else:
			if self.goal:
				problem = ''
				for value in self.values:
					if value.yes_no == "No":
						problem = problem + 'In '+ value.objective +', is set to "no".\n'

				if problem != '':
					problem = filter(None, problem.split("\n"))
					query = frappe.get_list("Quality Action", filters={"review":""+ self.name +""})
					if len(query) == 0:
						doc = frappe.get_doc({
							'doctype': 'Quality Action',
							'action': 'Corrective',
							'type': 'Quality Review',
							'review': ''+ self.name +'',
							'date': ''+ frappe.utils.nowdate() +'',
							'procedure': ''+ self.procedure +''
						})
						for data in problem:
							doc.append("description",{
								'problem': data,
								'status': 'Open'
							})
						doc.insert()
						frappe.db.commit()
					else:
						child_table = frappe.get_list("Quality Action Table", filters={'parent': ''+ query[0].name +''})
						for child in child_table:
							frappe.delete_doc("Quality Action Table", ""+ child.name +"")
						doc = frappe.get_doc("Quality Action", ""+ query[0].name +"")
						for data in problem:
							
							doc.append("description",{
								'problem': data,
								'status': 'Open'
							})
						doc.save()
						frappe.db.commit()
				else:
					query = frappe.get_list("Quality Action", filters={"review":""+ self.name +""})
					if len(query) != 0:
						frappe.delete_doc("Quality Action", ""+ query[0].name +"")
					else:
						pass
"""