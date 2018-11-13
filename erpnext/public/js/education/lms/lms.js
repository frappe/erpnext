import Vue from 'vue/dist/vue.js';
import VueRouter from 'vue-router/dist/vue-router.js'

import lmsRoot from "./lmsRoot.vue";
import routes from './routes';
import './call';

Vue.use(VueRouter)

var store = {
	isLogin: false,
	completedCourses: new Set(),
	enrolledPrograms: new Set(),
	enrolledCourses: {}
}

frappe.ready(() => {
	frappe.provide('lms')
	// frappe.utils.make_event_emitter(lms);

	lms.store = new Vue({
		data: store,
		methods: {
			addCompletedCourses (courseName){
				if (lms.debug) console.log('addCompletedCourses triggered with', courseName)
				this.completedCourses.add(courseName)
			},

			checkCourseCompletion (courseName){
				return this.completedCourses.has(courseName)
			},

			checkProgramEnrollment (programName){
				return this.enrolledPrograms.has(programName)
			},

			checkCourseEnrollment (courseName){
				course = new Set(Object.keys(enrolledCourses))
				return course.has(courseName)
			},

			updateEnrolledPrograms (){
				if (lms.debug) console.log('Updating enrolledPrograms')
				lms.call("get_program_enrollments").then(data => {
					data.forEach(element => {
						this.enrolledPrograms.add(element)
					})
				});
				if (lms.debug) console.log('Updated State', this.enrolledPrograms)
			},

			updateEnrolledCourses (){
				if (lms.debug) console.log('Updating enrolledCourses')
				frappe.call({
					method: "erpnext.www.lms.get_course_enrollments",
					args:{
						email: frappe.session.user
					}
				}).then( r => {
					this.enrolledCourses = r.message
				})
				if (lms.debug) console.log('Updated State', this.enrolledCourses)
			},

			updateCompletedCourses (){
				if (lms.debug) console.log('Updating States')
				frappe.call({
					method: "erpnext.www.lms.get_completed_courses",
					args:{
						email: frappe.session.user
					}
				}).then( r => {
					if(r.message){
						for(var ii=0; ii < r.message.length; ii++){
							this.completedCourses.add(r.message[ii])
						}
					}
				})
				if (lms.debug) console.log('Updated State', this.completedCourses)
			},

			checkLogin (){
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

			updateState (){
				this.updateCompletedCourses()
				this.updateEnrolledPrograms()
				this.updateEnrolledCourses()
				this.checkLogin()
			},
		}
	});

	lms.view = new Vue({
		el: "#lms-app",
		router: new VueRouter({ routes }),
		template: "<lms-root/>",
		components: { lmsRoot },
		created: function() {
			if(lms.store.checkLogin()){
				lms.store.updateState()
			}
		}
	});

	lms.debug = true
})