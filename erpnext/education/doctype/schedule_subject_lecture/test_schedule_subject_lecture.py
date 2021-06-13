# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

import datetime
from frappe.utils import today, to_timedelta
from erpnext.education.utils import OverlapError
from frappe.utils.make_random import get_random

# test_records = frappe.get_test_records('Course Schedule')

class TestScheduleSubjectLecture(unittest.TestCase):
	def test_student_group_conflict(self):
		cs1 = make_schedule_subject_lecture_test_record(simulate= True)

		cs2 = make_schedule_subject_lecture_test_record(schedule_date=cs1.schedule_date, from_time= cs1.from_time, 
			to_time= cs1.to_time, instructor="_Test Instructor 2", room=frappe.get_all("Room")[1].name, do_not_save= 1)
		self.assertRaises(OverlapError, cs2.save)

	def test_instructor_conflict(self):
		cs1 = make_schedule_subject_lecture_test_record(simulate= True)
		
		cs2 = make_schedule_subject_lecture_test_record(from_time= cs1.from_time, to_time= cs1.to_time, 
			student_group="Course-TC101-2014-2015 (_Test Academic Term)", room=frappe.get_all("Room")[1].name, do_not_save= 1)
		self.assertRaises(OverlapError, cs2.save)

	def test_room_conflict(self):
		cs1 = make_schedule_subject_lecture_test_record(simulate= True)
		
		cs2 = make_schedule_subject_lecture_test_record(from_time= cs1.from_time, to_time= cs1.to_time, 
			student_group="Course-TC101-2014-2015 (_Test Academic Term)", instructor="_Test Instructor 2", do_not_save= 1)
		self.assertRaises(OverlapError, cs2.save)
		
	def test_no_conflict(self):
		cs1 = make_schedule_subject_lecture_test_record(simulate= True)
		
		make_schedule_subject_lecture_test_record(from_time= cs1.from_time, to_time= cs1.to_time, 
			student_group="Course-TC102-2014-2015 (_Test Academic Term)", instructor="_Test Instructor 2", room=frappe.get_all("Room")[1].name)

def make_schedule_subject_lecture_test_record(**args):
	args = frappe._dict(args)

	schedule_subject_lecture = frappe.new_doc("Course Schedule")
	schedule_subject_lecture.student_group = args.student_group or "Course-TC101-2014-2015 (_Test Academic Term)"
	schedule_subject_lecture.course = args.course or "TC101"
	schedule_subject_lecture.instructor = args.instructor or "_Test Instructor"
	schedule_subject_lecture.room = args.room or frappe.get_all("Room")[0].name
	
	schedule_subject_lecture.schedule_date = args.schedule_date or today()
	schedule_subject_lecture.from_time = args.from_time or to_timedelta("01:00:00")
	schedule_subject_lecture.to_time = args.to_time or schedule_subject_lecture.from_time + datetime.timedelta(hours= 1)

	
	if not args.do_not_save:
		if args.simulate:
			while True:
				try:
					schedule_subject_lecture.save()
					break
				except OverlapError:
					schedule_subject_lecture.from_time = schedule_subject_lecture.from_time + datetime.timedelta(minutes=10)
					schedule_subject_lecture.to_time = schedule_subject_lecture.from_time + datetime.timedelta(hours= 1)
		else:
			schedule_subject_lecture.save()

	return schedule_subject_lecture
