<template>
	<div>
		<div ref="comment-input"></div>
		<div class="level">
			<div class="level-left">
				<span class="text-muted">{{ __('Ctrl + Enter to submit') }}</span>
			</div>
			<div class="level-right">
				<button class="btn btn-primary btn-xs" @click="submit_input">{{ __('Submit') }}</button>
			</div>
		</div>
	</div>
</template>
<script>
export default {
	mounted() {
		this.make_input();
	},
	methods: {
		make_input() {
			this.message_input = frappe.ui.form.make_control({
				parent: this.$refs['comment-input'],
				on_submit: (message) => {
					this.message_input.reset();
					this.$emit('change', message);
				},
				only_input: true,
				no_wrapper: true
			});
		},
		submit_input() {
			if (!this.message_input) return;
			const value = this.message_input.get_value();
			if (!value) return;
			this.message_input.submit();
		}
	}
}
</script>
