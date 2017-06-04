# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

import datetime
from frappe.utils import today, to_timedelta
from erpnext.schools.utils import OverlapError

# test_records = frappe.get_test_records('Course Schedule')

class TestCourseSchedule(unittest.TestCase):
	def test_student_group_conflict(self):
		cs1 = make_course_schedule_test_record(simulate= True)

		cs2 = make_course_schedule_test_record(schedule_date=cs1.schedule_date, from_time= cs1.from_time, 
			to_time= cs1.to_time, instructor="_T-Instructor-00002", room="RM0002", do_not_save= 1)
		self.assertRaises(OverlapError, cs2.save)

	def test_instructor_conflict(self):
		cs1 = make_course_schedule_test_record(simulate= True)
		
		cs2 = make_course_schedule_test_record(from_time= cs1.from_time, to_time= cs1.to_time, 
			student_group="TC2-TP-2014-2015-2014-2015 (_Test Academic Term)", room="RM0002", do_not_save= 1)
		self.assertRaises(OverlapError, cs2.save)

	def test_room_conflict(self):
		cs1 = make_course_schedule_test_record(simulate= True)
		
		cs2 = make_course_schedule_test_record(from_time= cs1.from_time, to_time= cs1.to_time, 
			student_group="TC2-TP-2014-2015-2014-2015 (_Test Academic Term)", instructor="_T-Instructor-00002", do_not_save= 1)
		self.assertRaises(OverlapError, cs2.save)
		
	def test_no_conflict(self):
		cs1 = make_course_schedule_test_record(simulate= True)
		
		make_course_schedule_test_record(from_time= cs1.from_time, to_time= cs1.to_time, 
			student_group="TC2-TP-2014-2015-2014-2015 (_Test Academic Term)", instructor="_T-Instructor-00002", room="RM0002")

def make_course_schedule_test_record(**args):
	args = frappe._dict(args)

	course_schedule = frappe.new_doc("Course Schedule")
	course_schedule.student_group = args.student_group or "TC-TP-2014-2015-2014-2015 (_Test Academic Term)"
	course_schedule.course = args.course or "_Test Course"
	course_schedule.instructor = args.instructor or "_T-Instructor-00001"
	course_schedule.room = args.room or "RM0001"
	
	course_schedule.schedule_date = args.schedule_date or today()
	course_schedule.from_time = args.from_time or to_timedelta("01:00:00")
	course_schedule.to_time = args.to_time or course_schedule.from_time + datetime.timedelta(hours= 1)

	
	if not args.do_not_save:
		if args.simulate:
			while True:
				try:
					course_schedule.save()
					break
				except OverlapError:
					course_schedule.from_time = course_schedule.from_time + datetime.timedelta(minutes=10)
					course_schedule.to_time = course_schedule.from_time + datetime.timedelta(hours= 1)
		else:
			course_schedule.save()

	return course_schedule
