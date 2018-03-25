# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.document import Document
import frappe.utils.nestedset

class Department(Document):
	nsm_parent_field = 'parent_department'

	def validate(self):
		pass

	def on_update(self):
		self.update_nsm_model()
		self.add_roles_and_permissions()

	def on_trash(self):
		self.validate_trash()
		self.update_nsm_model()

	def update_nsm_model(self):
		"""update lft, rgt indices for nested set model"""
		frappe.utils.nestedset.update_nsm(self)

	def validate_trash(self):
		pass

	def add_roles_and_permissions(self):
		# if self.director:
		# 	user_emp = frappe.db.sql("select user_id from `tabEmployee` where name = '{0}'".format(self.director), as_dict = 1)
		# 	ups = frappe.get_list("User permission", filters = {user: user_emp, allow: 'Department'}, fields=[self.name], ignore_permissions=True)
		# 	for up in ups:
		if self.director:
			user_emp = frappe.db.sql("select user_id from `tabEmployee` where name = '{0}'".format(self.director), as_dict = 1)
			user = frappe.get_doc("User", user_emp[0].user_id)
			user.add_roles("Director")
			frappe.permissions.add_user_permission ("Department", self.name, user_emp[0].user_id)
			second_level_departments = frappe.db.sql("select name from `tabDepartment` where parent_department = '{0}'".format(self.name), as_dict = 1)
			for dp in second_level_departments:
				frappe.permissions.add_user_permission ("Department", dp.name, user_emp[0].user_id)
				third_level_departments = frappe.db.sql("select name from `tabDepartment` where parent_department = '{0}'".format(dp.name), as_dict = 1)
				for dp in third_level_departments:
					frappe.permissions.add_user_permission ("Department", dp.name,user_emp[0].user_id)

		elif self.manager:
			user_emp = frappe.db.sql("select user_id from `tabEmployee` where name = '{0}'".format(self.manager), as_dict = 1)
			user = frappe.get_doc("User", user_emp[0].user_id)
			user.add_roles("Manager")
			frappe.permissions.add_user_permission ("Department", self.name, user_emp[0].user_id)
			second_level_departments = frappe.db.sql("select name from `tabDepartment` where parent_department = '{0}'".format(self.name), as_dict = 1)
			for dp in second_level_departments:
				frappe.permissions.add_user_permission ("Department", dp.name, user_emp[0].user_id)

		elif self.line_manager:
			user_emp = frappe.db.sql("select user_id from `tabEmployee` where name = '{0}'".format(self.line_manager), as_dict = 1)
			user = frappe.get_doc("User", user_emp[0].user_id)
			user.add_roles("Line Manager")
			frappe.permissions.add_user_permission ("Department", self.name, user_emp[0].user_id)

	# def update_department_permissions(self):
	# 	pass
	# 	deps = get_departments(self.lft, self.rgt)

	# 	for dep in deps:
	# 		if self.director:
	# 			emp_user = get_employee_user(self.director)
	# 			prev_permitted_user = get_permitted_user(self.name, "director")
	# 			if emp_user:
	# 				up_dict = {
	# 					"user": emp_user,
	# 					"allow": "Department",
	# 					"for_value": dep[0]
	# 				}

	# 				if prev_permitted_user:
	# 					permission_dn = get_user_permission_dn(prev_permitted_user, "Department", dep[0])
	# 					if permission_dn:
	# 						perm_doc = frappe.get_doc("User Permission", permission_dn)
	# 						perm_doc.user = emp_user
	# 						perm_doc.save(ignore_permissions=True)
	# 					else:
	# 						perm_new_doc = frappe.new_doc("User Permission")
	# 						perm_new_doc.update(up_dict)
	# 				else: 
	# 					perm_new_doc = frappe.new_doc("User Permission")
	# 					perm_new_doc.update(up_dict)

def get_permitted_user(department_dn, role_fn):
	if role_fn in ["director", "department_manager", "line_manager"]:
		dep_role_emp = frappe.db.get_value("Department", filters = {name: department_dn}, fieldname = role_fn)
		if dep_role_emp:
			return get_employee_user(dep_role_emp)

def get_user_permission_dn(user, allow, for_value):
	return frappe.get_value("Employee", filters = {"user": user, "allow": allow, "for_value": for_value}, fieldname = "name")

def get_employee_user(employee):
	return frappe.get_value("Employee", filters = {"name": employee}, fieldname = "user_id")

def get_departments(lft, rgt):
	return frappe.db.sql("""
		select name from `tabDepartment` where lft >= '{0}' and rgt <= '{1}'
		""".format(lft, rgt))


def add_departments():
	dps = frappe.db.sql("select name from `tabDepartment` where parent_department = 'الادارة العليا'", as_dict = 1)
	 # frappe.get_list("Department", filters = {"parent_department": "Finance"}, fields = {"name"})
	for dp in dps:
		cdps = frappe.db.sql("select name from `tabDepartment` where parent_department = '{0}'".format(frappe.db.escape(dp.name)), as_dict = 1)
		for cdp in cdps:
			# print cdp.name
			for x in range(2):
				dep = frappe.new_doc("Department")
				dep.update({
					"name": cdp.name + " Line Management {0}".format(x+1),
					"department_name": cdp.name + " Line Management {0}".format(x+1), 
					"is_group": 0,
					"parent_department": cdp.name
					})
				dep.save(ignore_permissions = True)
				print x

def add_roles_and_permissions():
	# frappe.permissions.add_user_permission ("Department", "Digital Computing", "as.alqahtani@tawari.sa")
	# print frappe.permissions.has_permission ("Department", doc="Digital Computing", user="as.alqahtani@tawari.sa")
	# print frappe.permissions.user_has_permission ("Digital Computing", user="as.alqahtani@tawari.sa")
	dps = frappe.db.sql("select name, line_manager, manager, director from `tabDepartment`", as_dict = 1)
	for dp in dps:
		if dp.line_manager:
			user_emp = frappe.db.sql("select user_id from `tabEmployee` where name = '{0}'".format(dp.line_manager), as_dict = 1)
			user = frappe.get_doc("User", user_emp[0].user_id)
			user.add_roles("Line Manager")
			frappe.permissions.add_user_permission ("Department", dp.name, user_emp[0].user_id)
			# dps1 = frappe.db.sql("select name from `tabDepartment` where parent_department = '{0}'".format(dp.name), as_dict = 1)
			# for dp1 in dps1:
			# 	frappe.permissions.add_user_permission ("Department", dp1.name, user_emp[0].user_id)
				# dps2 = frappe.db.sql("select name from `tabDepartment` where parent_department = '{0}'".format(dp1.name), as_dict = 1)
				# for dp2 in dps2:
				# 	frappe.permissions.add_user_permission ("Department", dp2.name,user_emp[0].user_id)
	# for dp in dps:
	# 	if dp.director:
	# 		user_emp = frappe.db.sql("select user_id from `tabEmployee` where name = '{0}'".format(dp.director), as_dict = 1)
	# 		user = frappe.get_doc("User", user_emp[0].user_id)
	# 		user.add_roles("Director")
	# 		frappe.permissions.add_user_permission ("Department", dp.name, user_emp[0].user_id)
	# 		dps1 = frappe.db.sql("select name from `tabDepartment` where parent_department = '{0}'".format(dp.name), as_dict = 1)
	# 		for dp1 in dps1:
	# 			frappe.permissions.add_user_permission ("Department", dp1.name, user_emp[0].user_id)
	# 			dps2 = frappe.db.sql("select name from `tabDepartment` where parent_department = '{0}'".format(dp1.name), as_dict = 1)
	# 			for dp2 in dps2:
	# 				frappe.permissions.add_user_permission ("Department", dp2.name,user_emp[0].user_id)


			# print dp.line_manager +" "+ dp.name
	# frappe.permissions.add_user_permission("Department", "_Test Company 1", "test2@example.com")
	# pass
	


