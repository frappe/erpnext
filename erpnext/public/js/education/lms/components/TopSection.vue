<template>
<div class="hero">
	<h1 class="text-center" v-html="title"></h1>
	<p class='text-center' v-html="description"></p>
	<p class="text-center padding">
		<slot></slot>
	</p>
</div>
</template>
<script>

export default {
	props: ['title', 'description'],
    name: "TopSection",
};
</script>
<style scoped>
	.hero {
		padding-top: 50px;
		padding-bottom: 100px;
	}

	.hero h1 {
		font-size: 40px;
		font-weight: 200;
	}
</style>
