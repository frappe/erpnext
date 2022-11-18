frappe.listview_settings['Vehicle Registration Order'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		var indicator;

		if(doc.status === "Completed") {
			indicator = [__("Completed"), "green", "status,=,Completed"];
		} else if (["To Receive Invoice"].includes(doc.status)) {
			indicator = [__(doc.status), "grey", `status,=,${doc.status}`];
		} else if (["To Retrieve Invoice", "To Pay Agent"].includes(doc.status)) {
			indicator = [__(doc.status), "light-blue", `status,=,${doc.status}`];
		} else if (["To Receive Payment", "To Receive Receipt"].includes(doc.status)) {
			indicator = [__(doc.status), "yellow", `status,=,${doc.status}`];
		} else if(["To Close Accounts", "To Bill"].includes(doc.status)) {
			indicator = [__(doc.status), "purple", `status,=,${doc.status}`];
		} else if(["To Issue Invoice", "To Deliver Invoice", "To Pay Authority"].includes(doc.status)) {
			indicator = [__(doc.status), "orange", `status,=,${doc.status}`];
		}

		return indicator;
	},
	onload: function(listview) {
		listview.page.fields_dict.customer.get_query = () => {
			return erpnext.queries.customer();
		}
		listview.page.fields_dict.registration_customer.get_query = () => {
			return erpnext.queries.customer();
		}

		listview.page.fields_dict.variant_of.get_query = () => {
			return erpnext.queries.item({"is_vehicle": 1, "has_variants": 1, "include_disabled": 1, "include_in_vehicle_booking": 1});
		}

		listview.page.fields_dict.item_code.get_query = () => {
			var variant_of = listview.page.fields_dict.variant_of.get_value('variant_of');
			var filters = {"is_vehicle": 1, "include_disabled": 1, "include_in_vehicle_booking": 1};
			if (variant_of) {
				filters['variant_of'] = variant_of;
			}
			return erpnext.queries.item(filters);
		}

		listview.page.add_action_item(__("Create Agent Payment"), function () {
			var names = listview.get_checked_items(true);

			if (names && names.length) {
				return frappe.call({
					method: "erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order.get_agent_payment_voucher",
					args: {
						"names": names
					},
					callback: function (r) {
						var doclist = frappe.model.sync(r.message);
						frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
					}
				});
			}
		});

		var get_vehicle_registration_details = function (df, dialog) {
			if (df.doc.vehicle_registration_order) {
				frappe.call({
					method: 'erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order.get_vehicle_registration_order_details',
					args: {
						vehicle_registration_order: df.doc.vehicle_registration_order,
						get_customer: 1,
						get_vehicle: 1,
						get_vehicle_booking_order: 1
					},
					callback: (r) => {
						if (r.message) {
							$.each(r.message || {}, function (k, v) {
								df.doc[k] = v;
							});
							dialog.fields_dict.orders.grid.refresh();
						}
					}
				});
			}
		};

		listview.page.add_menu_item(__("Select Orders for Agent Payment"), function () {
			var data = [];

			var table_fields = [
				{
					label: __("Registration Order"),
					fieldname: "vehicle_registration_order",
					fieldtype: "Link",
					options: "Vehicle Registration Order",
					reqd: 1,
					in_list_view: 1,
					columns: 2,
					get_query: () => {
						return {
							filters: {
								agent: dialog.get_value('agent') || undefined,
								docstatus: 1,
							}
						}
					},
					change: function () {
						get_vehicle_registration_details(this, dialog);
					}
				},
				{
					label: __("Booking Order"),
					fieldname: "vehicle_booking_order",
					fieldtype: "Link",
					options: "Vehicle Booking Order",
					read_only: 1,
					in_list_view: 1,
					columns: 2,
				},
				{
					label: __("Registration Customer"),
					fieldname: "registration_customer_name",
					fieldtype: "Data",
					read_only: 1,
					in_list_view: 1,
					columns: 3,
				},
				{
					label: __("Variant Item Code"),
					fieldname: "item_code",
					fieldtype: "Link",
					options: "Item",
					read_only: 1,
					in_list_view: 1,
					columns: 2,
				},
				{
					label: __("Variant Item Name"),
					fieldname: "item_name",
					fieldtype: "Link",
					options: "Item",
					read_only: 1,
				},
				{
					label: __("Reg #"),
					fieldname: "vehicle_license_plate",
					fieldtype: "Data",
					read_only: 1,
					in_list_view: 1,
					columns: 1,
				},
				{
					label: __("Chassis #"),
					fieldname: "vehicle_chassis_no",
					fieldtype: "Data",
					read_only: 1,
				},
				{
					label: __("Engine #"),
					fieldname: "vehicle_engine_no",
					fieldtype: "Data",
					read_only: 1,
				},
			];

			var fields = [
				{
					label: __('Agent'),
					fieldname: 'agent',
					fieldtype: 'Link',
					options: 'Supplier',
					reqd: 1,
					change: function () {
						if (dialog.get_value('agent')) {
							frappe.db.get_value("Supplier", dialog.get_value('agent'), 'supplier_name', function (r) {
								dialog.set_value('agent_name', r.supplier_name);
							});
						}
					},
				},
				{
					label: __('Agent Name'),
					fieldname: 'agent_name',
					fieldtype:'Data',
					read_only: 1,
					fetch_from: "agent.supplier_name",
					depends_on: "eval:doc.agent && doc.agent_name != doc.agent"
				},
				{
					fieldtype: 'Section Break'
				},
				{
					label: __('Orders'),
					fieldname: 'orders',
					fieldtype: 'Table',
					reqd: 1,
					in_place_edit: true,
					data: data,
					get_data: () => {
						return data;
					},
					fields: table_fields
				}
			]

			var dialog = new frappe.ui.Dialog({
				title: __('Agent Payment Order Selection'),
				size: "large",
				fields: fields
			});

			dialog.set_primary_action(__('Create'), function() {
				const dialog_data = dialog.get_values();
				var orders = dialog_data.orders.map(d => d.vehicle_registration_order).filter(d => d);
				if (orders && orders.length) {
					return frappe.call({
						method: "erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order.get_agent_payment_voucher",
						args: {
							"names": orders
						},
						callback: function (r) {
							dialog.hide();
							var doclist = frappe.model.sync(r.message);
							frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
						}
					});
				}
			});

			dialog.show();
		});
	}
};
