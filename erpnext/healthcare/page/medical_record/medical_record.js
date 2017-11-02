frappe.provide("frappe.medical_record");
frappe.pages['medical_record'].on_page_load = function(wrapper) {
	var me = this;
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Medical Record',
		single_column: true
	});

	frappe.breadcrumbs.add("Healthcare");

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
				patient.refresh();
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
			details = frappe.render_template("patient_details", {"data": data});
			me.page.wrapper.find(".patient-details").html(details);
			me.page.wrapper.find(".section-patient-details").removeClass("hide")
			me.page.wrapper.find(".patient-details").removeClass("hide");
			return
		}
	});
};
var draw_page = function(patient, me){
	if(!patient){
		me.page.wrapper.find(".section-patient-details").addClass("hide");
		me.page.wrapper.find(".patient-details").addClass("hide");
		return
	}
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
