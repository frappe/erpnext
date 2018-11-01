<template>
	<div class="nav-buttons">
		<button class='btn btn-outline-secondary' @click="$router.go(-1)">Previous</button>
		<button class='btn btn-primary' @click="$router.push({ name: 'content', params: { course: $route.params.course, type:nextContentType, content:nextContent }})">Next</button>
	</div>
</template>

<script>
export default {
	props: ['nextContent', 'nextContentType'],
	name: 'ContentNavigation',
};
</script>

<style lang="css" scoped>
	.nav-buttons {
		position: absolute;
  		bottom: 0;
  		right: 0;
	}
</style>
