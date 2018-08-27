<template>
	<div>
		<div ref="review-area"></div>
	</div>
</template>
<script>
export default {
	props: ['hub_item_code'],
	mounted() {
		this.make_input();
	},
	methods: {
		make_input() {
			this.comment_area = new frappe.ui.ReviewArea({
				parent: this.$refs['review-area'],
				mentions: [],
				on_submit: this.on_submit_review.bind(this)
			});

			this.message_input = new frappe.ui.CommentArea({
				parent: this.$refs['review-area'],
				on_submit: (message) => {
					this.message_input.reset();
					this.$emit('change', message);
				},
				no_wrapper: true
			});
		},

		on_submit_review(values) {
			values.user = frappe.session.user;
			values.username = frappe.session.user_fullname;

			hub.call('add_item_review', {
				hub_item_code: this.hub_item_code,
				review: JSON.stringify(values)
			})
			// .then(this.push_review_in_review_area.bind(this));
		}
	}
}
</script>
