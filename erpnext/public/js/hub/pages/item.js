import SubPage from './subpage';
import { get_detail_view_html } from '../components/detail_view';
// import { get_detail_skeleton_html } from '../components/skeleton_state';
import { get_review_html } from '../components/reviews';

erpnext.hub.Item = class Item extends SubPage {
	refresh() {
		this.show_skeleton();
		this.hub_item_code = frappe.get_route()[2];

		this.own_item = false;

		this.get_item(this.hub_item_code)
			.then(item => {
				this.own_item = item.hub_seller === hub.settings.company_email;
				this.item = item;
				this.render(item);
			});
	}


	show_skeleton() {
		// this.$wrapper.html(get_detail_skeleton_html());
	}


	get_item(hub_item_code) {
		return hub.call('get_item_details', {
			hub_item_code
		});
	}


	render(item) {
		const html = get_detail_view_html(item, this.own_item);
		this.$wrapper.html(html);

		this.make_review_area();

		this.get_reviews()
			.then(reviews => {
				this.reviews = reviews;
				this.render_reviews();
			});
	}


	edit_details() {
		if (!this.edit_dialog) {
			this.edit_dialog = new frappe.ui.Dialog({
				title: "Edit Your Product",
				fields: []
			});
		}
		this.edit_dialog.show();
	}


	unpublish_item() {
		if (!this.unpublish_dialog) {
			this.unpublish_dialog = new frappe.ui.Dialog({
				title: "Edit Your Product",
				fields: []
			});
		}

		this.unpublish_dialog.show();
	}


	add_to_favourites(favourite_button) {
		$(favourite_button).addClass('disabled');

		hub.call('add_item_to_seller_favourites', {
			hub_item_code: this.hub_item_code,
			hub_seller: hub.settings.company_email
		})
			.then(() => {
				$(favourite_button).html('Saved');
				frappe.show_alert(__('Saved to <b><a href="#marketplace/favourites">Favourites</a></b>'));
				erpnext.hub.trigger('action:item_favourite');
			})
			.catch(e => {
				console.error(e);
			});
	}


	contact_seller() {
		const d = new frappe.ui.Dialog({
			title: __('Send a message'),
			fields: [
				{
					fieldname: 'to',
					fieldtype: 'Read Only',
					label: __('To'),
					default: this.item.company
				},
				{
					fieldtype: 'Text',
					fieldname: 'message',
					label: __('Message')
				}
			],
			primary_action: ({ message }) => {
				if (!message) return;

				hub.call('send_message', {
					from_seller: hub.settings.company_email,
					to_seller: this.item.hub_seller,
					hub_item: this.item.hub_item_code,
					message
				})
					.then(() => {
						d.hide();
						frappe.set_route('marketplace', 'buy', this.item.hub_item_code);
						erpnext.hub.trigger('action:send_message')
					});
			}
		});

		d.show();
	}


	make_review_area() {
		if (hub.settings.registered) {
			this.comment_area = new frappe.ui.ReviewArea({
				parent: this.$wrapper.find('.timeline-head').empty(),
				mentions: [],
				on_submit: this.on_submit_review.bind(this)
			});
		} else {
			//TODO: fix UI
			this.comment_area = this.$wrapper
				.find('.timeline-head')
				.empty()
				.append('<div></div>');
		}
	}


	on_submit_review(values) {
		values.user = frappe.session.user;
		values.username = frappe.session.user_fullname;

		hub.call('add_item_review', {
			hub_item_code: this.hub_item_code,
			review: JSON.stringify(values)
		})
		.then(this.push_review_in_review_area.bind(this));
	}


	push_review_in_review_area(review) {
		this.reviews = this.reviews || [];
		this.reviews.push(review);
		this.render_reviews();

		this.comment_area.reset();
	}


	get_reviews() {
		return hub.call('get_item_reviews', { hub_item_code: this.hub_item_code }).catch(() => {});
	}


	render_reviews() {
		const $timeline = this.$wrapper.find('.timeline-items');

		$timeline.empty();

		const reviews = this.reviews || [];

		reviews.sort((a, b) => {
			if (a.modified > b.modified) {
				return -1;
			}

			if (a.modified < b.modified) {
				return 1;
			}

			return 0;
		});

		reviews.forEach(review => {
			$(get_review_html(review)).appendTo($timeline);
		});
	}
}
