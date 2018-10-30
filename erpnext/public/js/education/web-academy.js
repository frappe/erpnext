import Vue from 'vue/dist/vue.js';
import VueRouter from 'vue-router/dist/vue-router.js'
import AcademyRoot from "./web-academy/AcademyRoot.vue";
import AcademyHome from "./web-academy/pages/AcademyHome.vue";
import AcademyProgramPage from "./web-academy/pages/AcademyProgramPage.vue";
import AcademyCoursePage from "./web-academy/pages/AcademyCoursePage.vue";

Vue.use(VueRouter)

const routes = [
	{path: '', component: AcademyHome},
	{path: '/Program/:code', component: AcademyProgramPage, props: true},
	{path: '/Course', component: AcademyCoursePage},
];

const router = new VueRouter({
	routes: routes,
});

frappe.ready(() => {
	new Vue({
		el: "#web-academy",
		router: router,
		template: "<academy-root/>",
		components: { AcademyRoot }
	});
})