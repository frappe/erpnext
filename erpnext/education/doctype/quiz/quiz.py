# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Quiz(Document):


	def validate_quiz_attempts(self, enrollment, quiz_name):
		print(enrollment, quiz_name)
		if self.max_attempts > 0:
			try:
				if len(frappe.get_all("Quiz Activity", {'enrollment': enrollment.name, 'quiz': quiz_name})) >= self.max_attempts:
					frappe.throw('Maximum attempts reached!')
			except:
				pass


	def get_quiz(self):
		pass


	def evaluate(self, response_dict, quiz_name):
		# self.validate_quiz_attempts(enrollment, quiz_name)
		self.get_questions()
		answers = {q.name:q.get_answer() for q in self.get_questions()}
		correct_answers = {}
		for key in answers:
			try:
				result = (response_dict[key] == answers[key])
			except:
				result = False
			correct_answers[key] = result
		score = (sum(correct_answers.values()) * 100 ) / len(answers)
		if score >= self.passing_score:
			status = "Pass"
		else:
			status = "Fail"
		return correct_answers, score, status


	def get_questions(self):
		quiz_question = self.get_all_children()
		if quiz_question:
			questions = [frappe.get_doc('Question', question.question_link) for question in quiz_question]
			return questions
		else:
			return None

