frappe.provide("erpnext.vehicles.pricing");

$.extend(erpnext.vehicles.pricing, {
	pricing_component_query: function (component_type) {
		return {
			filters: {
				component_type: component_type
			}
		}
	},

	pricing_component_route_options: function (component_type) {
		return {
			component_type: component_type
		}
	},
});
