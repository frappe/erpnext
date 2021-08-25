$(() => {
	class CustomerReviews {
		constructor() {
			this.bind_button_actions();
			this.start = 0;
			this.page_length = 10;
		}

		bind_button_actions() {
			this.write_review();
			this.view_more();
		}

		write_review() {
			//TODO: make dialog popup on stray page
			$('.page_content').on('click', '.btn-write-review', (e) => {
				// Bind action on write a review button
				const $btn = $(e.currentTarget);

				let d = new frappe.ui.Dialog({
					title: __("Write a Review"),
					fields: [
						{fieldname: "title", fieldtype: "Data", label: "Headline", reqd: 1},
						{fieldname: "rating", fieldtype: "Rating", label: "Overall Rating", reqd: 1},
						{fieldtype: "Section Break"},
						{fieldname: "comment", fieldtype: "Small Text", label: "Your Review"}
					],
					primary_action: function() {
						let data = d.get_values();
						frappe.call({
							method: "erpnext.e_commerce.doctype.item_review.item_review.add_item_review",
							args: {
								web_item: $btn.attr('data-web-item'),
								title: data.title,
								rating: data.rating,
								comment: data.comment
							},
							freeze: true,
							freeze_message: __("Submitting Review ..."),
							callback: (r) => {
								if (!r.exc) {
									frappe.msgprint({
										message: __("Thank you for submitting your review"),
										title: __("Review Submitted"),
										indicator: "green"
									});
									d.hide();
									location.reload();
								}
							}
						});
					},
					primary_action_label: __('Submit')
				});
				d.show();
			});
		}

		view_more() {
			$('.page_content').on('click', '.btn-view-more', (e) => {
				// Bind action on view more button
				const $btn = $(e.currentTarget);
				$btn.prop('disabled', true);

				this.start += this.page_length;
				let me = this;

				frappe.call({
					method: "erpnext.e_commerce.doctype.item_review.item_review.get_item_reviews",
					args: {
						web_item: $btn.attr('data-web-item'),
						start: me.start,
						end: me.page_length
					},
					callback: (result) => {
						if (result.message) {
							let res = result.message;
							me.get_user_review_html(res.reviews);

							$btn.prop('disabled', false);
							if (res.total_reviews <= (me.start + me.page_length)) {
								$btn.hide();
							}

						}
					}
				});
			});

		}

		get_user_review_html(reviews) {
			let me = this;
			let $content = $('.user-reviews');

			reviews.forEach((review) => {
				$content.append(`
					<div class="mb-3 review">
						<div class="d-flex">
							<p class="mr-4 user-review-title">
								<span>${__(review.review_title)}</span>
							</p>
							<div class="rating">
								${me.get_review_stars(review.rating)}
							</div>
						</div>

						<div class="product-description mb-4">
							<p>
								${__(review.comment)}
							</p>
						</div>
						<div class="review-signature mb-2">
							<span class="reviewer">${__(review.customer)}</span>
							<span class="indicator grey" style="--text-on-gray: var(--gray-300);"></span>
							<span class="reviewer">${__(review.published_on)}</span>
						</div>
					</div>
				`);
			});
		}

		get_review_stars(rating) {
			let stars = ``;
			for (let i = 1; i < 6; i++) {
				let fill_class = i <= rating ? 'star-click' : '';
				stars += `
					<svg class="icon icon-sm ${fill_class}">
						<use href="#icon-star"></use>
					</svg>
				`;
			}
			return stars;
		}
	}

	new CustomerReviews();
});