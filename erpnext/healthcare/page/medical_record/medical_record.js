frappe.provide("frappe.medical_record");
frappe.pages['medical_record'].on_page_load = function(wrapper) {
	var me = this;
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Medical Record',
	});

	frappe.breadcrumbs.add("Medical");

	page.main.html(frappe.render_template("patient_select", {}));
	var patient = frappe.ui.form.make_control({
		parent: page.main.find(".patient"),
		df: {
			fieldtype: "Link",
			options: "Patient",
			fieldname: "patient",
			change: function(){
				page.main.find(".frappe-list").html("");
				draw_page(patient.get_value(), me);
			}
		},
		only_input: true,
	});
	patient.refresh();


	this.page.main.on("click", ".medical_record-message", function() {
		var	doctype = $(this).attr("data-doctype"),
			docname = $(this).attr("data-docname");

		if (doctype && docname) {
			frappe.route_options = {
				scroll_to: { "doctype": doctype, "name": docname }
			};
			frappe.set_route(["Form", doctype, docname]);
		}
	});

	this.page.sidebar.on("click", ".edit-details", function() {
		patient = patient.get_value();
		if (patient) {
			frappe.set_route(["Form", "Patient", patient]);
		}
	});

};

frappe.pages['medical_record'].refresh = function() {
	var me = this;

	if(frappe.route_options) {
		if(frappe.route_options.patient){
			me.page.main.find(".frappe-list").html("");
			var patient = frappe.route_options.patient;
			draw_page(patient,me);
			me.page.main.find("[data-fieldname='patient']").val(patient);
			frappe.route_options = null;
		}
	}
};
var show_patient_info = function(patient, me){
	frappe.call({
		"method": "erpnext.healthcare.doctype.patient.patient.get_patient_detail",
		args: {
			patient: patient
		},
		callback: function (r) {
			var data = r.message;
			var details = "";
			if(data.email) details += "<br><b>Email :</b> " + data.email;
			if(data.mobile) details += "<br><b>Mobile :</b> " + data.mobile;
			if(data.occupation) details += "<br><b>Occupation :</b> " + data.occupation;
			if(data.blood_group) details += "<br><b>Blood group : </b> " + data.blood_group;
			if(data.allergies) details +=  "<br><br><b>Allergies : </b> "+  data.allergies;
			if(data.medication) details +=  "<br><b>Medication : </b> "+  data.medication;
			if(data.alcohol_current_use) details +=  "<br><br><b>Alcohol use : </b> "+  data.alcohol_current_use;
			if(data.alcohol_past_use) details +=  "<br><b>Alcohol past use : </b> "+  data.alcohol_past_use;
			if(data.tobacco_current_use) details +=  "<br><b>Tobacco use : </b> "+  data.tobacco_current_use;
			if(data.tobacco_past_use) details +=  "<br><b>Tobacco past use : </b> "+  data.tobacco_past_use;
			if(data.medical_history) details +=  "<br><br><b>Medical history : </b> "+  data.medical_history;
			if(data.surgical_history) details +=  "<br><b>Surgical history : </b> "+  data.surgical_history;
			if(data.surrounding_factors) details +=  "<br><br><b>Occupational hazards : </b> "+  data.surrounding_factors;
			if(data.other_risk_factors) details += "<br><b>Other risk factors : </b> " + data.other_risk_factors;
			if(data.patient_details) details += "<br><br><b>More info : </b> " + data.patient_details;

			if(details){
				details = "<div style='padding-left:10px; font-size:13px;' align='center'></br><b class='text-muted'>Patient Details</b>" + details + "</div>";
			}

			var vitals = "";
			if(data.temperature) vitals += "<br><b>Temperature :</b> " + data.temperature;
			if(data.pulse) vitals += "<br><b>Pulse :</b> " + data.pulse;
			if(data.respiratory_rate) vitals += "<br><b>Respiratory Rate :</b> " + data.respiratory_rate;
			if(data.bp) vitals += "<br><b>BP :</b> " + data.bp;
			if(data.bmi) vitals += "<br><b>BMI :</b> " + data.bmi;
			if(data.height) vitals += "<br><b>Height :</b> " + data.height;
			if(data.weight) vitals += "<br><b>Weight :</b> " + data.weight;
			if(data.signs_date) vitals += "<br><b>Date :</b> " + data.signs_date;

			if(vitals){
				vitals = "<div style='padding-left:10px; font-size:13px;' align='center'></br><b class='text-muted'>Vital Signs</b>" + vitals + "<br></div>";
				details = vitals + details;
			}
			if(details) details += "<div align='center'><br><a class='btn btn-default btn-sm edit-details'>Edit Details</a></b> </div>";

			me.page.sidebar.addClass("col-sm-3");
			me.page.sidebar.html(details);
			me.page.wrapper.find(".layout-main-section-wrapper").addClass("col-sm-9");
		}
	});
};
var draw_page = function(patient, me){
	frappe.model.with_doctype("Patient Medical Record", function() {
		me.page.list = new frappe.ui.BaseList({
			hide_refresh: true,
			page: me.page,
			method: 'erpnext.healthcare.page.medical_record.medical_record.get_feed',
			args: {name: patient},
			parent: $("<div></div>").appendTo(me.page.main),
			render_view: function(values) {
				var me = this;
				var wrapper = me.page.main.find(".result-list").get(0);
				values.map(function (value) {
					var row = $('<div class="list-row">').data("data", value).appendTo($(wrapper)).get(0);
					new frappe.medical_record.Feed(row, value);
				});
			},
			show_filters: true,
			doctype: "Patient Medical Record",
		});
		show_patient_info(patient, me);
		me.page.list.run();
	});
};

frappe.medical_record.last_feed_date = false;
frappe.medical_record.Feed = Class.extend({
	init: function(row, data) {
		this.scrub_data(data);
		this.add_date_separator(row, data);
		if(!data.add_class)
			data.add_class = "label-default";

		data.link = "";
		if (data.reference_doctype && data.reference_name) {
			data.link = frappe.format(data.reference_name, {fieldtype: "Link", options: data.reference_doctype},
				{label: __(data.reference_doctype)});
		}

		$(row)
			.append(frappe.render_template("medical_record_row", data))
			.find("a").addClass("grey");
	},
	scrub_data: function(data) {
		data.by = frappe.user.full_name(data.owner);
		data.imgsrc = frappe.utils.get_file_link(frappe.user_info(data.owner).image);

		data.icon = "icon-flag";
	},
	add_date_separator: function(row, data) {
		var date = frappe.datetime.str_to_obj(data.creation);
		var last = frappe.medical_record.last_feed_date;

		if((last && frappe.datetime.obj_to_str(last) != frappe.datetime.obj_to_str(date)) || (!last)) {
			var diff = frappe.datetime.get_day_diff(frappe.datetime.get_today(), frappe.datetime.obj_to_str(date));
			if(diff < 1) {
				var pdate = 'Today';
			} else if(diff < 2) {
				pdate = 'Yesterday';
			} else {
				pdate = frappe.datetime.global_date_format(date);
			}
			data.date_sep = pdate;
			data.date_class = pdate=='Today' ? "date-indicator blue" : "date-indicator";
		} else {
			data.date_sep = null;
			data.date_class = "";
		}
		frappe.medical_record.last_feed_date = date;
	}
});
