import SubPage from './subpage';
import { get_profile_html } from '../components/detail_view';
import { get_item_card_container_html } from '../components/items_container';
import { get_detail_skeleton_html } from '../components/skeleton_state';

erpnext.hub.Seller = class Seller extends SubPage {
	make_wrapper() {
		super.make_wrapper();
	}

	refresh() {
		this.show_skeleton();
		this.company = frappe.get_route()[2];
		this.get_hub_seller_profile()
			.then(this.render.bind(this));
	}

	get_hub_seller_profile() {
		return hub.call('get_hub_seller_page_info', { company: this.company });
	}

	show_skeleton() {
		this.$wrapper.html(get_detail_skeleton_html());
	}

	render(data) {
		this.$wrapper.html(get_profile_html(data.profile));

		let html = get_item_card_container_html(data.items, __('Products by ' + p.company));
		this.$wrapper.append(html);
	}
}
