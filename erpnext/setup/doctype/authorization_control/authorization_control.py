# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, session
from frappe.query_builder.functions import Coalesce
from frappe.utils import comma_or, cstr, flt, has_common

from erpnext.utilities.transaction_base import TransactionBase


class AuthorizationControl(TransactionBase):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

	# end: auto-generated types

	def get_appr_user_role(self, det, doctype_name, total, based_on, condition, master_name, company):
		amt_list, appr_users, appr_roles = [], [], []
		_users, _roles = "", ""
		if det:
			for x in det:
				amt_list.append(flt(x[0]))
			max_amount = max(amt_list)

			app_dtl = frappe.db.sql(
				"""select approving_user, approving_role from `tabAuthorization Rule`
				where transaction = {} and (value = {} or value > {})
				and docstatus != 2 and based_on = {} and company = {} {}""".format(
					"%s", "%s", "%s", "%s", "%s", condition
				),
				(doctype_name, flt(max_amount), total, based_on, company),
			)

			if not app_dtl:
				app_dtl = frappe.db.sql(
					"""select approving_user, approving_role from `tabAuthorization Rule`
					where transaction = {} and (value = {} or value > {}) and docstatus != 2
					and based_on = {} and coalesce(company,'') = '' {}""".format(
						"%s", "%s", "%s", "%s", condition
					),
					(doctype_name, flt(max_amount), total, based_on),
				)

			for d in app_dtl:
				if d[0]:
					appr_users.append(d[0])
				if d[1]:
					appr_roles.append(d[1])

			if not has_common(appr_roles, frappe.get_roles()) and not has_common(
				appr_users, [session["user"]]
			):
				frappe.msgprint(_("Not authorized since {0} exceeds limits").format(_(based_on)))
				frappe.throw(_("Can be approved by {0}").format(comma_or(appr_roles + appr_users)))

	def validate_auth_rule(self, doctype_name, total, based_on, cond, company, master_name=""):
		chk = 1
		add_cond1, add_cond2 = "", ""
		if based_on in ["Itemwise Discount", "Item Group wise Discount"]:
			add_cond1 += " and master_name = " + frappe.db.escape(cstr(master_name))
			itemwise_exists = frappe.db.sql(
				"""select value from `tabAuthorization Rule`
				where transaction = {} and value <= {}
				and based_on = {} and company = {} and docstatus != 2 {} {}""".format(
					"%s", "%s", "%s", "%s", cond, add_cond1
				),
				(doctype_name, total, based_on, company),
			)

			if not itemwise_exists:
				itemwise_exists = frappe.db.sql(
					"""select value from `tabAuthorization Rule`
					where transaction = {} and value <= {} and based_on = {}
					and coalesce(company,'') = ''	and docstatus != 2 {} {}""".format(
						"%s", "%s", "%s", cond, add_cond1
					),
					(doctype_name, total, based_on),
				)

			if itemwise_exists:
				self.get_appr_user_role(
					itemwise_exists, doctype_name, total, based_on, cond + add_cond1, master_name, company
				)
				chk = 0
		if chk == 1:
			if based_on in ["Itemwise Discount", "Item Group wise Discount"]:
				add_cond2 += " and coalesce(master_name,'') = ''"

			appr = frappe.db.sql(
				"""select value from `tabAuthorization Rule`
				where transaction = {} and value <= {} and based_on = {}
				and company = {} and docstatus != 2 {} {}""".format("%s", "%s", "%s", "%s", cond, add_cond2),
				(doctype_name, total, based_on, company),
			)

			if not appr:
				appr = frappe.db.sql(
					"""select value from `tabAuthorization Rule`
					where transaction = {} and value <= {} and based_on = {}
					and coalesce(company,'') = '' and docstatus != 2 {} {}""".format(
						"%s", "%s", "%s", cond, add_cond2
					),
					(doctype_name, total, based_on),
				)

			self.get_appr_user_role(
				appr, doctype_name, total, based_on, cond + add_cond2, master_name, company
			)

	def bifurcate_based_on_type(self, doctype_name, total, av_dis, based_on, doc_obj, val, company):
		add_cond = ""
		auth_value = av_dis

		if val == 1:
			add_cond += " and system_user = {}".format(frappe.db.escape(session["user"]))
		elif val == 2:
			add_cond += " and system_role IN (%s)" % ", ".join(
				frappe.db.escape(r) for r in frappe.get_roles()
			)
		else:
			add_cond += " and coalesce(system_user,'') = '' and coalesce(system_role,'') = ''"

		if based_on == "Grand Total":
			auth_value = total
		elif based_on == "Customerwise Discount":
			if doc_obj:
				if doc_obj.doctype == "Sales Invoice":
					customer = doc_obj.customer
				else:
					customer = doc_obj.customer_name
				add_cond = f" and master_name = {frappe.db.escape(customer)}"
		if based_on == "Itemwise Discount":
			if doc_obj:
				for t in doc_obj.get("items"):
					self.validate_auth_rule(
						doctype_name, t.discount_percentage, based_on, add_cond, company, t.item_code
					)
		elif based_on == "Item Group wise Discount":
			if doc_obj:
				for t in doc_obj.get("items"):
					self.validate_auth_rule(
						doctype_name, t.discount_percentage, based_on, add_cond, company, t.item_group
					)
		else:
			self.validate_auth_rule(doctype_name, auth_value, based_on, add_cond, company)

	def validate_approving_authority(self, doctype_name, company, total, doc_obj=""):
		if not frappe.db.count("Authorization Rule"):
			return

		av_dis = 0
		if doc_obj:
			price_list_rate, base_rate = 0, 0
			for d in doc_obj.get("items"):
				if d.base_rate:
					price_list_rate += (flt(d.base_price_list_rate) or flt(d.base_rate)) * flt(d.qty)
					base_rate += flt(d.base_rate) * flt(d.qty)
			if doc_obj.get("discount_amount"):
				base_rate -= flt(doc_obj.discount_amount)

			if price_list_rate:
				av_dis = 100 - flt(base_rate * 100 / price_list_rate)

		final_based_on = [
			"Grand Total",
			"Average Discount",
			"Customerwise Discount",
			"Itemwise Discount",
			"Item Group wise Discount",
		]

		auth_rule = frappe.qb.DocType("Authorization Rule")

		# Check for authorization set for individual user
		based_on = [
			x[0]
			for x in (
				frappe.qb.from_(auth_rule)
				.select(auth_rule.based_on)
				.distinct()
				.where(
					(auth_rule.transaction == doctype_name)
					& (auth_rule.system_user == session["user"])
					& ((auth_rule.company == company) | (Coalesce(auth_rule.company, "") == ""))
					& (auth_rule.docstatus != 2)
				)
			).run()
		]

		for d in based_on:
			self.bifurcate_based_on_type(doctype_name, total, av_dis, d, doc_obj, 1, company)

		# Remove user specific rules from global authorization rules
		for r in based_on:
			if r in final_based_on and r not in [
				"Itemwise Discount",
				"Item Group wise Discount",
			]:
				final_based_on.remove(r)

		# Check for authorization set on particular roles
		based_on = [
			x[0]
			for x in (
				frappe.qb.from_(auth_rule)
				.select(auth_rule.based_on)
				.where(
					(auth_rule.transaction == doctype_name)
					& auth_rule.system_role.isin(frappe.get_roles())
					& auth_rule.based_on.isin(final_based_on)
					& ((auth_rule.company == company) | (Coalesce(auth_rule.company, "") == ""))
					& (auth_rule.docstatus != 2)
				)
			).run()
		]

		for d in based_on:
			self.bifurcate_based_on_type(doctype_name, total, av_dis, d, doc_obj, 2, company)

		# Remove role specific rules from global authorization rules
		for r in based_on:
			if r in final_based_on and r not in [
				"Itemwise Discount",
				"Item Group wise Discount",
			]:
				final_based_on.remove(r)

		# Check for global authorization
		for g in final_based_on:
			self.bifurcate_based_on_type(doctype_name, total, av_dis, g, doc_obj, 0, company)

	def get_value_based_rule(self, doctype_name, employee, total_claimed_amount, company):
		auth_rule = frappe.qb.DocType("Authorization Rule")
		emp = frappe.qb.DocType("Employee")

		def emp_designation():
			# fresh subquery per use to avoid sharing a pypika builder across queries
			return frappe.qb.from_(emp).select(emp.designation).where(emp.name == employee)

		val_lst = []
		val = (
			frappe.qb.from_(auth_rule)
			.select(auth_rule.value)
			.where(
				(auth_rule.transaction == doctype_name)
				& ((auth_rule.to_emp == employee) | auth_rule.to_designation.isin(emp_designation()))
				& (Coalesce(auth_rule.value, 0) < total_claimed_amount)
				& (auth_rule.company == company)
				& (auth_rule.docstatus != 2)
			)
		).run()

		if not val:
			val = (
				frappe.qb.from_(auth_rule)
				.select(auth_rule.value)
				.where(
					(auth_rule.transaction == doctype_name)
					& ((auth_rule.to_emp == employee) | auth_rule.to_designation.isin(emp_designation()))
					& (Coalesce(auth_rule.value, 0) < total_claimed_amount)
					& (Coalesce(auth_rule.company, "") == "")
					& (auth_rule.docstatus != 2)
				)
			).run()

		if val:
			val_lst = [y[0] for y in val]
		else:
			val_lst.append(0)

		max_val = max(val_lst)
		rule = (
			frappe.qb.from_(auth_rule)
			.select(
				auth_rule.name,
				auth_rule.to_emp,
				auth_rule.to_designation,
				auth_rule.approving_role,
				auth_rule.approving_user,
			)
			.where(
				(auth_rule.transaction == doctype_name)
				& (auth_rule.company == company)
				& ((auth_rule.to_emp == employee) | auth_rule.to_designation.isin(emp_designation()))
				& (Coalesce(auth_rule.value, 0) == flt(max_val))
				& (auth_rule.docstatus != 2)
			)
		).run(as_dict=1)

		if not rule:
			rule = (
				frappe.qb.from_(auth_rule)
				.select(
					auth_rule.name,
					auth_rule.to_emp,
					auth_rule.to_designation,
					auth_rule.approving_role,
					auth_rule.approving_user,
				)
				.where(
					(auth_rule.transaction == doctype_name)
					& (Coalesce(auth_rule.company, "") == "")
					& ((auth_rule.to_emp == employee) | auth_rule.to_designation.isin(emp_designation()))
					& (Coalesce(auth_rule.value, 0) == flt(max_val))
					& (auth_rule.docstatus != 2)
				)
			).run(as_dict=1)

		return rule
