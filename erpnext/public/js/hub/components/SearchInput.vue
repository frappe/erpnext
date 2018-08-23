<template>
  <div class="hub-search-container">
	<input
		type="text"
		class="form-control"
		:placeholder="placeholder"
		:value="value"
		@input="on_input">
  </div>
</template>

<script>
export default {
	props: {
		placeholder: String,
		value: String,
		on_search: Function
	},
	methods: {
		on_input(event) {
			this.$emit('input', event.target.value);
			this.on_search();

			// TODO: Debouncing doesn't fire search
			// frappe.utils.debounce(this.on_search, 500);
		}
	}
};
</script>

<style lang="scss" scoped>
</style>
