<template>
	<div id="lms-root">
		<navbar></navbar>
		<main class="container my-5">
			<div class="page_content">
				<router-view :key="$route.fullPath"></router-view>
			</div>
		</main>
	</div>
</template>
<script>
import Navbar from "./components/Navbar.vue"
export default {
	name: "lmsRoot",
	components: {
		Navbar
	}
};
</script>
