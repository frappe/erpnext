<template>
	<div>
		<div class="timeline-head">
			<div class="comment-input-wrapper">
				<div class="comment-input-header">
					<span class="text-muted">{{ __('Add your review') }}</span>
					<div class="btn btn-default btn-xs pull-right"
						@click="on_submit_review"
						:disabled="!(user_review.rating && user_review.subject)"
					>
						{{ __('Submit Review') }}
					</div>
				</div>
				<div class="comment-input-container">
					<div class="rating-area text-muted">
						<span>{{ __('Your rating:') }}</span>
						<div
							v-for="i in [1, 2, 3, 4, 5]"
							:key="i"
							:class="['fa fa-fw', user_review.rating < i ? 'fa-star-o' : 'fa-star']"
							:data-index="i"
							@click="set_rating(i)"
						>
						</div>
					</div>
					<div class="comment-input-body margin-top" v-show="user_review.rating">
						<input
							type="text"
							placeholder="Subject"
							class="form-control margin-bottom"
							style="border-color: #ebeff2"
							v-model="user_review.subject"
						>
						<div ref="review-content"></div>
						<div>
							<span class="text-muted text-small">{{ __('Ctrl+Enter to submit') }}</span>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="timeline-items">
			<review-timeline-item v-for="review in reviews"
				:key="review.user"
				:username="review.username"
				:avatar="review.user_image"
				:comment_when="when(review.modified)"
				:rating="review.rating"
				:subject="review.subject"
				:content="review.content"
			>
			</review-timeline-item>
		</div>
	</div>
</template>
<script>
import ReviewTimelineItem from '../components/ReviewTimelineItem.vue';

export default {
	props: ['hub_item_name'],
	data() {
		return {
			user_review: {
				rating: 0,
				subject: '',
				content: ''
			},
			reviews: []
		}
	},
	components: {
		ReviewTimelineItem
	},
	created() {
		this.get_item_reviews();
	},
	mounted() {
		this.make_input();
	},
	methods: {
		set_rating(i) {
			this.user_review.rating = i;
		},

		when(datetime) {
			return comment_when(datetime);
		},

		get_item_reviews() {
			hub.call('get_item_reviews', { hub_item_name: this.hub_item_name })
				.then(reviews => {
					this.reviews = reviews;
				})
				.catch(() => {});
		},

		make_input() {
			this.review_content = frappe.ui.form.make_control({
				parent: this.$refs['review-content'],
				on_submit: this.on_submit_review.bind(this),
				no_wrapper: true,
				only_input: true,
				render_input: true,
				df: {
					fieldtype: 'Comment',
					fieldname: 'comment'
				}
			});
		},

		on_submit_review() {
			const review = Object.assign({}, this.user_review, {
				content: this.review_content.get_value()
			});

			if (!hub.is_seller_registered()) {
				frappe.throw(__('You need to login as a Marketplace User before you can add any reviews.'));
			}

			hub.call('add_item_review', {
				hub_item_name: this.hub_item_name,
				review: JSON.stringify(review)
			})
			.then(this.push_review.bind(this));

			this.reset_user_review();
		},

		reset_user_review() {
			this.user_review.rating = 0;
			this.user_review.subject = '';
			this.review_content.set_value('');
		},

		push_review(review){
			this.reviews.unshift(review);
		}
	}
}
</script>