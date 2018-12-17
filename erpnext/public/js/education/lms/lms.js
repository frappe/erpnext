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
				if(this.checkLogin()) {
					lms.call("get_program_enrollments").then(data => {
						this.enrolledPrograms = data
					});
					if (lms.debug) console.log('Updated Enrolled Programs', this.enrolledPrograms)
				}
			},
			updateEnrolledCourses() {
				if(this.checkLogin()) {
					lms.call("get_all_course_enrollments").then(data => {
						this.enrolledCourses = data
					})
					if (lms.debug) console.log('Updated Enrolled Courses', this.enrolledCourses)
				}
			},
			checkLogin() {
				return frappe.is_user_logged_in()
			},
			updateState() {
				this.checkLogin()
				this.updateEnrolledPrograms()
				this.updateEnrolledCourses()
			},
			checkProgramEnrollment(programName) {
				if(this.checkLogin()){
					if(this.enrolledPrograms) {
						if(this.enrolledPrograms.includes(programName)) {
							return true
						}
						else {
							return false
						}
					}
					else {
						return false
					}
				}
				else {
					return false
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
			lms.store.updateState()
		}
	});
	lms.view.$router.afterEach((to, from) => {
		window.scrollTo(0,0)
	  })
	lms.debug = true
})