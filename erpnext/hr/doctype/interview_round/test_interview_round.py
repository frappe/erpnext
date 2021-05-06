# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
import unittest

class TestInterviewRound(unittest.TestCase):
	def tearDown(self):
		frappe.db.sql("DELETE FROM `tabInterview Round`")
		frappe.db.sql("DELETE FROM `tabExpected Skill Set`")

	def test_role_validation(self):
		interviewer = create_user("test_interviewer@example.com")
		interview_round = create_interview_round("Technical Round", ["Python", "JS"], interviewers=[interviewer.name], save=False)
		self.assertRaises(frappe.ValidationError, interview_round.save)


def create_interview_round(name, skill_set, interviewers=[], designation=None, save=True):
	create_skill_set(skill_set)
	interview_round = frappe.new_doc("Interview Round")
	interview_round.round_name = name
	interview_round.interview_type = create_interview_type()
	interview_round.expected_average_rating = 4
	if designation:
		interview_round.designation = designation

	for skill in skill_set:
		interview_round.append("expected_skill_set", {"skill": skill})

	for interviewer in interviewers:
		interview_round.append("interviewer", {
			"user": interviewer
		})

	if save:
		interview_round.save()

	return interview_round

def create_skill_set(skill_set):
	for skill in skill_set:
		if not frappe.db.exists("Skill", skill):
			doc = frappe.new_doc("Skill")
			doc.skill_name = skill
			doc.save()

def create_interview_type(name = "test_interview_type"):
	if frappe.db.exists("Interview Type", name):
		return frappe.get_doc("Interview Type", name).name
	else:
		doc = frappe.new_doc("Interview Type")
		doc.name = name
		doc.description = "_Test_Description"
		doc.save()

		return doc.name

