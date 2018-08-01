import SubPage from './subpage';
import { get_rating_html } from '../helpers';

erpnext.hub.Item = class Item extends SubPage {
	make_wrapper() {
		super.make_wrapper();
		this.setup_events();
	}

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
		const skeleton = `<div class="hub-item-container">
			<div class="row">
				<div class="col-md-3">
					<div class="hub-item-skeleton-image"></div>
				</div>
				<div class="col-md-6">
					<h2 class="hub-skeleton" style="width: 75%;">Name</h2>
					<div class="text-muted">
						<p class="hub-skeleton" style="width: 35%;">Details</p>
						<p class="hub-skeleton" style="width: 50%;">Ratings</p>
					</div>
					<hr>
					<div class="hub-item-description">
						<p class="hub-skeleton">Desc</p>
						<p class="hub-skeleton" style="width: 85%;">Desc</p>
					</div>
				</div>
			</div>
		</div>`;

		this.$wrapper.html(skeleton);
	}

	setup_events() {
		this.$wrapper.on('click', '.btn-contact-seller', () => {
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
				]
			});

			d.show();
		});
	}

	get_item(hub_item_code) {
		return hub.call('get_item_details', { hub_item_code });
	}

	render(item) {
		const title = item.item_name || item.name;
		const seller = item.company;

		const who = __('Posted By {0}', [seller]);
		const when = comment_when(item.creation);

		const city = item.city ? item.city + ', ' : '';
		const country = item.country ? item.country : '';
		const where = `${city}${country}`;

		const dot_spacer = '<span aria-hidden="true"> · </span>';

		const description = item.description || '';

		const rating_html = get_rating_html(item.average_rating);
		const rating_count = item.no_of_ratings > 0 ? `${item.no_of_ratings} reviews` : __('No reviews yet');

		let menu_items = '';

		if(this.own_item) {
			menu_items = `
				<li><a data-action="edit_details">${__('Edit Details')}</a></li>
				<li><a data-action="unpublish_item">${__('Unpublish')}</a></li>`;
		} else {
			menu_items = `
				<li><a data-action="report_item">${__('Report this item')}</a></li>
			`;
		}

		const html = `
			<div class="hub-item-container">
				<div class="row visible-xs">
					<div class="col-xs-12 margin-bottom">
						<button class="btn btn-xs btn-default" data-route="marketplace/home">${__('Back to home')}</button>
					</div>
				</div>
				<div class="row">
					<div class="col-md-3">
						<div class="hub-item-image">
							<img src="${item.image}">
						</div>
					</div>
					<div class="col-md-8">
						<h2>${title}</h2>
						<div class="text-muted">
							<p>${where}${dot_spacer}${when}</p>
							<p>${rating_html} (${rating_count})</p>
						</div>
						<hr>
						<div class="hub-item-description">
						${description ?
							`<b>${__('Description')}</b>
							<p>${description}</p>
							` : `<p>${__('No description')}<p>`
						}
						</div>
					</div>
					<div class="col-md-1">
						<div class="dropdown pull-right hub-item-dropdown">
							<a class="dropdown-toggle btn btn-xs btn-default" data-toggle="dropdown">
								<span class="caret"></span>
							</a>
							<ul class="dropdown-menu dropdown-right" role="menu">
								${menu_items}
							</ul>
						</div>
					</div>
				</div>
				<div class="row hub-item-seller">
					<div class="col-md-12 margin-top margin-bottom">
						<b class="text-muted">Seller Information</b>
					</div>
					<div class="col-md-1">
						<img src="https://picsum.photos/200">
					</div>
					<div class="col-md-8">
						<div class="margin-bottom"><a href="#marketplace/seller/${seller}" class="bold">${seller}</a></div>
						<button class="btn btn-xs btn-default text-muted btn-contact-seller">
							${__('Contact Seller')}
						</button>
					</div>
				</div>
				<!-- review area -->
				<div class="row hub-item-review-container">
					<div class="col-md-12 form-footer">
						<div class="form-comments">
							<div class="timeline">
								<div class="timeline-head"></div>
								<div class="timeline-items"></div>
							</div>
						</div>
						<div class="pull-right scroll-to-top">
							<a onclick="frappe.utils.scroll_to(0)"><i class="fa fa-chevron-up text-muted"></i></a>
						</div>
					</div>
				</div>
			</div>
		`;

		this.$wrapper.html(html);

		this.make_review_area();

		this.get_reviews()
			.then(reviews => {
				this.reviews = reviews;
				this.render_reviews(reviews);
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
		if(!this.unpublish_dialog) {
			this.unpublish_dialog = new frappe.ui.Dialog({
				title: "Edit Your Product",
				fields: []
			});
		}

		this.unpublish_dialog.show();
	}

	make_review_area() {
		this.comment_area = new frappe.ui.ReviewArea({
			parent: this.$wrapper.find('.timeline-head').empty(),
			mentions: [],
			on_submit: (values) => {
				values.user = frappe.session.user;
				values.username = frappe.session.user_fullname;

				hub.call('add_item_review', {
					hub_item_code: this.hub_item_code,
					review: JSON.stringify(values)
				})
				.then(review => {
					this.reviews = this.reviews || [];
					this.reviews.push(review);
					this.render_reviews(this.reviews);

					this.comment_area.reset();
				});
			}
		});
	}

	get_reviews() {
		return hub.call('get_item_reviews', { hub_item_code: this.hub_item_code }).catch(() => {});
	}

	render_reviews(reviews=[]) {
		this.$wrapper.find('.timeline-items').empty();

		reviews.sort((a, b) => {
			if (a.modified > b.modified) {
				return -1;
			}

			if (a.modified < b.modified) {
				return 1;
			}

			return 0;
		});

		reviews.forEach(review => this.render_review(review));
	}

	render_review(review) {
		let username = review.username || review.user || __("Anonymous");

		let image_html = review.user_image
			? `<div class="avatar-frame" style="background-image: url(${review.user_image})"></div>`
			: `<div class="standard-image" style="background-color: #fafbfc">${frappe.get_abbr(username)}</div>`

		let edit_html = review.own
			? `<div class="pull-right hidden-xs close-btn-container">
				<span class="small text-muted">
					${'data.delete'}
				</span>
			</div>
			<div class="pull-right edit-btn-container">
				<span class="small text-muted">
					${'data.edit'}
				</span>
			</div>`
			: '';

		let rating_html = get_rating_html(review.rating);

		const $timeline_items = this.$wrapper.find('.timeline-items');

		$(this.get_timeline_item(review, image_html, edit_html, rating_html))
			.appendTo($timeline_items);
	}

	get_timeline_item(data, image_html, edit_html, rating_html) {
		return `<div class="media timeline-item user-content" data-doctype="${''}" data-name="${''}">
			<span class="pull-left avatar avatar-medium hidden-xs" style="margin-top: 1px">
				${image_html}
			</span>
			<div class="pull-left media-body">
				<div class="media-content-wrapper">
					<div class="action-btns">${edit_html}</div>

					<div class="comment-header clearfix">
						<span class="pull-left avatar avatar-small visible-xs">
							${image_html}
						</span>

						<div class="asset-details">
							<span class="author-wrap">
								<i class="octicon octicon-quote hidden-xs fa-fw"></i>
								<span>${data.username}</span>
							</span>
							<a class="text-muted">
								<span class="text-muted hidden-xs">&ndash;</span>
								<span class="hidden-xs">${comment_when(data.modified)}</span>
							</a>
						</div>
					</div>
					<div class="reply timeline-content-show">
						<div class="timeline-item-content">
							<p class="text-muted">
								${rating_html}
							</p>
							<h6 class="bold">${data.subject}</h6>
							<p class="text-muted">
								${data.content}
							</p>
						</div>
					</div>
				</div>
			</div>
		</div>`;
	}
}