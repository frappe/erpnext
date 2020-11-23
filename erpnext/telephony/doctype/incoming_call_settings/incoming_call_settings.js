// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

function timeToSeconds(time_str){
	// Convert time string of format HH:MM:SS into seconds.
	let seq = time_str.split(':');
	seq = seq.map((n) => parseInt(n));
	return (seq[0]*60*60) + (seq[1]*60) + seq[2];
}

function numberSort(array, ascending=true){
	let array_copy = [...array]
	if (ascending){
		array_copy.sort((a, b) => a-b); // ascending order
	} else {
		array_copy.sort((a, b) => b-a); // descending order
	}
	return array_copy;
}

function groupBy(items, key){
	// Group the list of items using the given key.
	const obj = {};
	items.forEach((item) => {
		if(item[key] in obj){
			obj[item[key]].push(item);
		} else {
			obj[item[key]] = [item];
		}
	});
	return obj;
}

function checkTimeSlotOverlap(timeslot_1, timeslot_2){
	/// Timeslot is a an array of length 2 ex: [from_time, to_time]
	/// time in timeslot is an integer represents number of seconds.
	let ts1 = numberSort(timeslot_1);
	let ts2 = numberSort(timeslot_2);

	if ((ts1[0] < ts2[0] && ts1[1] <= ts2[0]) || (ts1[0] >= ts2[1] && ts1[1] > ts2[1])){
		return false;
	}
	return true;
}

function validateCallSchedule(schedule){
	validateCallScheduleTimeslot(schedule);
	validateCallScheduleOverlaps(schedule);
}

function validateCallScheduleTimeslot(schedule){
	// Make sure that to time slot is ahead of from time slot.
	let errors = []

	for (let row in schedule)
	{
		let record = schedule[row];
		let from_time_in_secs = timeToSeconds(record.from_time);
		let to_time_in_secs = timeToSeconds(record.to_time);
		if (from_time_in_secs >= to_time_in_secs)
		{
			errors.push(`Call Schedule Row ${row}: To time slot should always be ahead of From time slot.`);
		}
	}

	if (errors.length > 0)
	{
		frappe.throw(errors.join("<br/>"));
	}
}

function isCallScheduleOverlapped(day_schedule){
	// Check if any time slots are overlapped in a day schedule.
	let timeslots = [];
	day_schedule.forEach((record)=> {
		timeslots.push([timeToSeconds(record.from_time), timeToSeconds(record.to_time)]);
	});

	if (timeslots.length < 2){
		return false;
	}

	timeslots = numberSort(timeslots);

	// Sorted timeslots will be in ascending order if not overlapped.
	for (let i=1; i < timeslots.length; i++){
		if(checkTimeSlotOverlap(timeslots[i-1], timeslots[i])){
			return true;
		}
	}
	return false;
}

function validateCallScheduleOverlaps(schedule){
	let group_by_day = groupBy(schedule, 'day_of_week');
	for (const [day, day_schedule] of Object.entries(group_by_day)) {
		if(isCallScheduleOverlapped(day_schedule)){
			frappe.throw(`Please fix overlapping time slots for ${day}.`);
		}
	}
};

frappe.ui.form.on('Incoming Call Settings', {
	validate(frm)
	{
		validateCallSchedule(frm.doc.call_handling_schedule);
	}
});

