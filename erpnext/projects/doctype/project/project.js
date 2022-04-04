// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide('erpnext.projects');

{% include 'erpnext/vehicles/vehicle_checklist.js' %};

erpnext.projects.ProjectController = frappe.ui.form.Controller.extend({
	setup: function() {
		this.setup_make_methods();
		this.setup_indicator();
	},

	onload: function () {
		this.setup_queries();
	},

	refresh: function () {
		this.set_dynamic_link();
		this.setup_route_options();
		this.setup_naming_series();
		erpnext.hide_company();
		this.setup_web_link();
		this.setup_buttons();
		this.set_percent_complete_read_only();
		this.set_cant_change_read_only();
		this.set_applies_to_read_only();
		this.toggle_vehicle_odometer_fields();
		this.make_vehicle_checklist();
		this.set_sales_data_html();
	},

	setup_queries: function () {
		var me = this;

		me.frm.set_query('customer', 'erpnext.controllers.queries.customer_query');
		me.frm.set_query('bill_to', 'erpnext.controllers.queries.customer_query');
		if (me.frm.fields_dict.vehicle_owner) {
			me.frm.set_query('vehicle_owner', 'erpnext.controllers.queries.customer_query');
		}

		me.frm.set_query('contact_person', erpnext.queries.contact_query);
		me.frm.set_query('customer_address', erpnext.queries.address_query);

		if(me.frm.fields_dict.insurance_company) {
			me.frm.set_query("insurance_company", function(doc) {
				return {
					query: "erpnext.controllers.queries.customer_query",
					filters: {is_insurance_company: 1}
				};
			});
		}

		me.frm.set_query("user", "users", function () {
			return {
				query: "erpnext.projects.doctype.project.project.get_users_for_project"
			};
		});

		// sales order
		me.frm.set_query('sales_order', function () {
			var filters = {
				'project': ["in", me.frm.doc.__islocal ? [""] : [me.frm.doc.name, ""]]
			};

			if (me.frm.doc.customer) {
				filters["customer"] = me.frm.doc.customer;
			}

			return {
				filters: filters
			};
		});

		// depreciation item
		me.frm.set_query('depreciation_item_code', 'non_standard_depreciation', () => erpnext.queries.item({
			is_stock_item: 1,
		}));
	},

	set_dynamic_link: function () {
		frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'customer', doctype: 'Customer'};
	},

	setup_route_options: function () {
		var me = this;

		var sales_order_field = me.frm.get_docfield("sales_order");
		if (sales_order_field) {
			sales_order_field.get_route_options_for_new_doc = function (field) {
				if (me.frm.is_new()) return;
				return {
					"customer": me.frm.doc.customer,
					"project": me.frm.doc.name
				};
			};
		}

		var vehicle_field = me.frm.get_docfield("applies_to_vehicle");
		if (vehicle_field) {
			vehicle_field.get_route_options_for_new_doc = function () {
				return {
					"item_code": me.frm.doc.applies_to_item,
					"item_name": me.frm.doc.applies_to_item_name
				}
			}
		}
	},

	setup_indicator: function () {
		this.frm.set_indicator_formatter('title', function (doc) {
			let indicator = 'orange';
			if (doc.status == 'Overdue') {
				indicator = 'red';
			} else if (doc.status == 'Cancelled') {
				indicator = 'dark grey';
			} else if (doc.status == 'Closed') {
				indicator = 'green';
			}
			return indicator;
		});
	},

	setup_naming_series: function () {
		if (frappe.defaults.get_default("project_naming_by")!="Naming Series") {
			this.frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}
	},

	setup_web_link: function () {
		if (this.frm.doc.__islocal) {
			this.frm.web_link && this.frm.web_link.remove();
		} else {
			this.frm.add_web_link("/projects?project=" + encodeURIComponent(this.frm.doc.name));
			this.frm.trigger('show_dashboard');
		}
	},

	setup_make_methods: function () {
		var me = this;

		me.frm.custom_make_buttons = {
			'Sales Invoice': 'Sales Invoice',
			'Delivery Note': 'Delivery Note',
			'Vehicle Service Receipt': 'Receive Vehicle',
			'Vehicle Gate Pass': 'Create Gate Pass',
			'Vehicle Log': 'Update Odometer',
		};

		var make_method_doctypes = [
			'Maintenance Visit', 'Warranty Claim', 'Quality Inspection', 'Timesheet',
		];

		me.frm.make_methods = {};
		$.each(make_method_doctypes, function (i, dt) {
			me.frm.make_methods[dt] = () => me.open_form(dt);
		});
	},

	setup_buttons: function() {
		var me = this;

		if (me.frm.fields_dict.receive_vehicle_btn) {
			me.frm.set_df_property('receive_vehicle_btn', 'hidden', 1);
		}
		if (me.frm.fields_dict.deliver_vehicle_btn) {
			me.frm.set_df_property('receive_vehicle_btn', 'hidden', 1);
		}

		if (!me.frm.is_new()) {
			me.frm.add_custom_button(__('Completed'), () => {
				me.set_status('Completed');
			}, __('Set Status'));

			me.frm.add_custom_button(__('Cancelled'), () => {
				me.set_status('Cancelled');
			}, __('Set Status'));

			if (frappe.model.can_read("Task")) {
				me.frm.add_custom_button(__("Gantt Chart"), function () {
					frappe.route_options = {
						"project": me.frm.doc.name
					};
					frappe.set_route("List", "Task", "Gantt");
				}, __("Tasks"));

				me.frm.add_custom_button(__("Kanban Board"), () => {
					frappe.call('erpnext.projects.doctype.project.project.create_kanban_board_if_not_exists', {
						project: me.frm.doc.name
					}).then(() => {
						frappe.set_route('List', 'Task', 'Kanban', me.frm.doc.name);
					});
				}, __("Tasks"));
			}

			me.frm.add_custom_button(__('Duplicate Project with Tasks'), () => me.create_duplicate(), __("Tasks"));

			if (me.frm.doc.applies_to_vehicle) {
				if (frappe.model.can_create("Vehicle Service Receipt") && me.frm.doc.vehicle_status == "Not Received") {
					me.frm.add_custom_button(__("Receive Vehicle"), () => me.receive_vehicle_btn(), __("Vehicle"));
					if (me.frm.fields_dict.receive_vehicle_btn) {
						me.frm.set_df_property('receive_vehicle_btn', 'hidden', 0);
					}
				}

				if (frappe.model.can_create("Vehicle Gate Pass") && me.frm.doc.vehicle_status == "In Workshop") {
					me.frm.add_custom_button(__("Create Gate Pass"), () => me.deliver_vehicle_btn(), __("Vehicle"));
					if (me.frm.fields_dict.deliver_vehicle_btn) {
						me.frm.set_df_property('deliver_vehicle_btn', 'hidden', 0);
					}
				}

				if (frappe.model.can_create("Vehicle Log")) {
					me.frm.add_custom_button(__("Update Odometer"), () => me.make_odometer_log(), __("Vehicle"));
				}
			}

			if (frappe.model.can_create("Sales Invoice")) {
				me.frm.add_custom_button(__("Sales Invoice"), () => me.make_sales_invoice(), __("Create"));
			}

			if (frappe.model.can_create("Delivery Note")) {
				me.frm.add_custom_button(__("Delivery Note"), () => me.make_delivery_note(), __("Create"));
			}
		}
	},

	toggle_vehicle_odometer_fields: function () {
		if (this.frm.fields_dict.vehicle_first_odometer && this.frm.fields_dict.vehicle_last_odometer) {
			var first_odometer_read_only = cint(this.frm.doc.vehicle_first_odometer);
			var last_odometer_read_only = !cint(this.frm.doc.vehicle_first_odometer)
				|| cint(this.frm.doc.vehicle_last_odometer) !== cint(this.frm.doc.vehicle_first_odometer);

			if (!this.frm.doc.applies_to_vehicle) {
				first_odometer_read_only = 0;
				last_odometer_read_only = 0;
			}

			this.frm.set_df_property("vehicle_first_odometer", "read_only", first_odometer_read_only);
			this.frm.set_df_property("vehicle_last_odometer", "read_only", last_odometer_read_only);
		}
	},

	set_cant_change_read_only: function () {
		const cant_change_fields = (this.frm.doc.__onload && this.frm.doc.__onload.cant_change_fields) || {};
		$.each(cant_change_fields, (fieldname, cant_change) => {
			this.frm.set_df_property(fieldname, 'read_only', cant_change ? 1 : 0);
		});
	},

	set_applies_to_read_only: function() {
		var me = this;
		var read_only_fields = [
			'applies_to_item', 'applies_to_item_name',
			'vehicle_license_plate', 'vehicle_unregistered',
			'vehicle_chassis_no', 'vehicle_engine_no',
			'vehicle_color', 'vehicle_warranty_no',
		];

		var read_only = me.frm.doc.applies_to_vehicle || me.frm.doc.vehicle_status != "Not Received" ? 1 : 0;

		$.each(read_only_fields, function (i, f) {
			if (me.frm.fields_dict[f]) {
				me.frm.set_df_property(f, "read_only", read_only);
			}
		});
	},

	create_duplicate: function() {
		var me = this;
		return new Promise(resolve => {
			frappe.prompt('Project Name', (data) => {
				frappe.xcall('erpnext.projects.doctype.project.project.create_duplicate_project',
					{
						prev_doc: me.frm.doc,
						project_name: data.value
					}).then(() => {
					frappe.set_route('Form', "Project", data.value);
					frappe.show_alert(__("Duplicate project has been created"));
				});
				resolve();
			});
		});
	},

	set_status: function(status) {
		var me = this;
		frappe.confirm(__('Set Project and all Tasks to status {0}?', [status.bold()]), () => {
			frappe.xcall('erpnext.projects.doctype.project.project.set_project_status',
				{project: me.frm.doc.name, status: status}).then(() => { /* page will auto reload */ });
		});
	},

	customer: function () {
		this.get_customer_details();
	},

	customer_address: function() {
		erpnext.utils.get_address_display(this.frm, "customer_address");
	},

	contact_person: function() {
		erpnext.utils.get_contact_details(this.frm);
	},

	get_customer_details: function () {
		var me = this;

		return frappe.call({
			method: "erpnext.projects.doctype.project.project.get_customer_details",
			args: {
				args: {
					doctype: me.frm.doc.doctype,
					company: me.frm.doc.company,
					customer: me.frm.doc.customer,
					bill_to: me.frm.doc.bill_to,
				}
			},
			callback: function (r) {
				if (r.message && !r.exc) {
					me.frm.set_value(r.message);
				}
			}
		});
	},

	applies_to_item: function () {
		this.get_applies_to_details();
	},
	applies_to_vehicle: function () {
		this.set_applies_to_read_only();
		this.get_applies_to_details();
	},
	vehicle_owner: function () {
		if (!this.frm.doc.vehicle_owner) {
			this.frm.doc.vehicle_owner_name = null;
		}
	},

	vehicle_chassis_no: function () {
		erpnext.utils.format_vehicle_id(this.frm, 'vehicle_chassis_no');
	},
	vehicle_engine_no: function () {
		erpnext.utils.format_vehicle_id(this.frm, 'vehicle_engine_no');
	},
	vehicle_license_plate: function () {
		erpnext.utils.format_vehicle_id(this.frm, 'vehicle_license_plate');
	},

	get_applies_to_details: function () {
		var me = this;
		var args = this.get_applies_to_args();
		return frappe.call({
			method: "erpnext.stock.get_item_details.get_applies_to_details",
			args: {
				args: args
			},
			callback: function(r) {
				if(!r.exc) {
					return me.frm.set_value(r.message);
				}
			}
		});
	},

	get_applies_to_args: function () {
		return {
			applies_to_item: this.frm.doc.applies_to_item,
			applies_to_vehicle: this.frm.doc.applies_to_vehicle,
			doctype: this.frm.doc.doctype,
			name: this.frm.doc.name,
		}
	},

	serial_no: function () {
		var me = this;
		if (me.frm.doc.serial_no) {
			frappe.call({
				method: "erpnext.stock.doctype.serial_no.serial_no.get_serial_no_item_customer",
				args: {
					serial_no: me.frm.doc.serial_no
				},
				callback: function (r) {
					if (r.message) {
						me.frm.set_value(r.message);
					}
				}
			});
		}
	},

	vehicle_checklist: function () {
		this.make_vehicle_checklist();
	},
	vehicle_checklist_add: function () {
		this.make_vehicle_checklist();
	},
	vehicle_checklist_remove: function () {
		this.make_vehicle_checklist();
	},
	checklist_item: function () {
		this.make_vehicle_checklist();
	},
	checklist_item_checked: function () {
		this.refresh_checklist();
	},

	make_vehicle_checklist: function () {
		if (this.frm.fields_dict.vehicle_checklist_html) {
			var is_read_only = cint(this.frm.doc.__onload && this.frm.doc.__onload.cant_change_fields && this.frm.doc.__onload.cant_change_fields.vehicle_checklist);

			this.frm.vehicle_checklist_editor = erpnext.vehicles.make_vehicle_checklist(this.frm,
				this.frm.fields_dict.vehicle_checklist_html.wrapper, is_read_only);
		}
	},

	refresh_checklist: function () {
		if (this.frm.vehicle_checklist_editor) {
			this.frm.vehicle_checklist_editor.render_checklist();
		}
	},

	set_sales_data_html: function () {
		this.frm.get_field("stock_items_html").$wrapper.html(this.frm.doc.__onload && this.frm.doc.__onload.stock_items_html || '');
		this.frm.get_field("service_items_html").$wrapper.html(this.frm.doc.__onload && this.frm.doc.__onload.service_items_html || '');
		this.frm.get_field("sales_summary_html").$wrapper.html(this.frm.doc.__onload && this.frm.doc.__onload.sales_summary_html || '');
	},

	receive_vehicle_btn: function () {
		this.make_vehicle_receipt();
	},
	deliver_vehicle_btn: function () {
		this.make_vehicle_gate_pass();
	},

	vehicle_workshop: function () {
		this.get_vehicle_workshop_details();
	},

	project_type: function () {
		this.get_project_type_defaults();
	},

	get_vehicle_workshop_details: function () {
		var me = this;

		if (me.frm.doc.vehicle_workshop) {
			return frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_workshop.vehicle_workshop.get_vehicle_workshop_details",
				args: {
					vehicle_workshop: me.frm.doc.vehicle_workshop
				},
				callback: function (r) {
					if (!r.exc) {
						return me.frm.set_value(r.message);
					}
				}
			});
		}
	},

	get_project_type_defaults: function () {
		var me = this;

		if (me.frm.doc.project_type) {
			return frappe.call({
				method: "erpnext.projects.doctype.project_type.project_type.get_project_type_defaults",
				args: {
					project_type: me.frm.doc.project_type
				},
				callback: function (r) {
					if (!r.exc) {
						return me.frm.set_value(r.message);
					}
				}
			});
		}
	},

	collect_progress: function() {
		this.frm.set_df_property("message", "reqd", this.frm.doc.collect_progress);
	},

	percent_complete: function () {
		this.set_percent_complete_read_only();
	},

	set_percent_complete_read_only: function () {
		var read_only = cint(this.frm.doc.percent_complete_method != "Manual");
		this.frm.set_df_property("percent_complete", "read_only", read_only);
	},

	open_form: function (doctype) {
		var me = this;

		var item_table_fieldnames = {
			'Maintenance Visit': 'purposes',
			'Stock Entry': 'items',
			'Delivery Note': 'items',
			'Timesheet': 'time_logs',
		};

		var items_fieldname = item_table_fieldnames[doctype];

		frappe.new_doc(doctype, {
			customer: me.frm.doc.customer,
			party: me.frm.doc.customer,
			party_name: me.frm.doc.customer,
			quotation_to: 'Customer',
			party_type: 'Customer',
			project: me.frm.doc.name,
			item_code: me.frm.doc.item_code,
			serial_no: me.frm.doc.serial_no,
			item_serial_no: me.frm.doc.serial_no
		}).then(r => {
			if (items_fieldname) {
				cur_frm.doc[items_fieldname] = [];
				var child = cur_frm.add_child(items_fieldname, {
					project: me.frm.doc.name
				});
				cur_frm.refresh_field(items_fieldname);
			}
		});
	},

	make_sales_invoice: function () {
		var me = this;
		me.frm.check_if_unsaved();

		if (me.frm.doc.default_depreciation_percentage || (me.frm.doc.non_standard_depreciation || []).length) {
			var html = `
<div class="text-center">
	<button type="button" class="btn btn-primary btn-bill-customer">${__("Bill Depreciation Amount Only to <b>Customer (User)</b>")}</button>
	<br/><br/>
	<button type="button" class="btn btn-primary btn-bill-insurance">${__("Bill After Depreciation Amount to <b>Insurance Company</b>")}</button>
</div>
`;

			var dialog = new frappe.ui.Dialog({
				title: __("Depreciation Invoice"),
				fields: [
					{fieldtype: "HTML", options: html}
				],
			});

			dialog.show();

			$('.btn-bill-customer', dialog.$wrapper).click(function () {
				dialog.hide();
				me._make_sales_invoice('Depreciation Amount Only');
			});
			$('.btn-bill-insurance', dialog.$wrapper).click(function () {
				dialog.hide();
				me._make_sales_invoice('After Depreciation Amount');
			});
		} else {
			me._make_sales_invoice();
		}
	},

	_make_sales_invoice: function (depreciation_type) {
		return frappe.call({
			method: "erpnext.projects.doctype.project.project.get_sales_invoice",
			args: {
				"project_name": this.frm.doc.name,
				"depreciation_type": depreciation_type,
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	},

	make_delivery_note: function () {
		var me = this;
		me.frm.check_if_unsaved();
		return frappe.call({
			method: "erpnext.projects.doctype.project.project.get_delivery_note",
			args: {
				"project_name": me.frm.doc.name,
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	},

	make_vehicle_receipt: function () {
		this.frm.check_if_unsaved();
		return frappe.call({
			method: "erpnext.projects.doctype.project.project.get_vehicle_service_receipt",
			args: {
				"project": this.frm.doc.name
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	},

	make_vehicle_gate_pass: function () {
		this.frm.check_if_unsaved();
		return frappe.call({
			method: "erpnext.projects.doctype.project.project.get_vehicle_gate_pass",
			args: {
				"project": this.frm.doc.name
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	},

	make_odometer_log: function () {
		var me = this;
		if (!me.frm.doc.applies_to_vehicle) {
			return;
		}

		var dialog = new frappe.ui.Dialog({
			title: __("Vehicle Odometer Log"),
			fields: [
				{"fieldtype": "Int", "label": __("New Odometer Reading"), "fieldname": "new_odometer", "reqd": 1},
				{"fieldtype": "Int", "label": __("Previous Odometer Reading"), "fieldname": "previous_odometer",
					"default": me.frm.doc.vehicle_last_odometer, "read_only": 1},
				{"fieldtype": "Date", "label": __("Reading Date"), "fieldname": "date", "default": "Today"},
			]
		});

		dialog.set_primary_action(__("Create"), function () {
			var values = dialog.get_values();
			return frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_log.vehicle_log.make_odometer_log",
				args: {
					"vehicle": me.frm.doc.applies_to_vehicle,
					"odometer": cint(values.new_odometer),
					"date": values.date,
					"project": me.frm.doc.name,
				},
				callback: function (r) {
					if (!r.exc) {
						dialog.hide();
						me.frm.reload_doc();
					}
				}
			});
		});

		dialog.show();
	},
});

$.extend(cur_frm.cscript, new erpnext.projects.ProjectController({frm: cur_frm}));
