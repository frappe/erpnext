// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide('erpnext.projects');

erpnext.projects.ProjectController = frappe.ui.form.Controller.extend({
	setup: function() {
		this.setup_make_methods();
		this.setup_indicator();
	},

	onload: function () {
		this.setup_queries();
	},

	refresh: function () {
		this.setup_route_options();
		this.setup_naming_series();
		erpnext.hide_company();
		this.setup_web_link();
		this.setup_buttons();
		this.set_applies_to_read_only();
		this.toggle_vehicle_odometer_fields();
	},

	setup_queries: function () {
		var me = this;

		me.frm.set_query('customer', 'erpnext.controllers.queries.customer_query');
		me.frm.set_query('bill_to', 'erpnext.controllers.queries.customer_query');
		if (me.frm.fields_dict.vehicle_owner) {
			me.frm.set_query('vehicle_owner', 'erpnext.controllers.queries.customer_query');
		}

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
						project: me.frm.doc.project_name
					}).then(() => {
						frappe.set_route('List', 'Task', 'Kanban', me.frm.doc.project_name);
					});
				}, __("Tasks"));
			}

			me.frm.add_custom_button(__('Duplicate Project with Tasks'), () => me.create_duplicate(), __("Tasks"));

			if (frappe.model.can_write("Sales Invoice")) {
				me.frm.add_custom_button(__("Sales Invoice"), function () {
					me.make_sales_invoice()
				}, __("Create"));
			}
		}
	},

	toggle_vehicle_odometer_fields: function () {
		if (this.frm.fields_dict.vehicle_first_odometer && this.frm.fields_dict.vehicle_last_odometer) {
			var first_odometer_read_only = cint(this.frm.doc.vehicle_first_odometer);
			var last_odometer_read_only = !cint(this.frm.doc.vehicle_first_odometer)
				|| cint(this.frm.doc.vehicle_last_odometer) !== cint(this.frm.doc.vehicle_first_odometer);

			this.frm.set_df_property("vehicle_first_odometer", "read_only", first_odometer_read_only);
			this.frm.set_df_property("vehicle_last_odometer", "read_only", last_odometer_read_only);
		}
	},

	set_applies_to_read_only: function() {
		var me = this;
		var read_only_fields = [
			'applies_to_item', 'applies_to_item_name',
			'vehicle_license_plate', 'vehicle_unregistered',
			'vehicle_chassis_no', 'vehicle_engine_no',
			'vehicle_color'
		];
		$.each(read_only_fields, function (i, f) {
			if (me.frm.fields_dict[f]) {
				me.frm.set_df_property(f, "read_only", me.frm.doc.applies_to_vehicle ? 1 : 0);
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

	collect_progress: function() {
		this.frm.set_df_property("message", "reqd", this.frm.doc.collect_progress);
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
		return frappe.call({
			method: "erpnext.projects.doctype.project.project.get_sales_invoice",
			args: {
				"project_name": this.frm.doc.name,
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.projects.ProjectController({frm: cur_frm}));
