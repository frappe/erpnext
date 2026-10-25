frappe.pages["visual-plant-floor"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Visual Plant Floor",
		single_column: true,
	});

	frappe.visual_plant_floor = new frappe.ui.VisualPlantFloor(
		{ wrapper: $(wrapper).find(".layout-main-section") },
		wrapper.page
	);
};

frappe.pages["visual-plant-floor"].on_page_show = function () {
	frappe.visual_plant_floor.bind_realtime();
	frappe.visual_plant_floor.render_plant_visualization();
};
