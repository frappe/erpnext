frappe.provide('frappe.medical');

frappe.pages['appointment-desk'].on_page_load = function(wrapper) {
	frappe.medical.appointment = new frappe.medical.Appointment(wrapper);
	frappe.breadcrumbs.add("Medical");
};

frappe.medical.Appointment = Class.extend({
	init: function(parent) {
		this.parent = parent;
		this.make_page();
		this.make_toolbar();
	},
	get_appointments: function() {
		var me = this;
		me.wrapper.empty();
		if (me.date.val() === '') return;
		if (me.physician.get_value() ==='' && me.department.get_value()==='') return;
		date = frappe.datetime.user_to_str(me.date.val());
		return frappe.call({
			method: "erpnext.medical.page.appointment_desk.appointment_desk.get_appointments",
			args: {date: date, physician: me.physician.get_value(), dept: me.department.get_value()},
			callback: function (r) {
				me.wrapper.empty();
				if(r.message){
					me.make_list(r.message)
				}else{
					$('<p class="text-muted" style="padding: 15px;">No Open, Scheduled or Pending appointments found for the day</p>').appendTo(me.wrapper);
				}
			}
		});
	},
	make_list: function (appointments) {
		var me = this;
		$.each(appointments, function(i, appointment){
			$(frappe.render_template("appointment-desk", {data: appointment})).appendTo(me.wrapper);
		});
		this.wrapper.find(".call").on("click", function() {
			$(this).removeClass("btn-primary");
			me.output_audio($(this).attr("data-patient"), $(this).attr("data-token"))
		});
		this.wrapper.find(".record-vitals").on("click", function() {
			me.create_vitals($(this).attr("data-patient"));
		});
		this.wrapper.find(".attend").on("click", function() {
			$(this).closest(".app-listing").hide();
			me.create_consultation($(this).attr("data-name"))
		});
	},
	output_audio: function (patient, token) {
		if('speechSynthesis'in window){
			var msg = new SpeechSynthesisUtterance();
			msg.text = patient + "token number " + token;
			msg.rate = 0.7;
			msg.voice = window.speechSynthesis.getVoices()[0];
			window.speechSynthesis.speak(msg);
		}
	},
	create_consultation: function (appointment) {
		frappe.call({
			method: "erpnext.medical.doctype.appointment.appointment.create_consultation",
			args: {appointment: appointment},
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},
	create_vitals:function (patient) {
		frappe.call({
			method:"erpnext.medical.doctype.vital_signs.vital_signs.create_vital_signs",
			args: {patient: patient},
			callback: function(data){
				if(!data.exc){
					var doclist = frappe.model.sync(data.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	},
	make_toolbar: function () {
		var me = this;
		this.department = this.page.add_field({label: __("Department"), fieldtype: 'Link', options: 'Medical Department'})
		this.department.$input.on('change', function(){
			me.get_appointments();
		});
		this.physician = this.page.add_field({label: __("Physician"), fieldtype: 'Link', options: 'Physician'})
		this.physician.$input.on('change', function(){
			me.get_appointments();
		});
		this.date = this.page.add_date(__("Date"), frappe.datetime.get_today())
		this.date.on('change', function(){
			me.get_appointments();
		});
		this.page.set_primary_action(__("Refresh"), function() { me.get_appointments(); }, "fa fa-refresh")
	},
	make_page: function() {
		if (this.page)
			return;

		frappe.ui.make_app_page({
			parent: this.parent,
			title: __('Appointment Desk'),
			single_column: true
		});
		this.page = this.parent.page;
		this.wrapper = $('<div></div>').appendTo(this.page.main);
	},
});
