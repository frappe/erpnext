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
<style>
	div.card-hero-img {
        height: 220px;
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        background-color: rgb(250, 251, 252);
    }

    .card-image-wrapper {
        display: flex;
        overflow: hidden;
        height: 220px;
        background-color: rgb(250, 251, 252);
        justify-content: center;
    }

    .image-body {
        align-self: center;
        color: #d1d8dd;
        font-size: 24px;
        font-weight: 600;
        line-height: 1;
        padding: 20px;
    }
</style>
