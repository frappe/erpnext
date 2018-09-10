<template>
	<div>
		<div ref="review-area" class="timeline-head"></div>
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
			this.review_area = new frappe.ui.ReviewArea({
				parent: this.$refs['review-area'],
				mentions: [],
				on_submit: this.on_submit_review.bind(this)
			});
		},

		on_submit_review(values) {
			this.review_area.reset();

			hub.call('add_item_review', {
				hub_item_name: this.hub_item_name,
				review: JSON.stringify(values)
			})
			.then(this.push_review.bind(this));
		},

		push_review(review){
			this.reviews.unshift(review);
		}
	}
}
</script>
