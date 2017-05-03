// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Unit', {
	refresh: function(frm) {

	}
});


frappe.ui.form.on("Work Schedule", "limit", function(frm, cdt, cdn) {
	var child = locals[cdt][cdn]
	if(child.limit){
		duration = moment.utc(moment(child.end,"HH:mm:ss").diff(moment(child.start,"HH:mm:ss"))).format("HH:mm:ss")

		//I am combining the snippets I found in multiple pages.
		//Conversion of hh:mm:ss to seconds, divided by the limit and then again convert to hh:mm:ss.
		var hms =  duration  // your input string
		var a = hms.split(':'); // split it at the colons

		// minutes are worth 60 seconds. Hours are worth 60 minutes.
		var seconds = (+a[0]) * 60 * 60 + (+a[1]) * 60 + (+a[2]);
		var newSeconds= seconds/child.limit;

		// multiply by 1000 because Date() requires miliseconds
		var date = new Date(newSeconds * 1000);
		var hh = date.getUTCHours();
		var mm = date.getUTCMinutes();
		var ss = date.getSeconds();
		// If you were building a timestamp instead of a duration, you would uncomment the following line to get 12-hour (not 24) time
		// if (hh > 12) {hh = hh % 12;}
		// These lines ensure you have two-digits
		if (hh < 10) {hh = "0"+hh;}
		if (mm < 10) {mm = "0"+mm;}
		if (ss < 10) {ss = "0"+ss;}
		// This formats your string to HH:MM:SS
		var t = hh+":"+mm+":"+ss;
		frappe.model.set_value(cdt, cdn, 'average',t)
	}
});
