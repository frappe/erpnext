// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide('erpnext');

$(document).on('toolbar_setup', () => {
	const home_button = $('.navbar-home');

	home_button.popover({
		animation: true,
		placement: 'bottom',
		trigger: 'manual',
		delay: { "show": 500, "hide": 100 },
		content: () => {
			const content = $('<div class="app-icon-container">');
			const icons_to_show = ['Desktop', 'Marketplace', 'Social', 'Explore'];
			icons_to_show.forEach(icon => {
				let _module = frappe.modules[icon];
				if (_module) {
					content.append(frappe.ui.app_icon.get_html(_module, true));
				}
			});


			return content.prop('outerHTML');
		},
		html: true,
		container: 'body'
	}).on("mouseenter",  () => {
		setTimeout(() => {
			home_button.popover("show");
		}, 500);
		$(".popover").on("mouseleave",  () => {
			home_button.popover('hide');
		});
	}).on("mouseleave",  () => {
		setTimeout(() => {
			if (!$(".popover:hover").length) {
				home_button.popover("hide");
			}
		}, 100);
	});
});
