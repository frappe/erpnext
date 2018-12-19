# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ServiceLevel(Document):

	def validate(self):
		week = ["Monday",  "Tuesday",  "Wednesday",  "Thursday", "Friday", "Saturday", "Sunday"]
		days = []
		for support_and_resolution in self.support_and_resolution:
			days.append(support_and_resolution.workday)
			#print("----->" + str(support_and_resolution.idx) + " -- " + str(support_and_resolution.workday))
			# for support in self.support_and_resolution[:len(self.support_and_resolution)-1-self.support_and_resolution.index(support_and_resolution)]:
			# 	if week.index(support.workday) > week.index((self.support_and_resolution[self.support_and_resolution.index(support)+1]).workday):
			# 		print(support.idx , (self.support_and_resolution[self.support_and_resolution.index(support)+1]).idx)
			# 		support.idx, (self.support_and_resolution[self.support_and_resolution.index(support)+1]).idx = (self.support_and_resolution[self.support_and_resolution.index(support)+1]).idx, support.idx

		indexes = list(map(lambda x: week.index(x), days))
		print(indexes)
		for i in range(len(indexes)):
			for j in range(0, len(indexes)-i-1):
				if indexes[j] > indexes[j+1]:
					indexes[j], indexes[j+1] = indexes[j+1], indexes[j]
		print(indexes)

		for count, support_and_resolution in enumerate(self.support_and_resolution):
			support_and_resolution.idx = indexes[count] + 1