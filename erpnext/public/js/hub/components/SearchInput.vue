<template>
  <div class="hub-search-container">
	<input
		type="text"
		class="form-control"
		:placeholder="placeholder"
		:value="value"
		@keydown.enter="on_input">
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
		}
	}
};
</script>
