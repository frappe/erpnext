frappe.provide('frappe.medical');

frappe.pages['service-desk'].on_page_load = function(wrapper) {
	frappe.medical.service_desk = new frappe.medical.ServiceDesk(wrapper);
	frappe.breadcrumbs.add("Medical");
};

frappe.medical.ServiceDesk = Class.extend({
	init: function(parent) {
		this.parent = parent;
		this.make_page();
		this.make_toolbar();
	},
	make_toolbar: function () {
		var me = this;
		this.patient = this.page.add_field({label: __("Patient"), fieldtype: 'Link', options: 'Patient'})
		this.patient.$input.on('change', function(){
			me.get_data(false);
		});
		this.physician = this.page.add_field({label: __("Physician"), fieldtype: 'Link', options: 'Physician'})
		this.physician.$input.on('change', function(){
			me.get_data(false);
		});
		this.from_date = this.page.add_date(__("From Date"), frappe.datetime.add_days(frappe.datetime.get_today(), -30))
		this.to_date = this.page.add_date(__("To Date"),  frappe.datetime.get_today())
		this.company = this.page.add_field({label: __("Company"), fieldtype: 'Link', options: 'Company', default: frappe.defaults.get_user_default("Company")})
		// this.from_date.on('change', function(){ me.get_data(false);});
		// this.to_date.on('change', function(){	me.get_data(false);});
		this.page.set_primary_action(__("Refresh"), function() {
			var menu_active = me.page.sidebar.find("li.active").attr("data-div");
			me.get_data(menu_active);
			me.page.wrapper.find('.btn-secondary').removeClass('disabled');
		}, "fa fa-refresh");
		this.page.set_secondary_action(__("Invoice"), function() {
			$(this).addClass('disabled');
			var active_div = me.page.sidebar.find("li.active").attr("data-div");
			var prescriptions = [];
			var doc_ids = [];
			$('#'+active_div).find('input:checked').each(function(){
				if($(this).attr('data-doc')){
					doc_ids.push($(this).attr('data-doc'));
				}else{
					if($(this).attr('data-id')){
						prescriptions.push($(this).attr('data-id'));
					};
				}
			})
			if (prescriptions.length > 0 || doc_ids.length > 0){
				me.create_invoice(active_div, prescriptions, doc_ids);
			}else{
				$(this).removeClass('disabled');
			}
		})
	},
	make_page: function() {
		if (this.page)
			return;

		frappe.ui.make_app_page({
			parent: this.parent,
			title: 'Service Desk',
		});
		this.page = this.parent.page;
		this.wrapper = $('<div></div>').appendTo(this.page.main);
	},
	get_data: function (menu_active) {
		var me = this;
		me.wrapper.empty();
		if (me.patient.get_value() ==='') return;
		if (me.from_date.val()==='' || me.to_date.val()===''){
			return;
		};
		var from = frappe.datetime.user_to_str(me.from_date.val());
		var to = frappe.datetime.user_to_str(me.to_date.val());

		return frappe.call({
			method: "erpnext.medical.page.service_desk.service_desk.get_patient_services_info",
			args: {patient: me.patient.get_value(), from_date: from, to_date: to, physician: me.physician.get_value(), company: me.company.get_value()},
			callback: function(r){
				if (r.message){
					data = r.message
					me.make_sidebar(data, menu_active)
				}else {
					me.page.sidebar.html('');
					$('<p class="text-muted" style="padding: 15px;">No documents found for the given period</p>').appendTo(me.wrapper);
				}
			}
		});
	},
	make_sidebar: function (data, menu_active) {
		var me = this;
		menu = { "Appointment" : data.appointments? "appointment": false, "Drug Prescription": data.drugs ? "drug" : false, "Lab Test": data.labtests ? "labtest" : false, "Procedure": data.procedures ? "procedure": false}
		me.page.sidebar.addClass("col-sm-3");
		me.page.sidebar.html(frappe.render_template("desk_sidebar", {menu: menu}));
		me.page.sidebar.find("a").on("click", function() {
			var li = $(this).parents("li:first");

			var show = li.attr("data-div");
			var hide = me.page.wrapper.find("li.active").attr("data-div");
			me.page.wrapper.find('#'+ hide).addClass("hidden")
			me.page.sidebar.find("li.active").removeClass("active");

			me.page.wrapper.find('#'+ show).removeClass("hidden");
			li.addClass("active");
		});
		me.show_data(data);
		if (menu_active && me.page.sidebar.find("." + menu_active)){
			me.page.sidebar.find("." + menu_active).click();
		}
		else{
			$(me.page.sidebar.find("a")[0]).click();
		}
	},
	show_data: function (data) {
		var me = this;
		status_color = {Draft:"lightgrey", Submitted: "lightblue", Paid: "lightgreen", Unpaid: "orange", Overdue: "red", Completed: "lightblue", Approved: "lightgreen", Cancelled: "red", Open: "lightgreen", Scheduled: "lightblue", Closed: "lightgrey"}
		if(data.appointments){
				$(frappe.render_template("appointment", {data: data.appointments, doc: "Appointment", color: status_color})).appendTo(me.wrapper);
		};
		if(data.drugs){
				$(frappe.render_template("drugs", {data: data.drugs, doc: "Drug Prescription"})).appendTo(me.wrapper);
		};
		if(data.labtests){
				$(frappe.render_template("service-desk", {data: data.labtests, doc: "Lab Test", color: status_color})).appendTo(me.wrapper);
		};
		if(data.procedures){
				$(frappe.render_template("service-desk", {data: data.procedures, doc: "Procedure", color: status_color})).appendTo(me.wrapper);
		};
		me.page.wrapper.find(".select-all").on("click", function(){
			group = $(this).closest(".list-group").find('input[type="checkbox"]').prop('checked', $(this).prop("checked"));
		});
		me.page.wrapper.find('.create-doc').on('click', function() {
			me.create_document($(this).attr('data-doc'), $(this).attr('data-id'), $(this).attr('data-item'), $(this).attr('data-inv'))
		});
		me.page.wrapper.find('.new-app').on('click', function() {
			appointment = frappe.model.get_new_doc("Appointment");
			appointment['patient'] = me.patient.get_value();
			appointment['physician'] = me.physician.get_value();;
			frappe.set_route('Form', "Appointment", appointment.name);
		});
	},
	create_invoice: function (div_id, prescriptions, doc_ids) {
		var me = this;
		if(div_id === "drug"){
			frappe.call({
				method: "erpnext.medical.doctype.consultation.consultation.create_drug_invoice",
				args: {company: me.company.get_value(), patient: me.patient.get_value(), prescriptions: prescriptions},
				callback: function (r) {
					if(!r.exe){
						me.page.btn_secondary.removeClass('disabled');
						var doclist = frappe.model.sync(r.message);
						frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
					}
				}
				});
		}else if (div_id === "labtest") {
			frappe.call({
				method: "erpnext.medical.doctype.lab_test.lab_test.create_invoice",
				args: {company: me.company.get_value(), patient: me.patient.get_value(), lab_tests: doc_ids, prescriptions: prescriptions},
				callback: function (r) {
					if(!r.exe){
						me.show_invoice_created(r.message)
					}
				}
			});
		}else if (div_id === "procedure") {
			frappe.call({
				method: "erpnext.medical.doctype.procedure.procedure.create_invoice",
				args: {company: me.company.get_value(), patient: me.patient.get_value(), procedures: doc_ids, prescriptions: prescriptions},
				callback: function (r) {
					if(!r.exe){
						me.show_invoice_created(r.message)
					}
				}
			});
		}else if (div_id === "appointment") {
			frappe.call({
				method: "erpnext.medical.doctype.appointment.appointment.create_invoice",
				args: {company: me.company.get_value(), patient: me.patient.get_value(), appointments: doc_ids},
				callback: function (r) {
					if(!r.exe){
						me.show_invoice_created(r.message)
					}
				}
			});
		}
	},
	show_invoice_created: function (invoice) {
		var me =this;
		me.page.btn_primary.click();
		me.page.btn_secondary.removeClass('disabled');
		if(invoice){
			frappe.msgprint(__("Sales Invoice <a href='#Form/Sales Invoice/{0}'>{0}</a> created", [invoice]))
		}
	},
	create_document: function (doc, line, template, invoice) {
		var me = this;
		if (doc === "Lab Test") {
			frappe.call({
				method: "erpnext.medical.doctype.lab_test.lab_test.create_lab_test_from_desk",
				args: {patient: me.patient.get_value(), template: template, prescription:line, invoice: invoice},
				callback: function (r) {
					if(!r.exe){
						me.page.btn_primary.click();
						if(r.message){
							frappe.msgprint(__("Lab Test <a href='#Form/Lab Test/{0}'>{0}</a> created", [r.message]))
						}
					}
				}
			});
		}else if (doc === "Procedure") {
			procedure = frappe.model.get_new_doc("Procedure");
			procedure['patient'] = me.patient.get_value();
			procedure['procedure_template'] = template;
			procedure['invoice'] = invoice;
			procedure['prescription'] = line;
			frappe.set_route('Form', "Procedure", procedure.name);
		}
	}
});
