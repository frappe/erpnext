// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide('erpnext');

$(document).on('toolbar_setup', () => {
	create_shortcut_popover();
	frappe.realtime.on('update_shortcut_setting', (shortcut_setting) => {
		frappe.boot.shortcut_setting = shortcut_setting;
	});
	frappe.search.utils.make_function_searchable(
		go_to_user_shortcut_setting_page,
		__('Shortcut Setting')
	)
});

function create_shortcut_popover() {
	const home_button = $('.navbar-home');

	home_button.popover({
		html: true,
		animation: true,
		container: 'body',
		trigger: 'manual',
		placement: 'bottom',
		template: `<div class="shortcut-popover popover">
			<div class="popover-content"></div>
		</div>`,
		content: () => {
			const shortcut_setting = frappe.boot.shortcut_setting;

			if (!shortcut_setting || !shortcut_setting.enabled) return

			const shortcut_popover = $(`<div>`);

			shortcut_setting.shortcut_items.map(item => {
				shortcut_popover.append(`
					<a href="#${item.link || ''}" class="shortcut-item">
						${item.label}
					</a>
				`);
			});

			// push configuration option
			shortcut_popover.append('<div class="divider">')
			shortcut_popover.append(get_customize_shortcut_link());

			return shortcut_popover;
		},
	})
	.on("mouseenter", () => {
		setTimeout(() => {
			home_button.popover("show");
			$(".popover").on("mouseleave click", () => {
				home_button.popover('hide');
			});
		}, 500);
	})
	.on("mouseleave", () => {
		setTimeout(() => {
			if (!$(".popover:hover").length) {
				home_button.popover("hide");
			}
		}, 100);
	});
}

function get_customize_shortcut_link() {
	const customize_shortcut_link = $(`<a class="shortcut-item">${__('Customize')}</a>`);
	customize_shortcut_link.click(() => {
		go_to_user_shortcut_setting_page();
	});
	return customize_shortcut_link;
}

function go_to_user_shortcut_setting_page() {
	let shortcut_setting = {...frappe.boot.shortcut_setting};
	if (shortcut_setting && shortcut_setting.user === frappe.session.user) {
		frappe.set_route('Form', shortcut_setting.doctype, shortcut_setting.name)
	} else {
		frappe.model.with_doctype('Shortcut Settings', () => {
			shortcut_setting = frappe.model.copy_doc(shortcut_setting);
			shortcut_setting.user = frappe.session.user;
			frappe.set_route('Form', shortcut_setting.doctype, shortcut_setting.name)
		})
	}
}