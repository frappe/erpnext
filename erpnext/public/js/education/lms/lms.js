import Vue from 'vue/dist/vue.js';
import VueRouter from 'vue-router/dist/vue-router.js'
import moment from 'moment/min/moment.min.js'

import lmsRoot from "./lmsRoot.vue";
import routes from './routes';
import './call';

Vue.use(VueRouter)

var store = {
	isLogin: false,
	enrolledPrograms: [],
	enrolledCourses: {}
}

frappe.ready(() => {
	frappe.provide('lms')
	// frappe.utils.make_event_emitter(lms);

	lms.moment = moment

	lms.store = new Vue({
		data: store,
		methods: {
			updateEnrolledPrograms() {
				if(this.isLogin) {
					lms.call("get_program_enrollments").then(data => {
						this.enrolledPrograms = data
					});
					if (lms.debug) console.log('Updated Enrolled Programs', this.enrolledPrograms)
				}
			},

			updateEnrolledCourses() {
				if(this.isLogin) {
					lms.call("get_all_course_enrollments").then(data => {
						this.enrolledCourses = data
					})
					if (lms.debug) console.log('Updated Enrolled Courses', this.enrolledCourses)
				}
			},

			checkLogin() {
				if(frappe.session.user === "Guest"){
					if (lms.debug) console.log('No Session')
					this.isLogin = false
				}
				else {
					if (lms.debug) console.log('Current User: ', frappe.session.user)
					this.isLogin = true
				}
				return this.isLogin
			},

			updateState() {
				this.checkLogin()
				this.updateEnrolledPrograms()
				this.updateEnrolledCourses()
			},
		}
	});

	lms.view = new Vue({
		el: "#lms-app",
		router: new VueRouter({ routes }),
		template: "<lms-root/>",
		components: { lmsRoot },
		mounted() {
			if(lms.store.isLogin) lms.store.updateState()
		}
	});
	lms.debug = true
})