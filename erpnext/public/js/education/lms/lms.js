import Vue from 'vue/dist/vue.js';
import VueRouter from 'vue-router/dist/vue-router.js';
import moment from 'moment/min/moment.min.js';

import lmsRoot from "./lmsRoot.vue";
import routes from './routes';
import './call';

Vue.use(VueRouter);

var store = {
	enrolledPrograms: [],
	enrolledCourses: []
};

// let profile_page = `<a class="dropdown-item" href="/lms#/Profile" rel="nofollow"> LMS Profile </a>`
// document.querySelector('#website-post-login > ul').innerHTML += profile_page

frappe.ready(() => {
	frappe.provide('lms');

	lms.moment = moment;

	lms.store = new Vue({
		data: store,
		methods: {
			updateEnrolledPrograms() {
				if(this.checkLogin()) {
					lms.call("get_program_enrollments").then(data => {
						this.enrolledPrograms = data;
					});
				}
			},
			updateEnrolledCourses() {
				if(this.checkLogin()) {
					lms.call("get_all_course_enrollments").then(data => {
						this.enrolledCourses = data;
					});
				}
			},
			checkLogin() {
				return frappe.is_user_logged_in();
			},
			updateState() {
				this.checkLogin();
				this.updateEnrolledPrograms();
				this.updateEnrolledCourses();
			},
			checkProgramEnrollment(programName) {
				if(this.checkLogin()){
					if(this.enrolledPrograms) {
						if(this.enrolledPrograms.includes(programName)) {
							return true;
						}
						else {
							return false;
						}
					}
					else {
						return false;
					}
				}
				else {
					return false;
				}
			}
		}
	});
	lms.view = new Vue({
		el: "#lms-app",
		router: new VueRouter({ routes }),
		template: "<lms-root/>",
		components: { lmsRoot },
		mounted() {
			lms.store.updateState();
		}
	});
	lms.view.$router.afterEach((to, from) => {
		window.scrollTo(0,0);
	});
});