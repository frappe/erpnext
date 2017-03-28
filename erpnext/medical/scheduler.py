# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, get_time
from frappe import msgprint, _
import datetime
from datetime import timedelta
import calendar

def check_overlap(doctype, df, dn, start, end):
	scheduled = frappe.db.sql("""select name, start_dt, end_dt from `tab{0}` where {1}='{2}' and status!='cancelled' and ((start_dt > '{3}' and start_dt < '{4}') or (end_dt > '{3}' and end_dt < '{4}') or (start_dt >='{3}' and end_dt <='{4}'))""".format(doctype, df, dn, start, end))
	if scheduled:
		return False
	else:
		return True

def get_all_slots(start, end, time_delta):
	interval = int(time_delta.total_seconds() / 60)
	slots = []
	while start < end:
		slots.append(start)
		start += timedelta(minutes=interval)
	return slots

def get_nearest_slot(date, time, duration, slots):
	dt = datetime.datetime.combine(date, time)
	start  = min(slots, key=lambda d: abs(d - dt))
	end = start + datetime.timedelta(hours = duration.hour, minutes=duration.minute)
	return start, end

def get_dict_by_token(start, end, token, slots=None):
	if token:
		if slots: return {"start": start, "end": end, "token": slots.index(start) + 1}
		else: return {"start": start, "end": end, "token": 1}
	else:
		return {"start": start, "end": end}

def get_availability_from_schedule(doctype, df, dn, schedules, token, date, time):
	data = []
	for line in schedules:
		duration = get_time(line["average"])
		scheduled_items = frappe.db.sql("""select start_dt from `tab{0}` where status!="Cancelled" and {1}='{2}' and start_dt between '{3}' and '{4}' order by start_dt""".format(doctype, df, dn, line["start"], line["end"]))
		if not scheduled_items and not time:
			start = datetime.datetime.combine(date, get_time(line["start"]))
			end = start + datetime.timedelta(hours = duration.hour, minutes=duration.minute)
			data.append(get_dict_by_token(start, end, token))
			continue

		slots = get_all_slots(line["start"], line["end"], line["average"])
		if scheduled_items:
			scheduled_map = set(map(lambda x : x[0], scheduled_items))
			slots_free = [x for x in slots if x not in scheduled_map]
			if not slots_free:
				data.append({"msg": _("No slots left for schedule {0} {1}").format(line["start"], line["end"])})
				continue
			if time:
				start, end = get_nearest_slot(date, time, duration, slots_free)
				data.append(get_dict_by_token(start, end, token, slots))
			else:
				end = slots_free[0] + datetime.timedelta(hours = duration.hour, minutes=duration.minute)
				data.append(get_dict_by_token(slots_free[0], end, token, slots))
		else:
			start, end = get_nearest_slot(date, time, duration, slots)
			data.append(get_dict_by_token(start, end, token, slots))
	return data

def check_availability(doctype, df, token, dt, dn, date, time, end_dt):
	# params doctype: doc to schedule,
	#df: doctype relation(O2M) field name to resource,
	#token: boolean, token required or not,
	#dt: resource doctype,
	#dn: resource docname,
	#date: date to check availability
	#time: time to check availability
	#end_dt: datetime end time to check availability
	resource = frappe.get_doc(dt, dn)
	date = getdate(date)
	if time: time = get_time(time)
	day = calendar.day_name[date.weekday()]
	availability = []
	schedules = []
	if hasattr(resource, "schedule") and resource.schedule: #build schedules based on work schedule
		day_sch = filter(lambda x : x.day == day, resource.schedule)
		if not day_sch:
			availability.append({"msg": _("{0} not available on {1} {2}").format(dn, day, date)})
			return availability
		for line in day_sch:
			if time:
				if(time>=get_time(line.start) and time <=get_time(line.end)):#add only if time between start and end
					schedules.append({"start": datetime.datetime.combine(date, get_time(line.start)), "end": datetime.datetime.combine(date, get_time(line.end)), "average": line.average})
			else:
				schedules.append({"start": datetime.datetime.combine(date, get_time(line.start)), "end": datetime.datetime.combine(date, get_time(line.end)), "average": line.average})

		if time and not schedules:
			msg = ""
			for sch in day_sch:
				msg += " &emsp;&emsp;{0}-{1}".format(sch.start, sch.end)
			availability.append({"msg": _("Schedules for {0} on  {1}   {2} ").format(dn, date, msg)})
		if schedules:
			availability.extend(get_availability_from_schedule(doctype, df, dn, schedules, token, date, time))

	elif hasattr(resource, "avg_time") and resource.avg_time: #build schedules based on avg_time for entire day
		schedules.append({"start": datetime.datetime.combine(date, get_time("00:00")), "end": datetime.datetime.combine(date, get_time("23:59")), "average": resource.avg_time})
		availability.extend(get_availability_from_schedule(doctype, df, dn, schedules, token, date, time))

	else: #check overlaping schedules for the resource for the given period
		if not (time and end_dt):
			availability.append({"msg": _("No Work Schedule or average time specified for {0} {1}").format(dt,dn)})
			return availability

		start = datetime.datetime.combine(date, time)
		if(check_overlap(doctype, df, dn, start, end_dt)):
			availability.append({"msg": _("{0} {1} available for given period").format(dt,dn)})
		else:
			availability.append({"msg": _("{0} {1} already scheduled for given period").format(dt, dn)})
	return availability
