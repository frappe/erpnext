# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe


class TestShiftType(unittest.TestCase):
	pass


def setup_shift_type(**args):
	args = frappe._dict(args)
	shift_type = frappe.new_doc("Shift Type")
	shift_type.__newname = args.shift_type or "_Test Shift"
	shift_type.start_time = args.start_time or "08:00:00"
	shift_type.end_time = args.end_time or "12:00:00"
	shift_type.holiday_list = args.holiday_list
	shift_type.enable_auto_attendance = 1

	shift_type.determine_check_in_and_check_out = (
		args.determine_check_in_and_check_out
		or "Alternating entries as IN and OUT during the same shift"
	)
	shift_type.working_hours_calculation_based_on = (
		args.working_hours_calculation_based_on or "First Check-in and Last Check-out"
	)
	shift_type.begin_check_in_before_shift_start_time = (
		args.begin_check_in_before_shift_start_time or 60
	)
	shift_type.allow_check_out_after_shift_end_time = args.allow_check_out_after_shift_end_time or 60

	shift_type.save()

	return shift_type
