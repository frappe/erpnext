import Vue from 'vue/dist/vue.js';
import VueRouter from 'vue-router/dist/vue-router.js'

import AcademyRoot from "./AcademyRoot.vue";
import routes from './routes';
import './call';

Vue.use(VueRouter)




frappe.provide('academy')

frappe.utils.make_event_emitter(academy);

academy.store = {
	debug: true,
	isLogin: false,
	completedCourses: new Set(),
	enrolledPrograms: new Set(),
	enrolledCourses: {},

	addCompletedCourses (courseName){
		if (this.debug) console.log('addCompletedCourses triggered with', courseName)
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
		if (this.debug) console.log('Updating enrolledPrograms')
		frappe.call({
			method: "erpnext.www.academy.get_program_enrollments",
			args:{
				email: frappe.session.user
			}
		}).then( r => {
			if(r.message){
				for(var ii=0; ii < r.message.length; ii++){
					this.enrolledPrograms.add(r.message[ii])
				}
			}
		})
		if (this.debug) console.log('Updated State', this.enrolledPrograms)
	},

	updateEnrolledCourses (){
		if (this.debug) console.log('Updating enrolledCourses')
		frappe.call({
			method: "erpnext.www.academy.get_course_enrollments",
			args:{
				email: frappe.session.user
			}
		}).then( r => {
			this.enrolledCourses = r.message
		})
		if (this.debug) console.log('Updated State', this.enrolledCourses)
	},

	updateCompletedCourses (){
		if (this.debug) console.log('Updating States')
		frappe.call({
			method: "erpnext.www.academy.get_completed_courses",
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
		if (this.debug) console.log('Updated State', this.completedCourses)
	},

	checkLogin (){
		if(frappe.session.user === "Guest"){
			if (this.debug) console.log('No Session')
			this.isLogin = false
		}
		else {
			if (this.debug) console.log('Current User: ', frappe.session.user)
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

frappe.ready(() => {
	window.v = new Vue({
		el: "#academy",
		router: new VueRouter({ routes }),
		template: "<academy-root/>",
		components: { AcademyRoot },
		created: function() {
			if(store.checkLogin()){
				store.updateState()
			}
		}
	});
	academy.store = new Vue({
		data: store,
		methods: {
			checkLogin (){
				if(frappe.session.user === "Guest"){
					if (this.debug) console.log('No Session')
					this.isLogin = false
				}
				else {
					if (this.debug) console.log('Current User: ', frappe.session.user)
					this.isLogin = true
				}
				return this.isLogin
			}
		}
	});
})