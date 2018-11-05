import Vue from 'vue/dist/vue.js';
import VueRouter from 'vue-router/dist/vue-router.js'

import AcademyRoot from "./web-academy/AcademyRoot.vue";
import AcademyHome from "./web-academy/pages/AcademyHome.vue";
import AcademyProgramPage from "./web-academy/pages/AcademyProgramPage.vue";
import AcademyCoursePage from "./web-academy/pages/AcademyCoursePage.vue";

Vue.use(VueRouter)


const routes = [
	{name: 'home', path: '', component: AcademyHome},
	{name: 'program', path: '/Program/:code', component: AcademyProgramPage, props: true},
	{name: 'content', path: '/Program/:code/:course/:type/:content', component: AcademyCoursePage, props: true},
];

var store = {
	debug: false,
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
			for(var ii=0; ii < r.message.length; ii++){
				this.enrolledPrograms.add(r.message[ii])
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
			for(var ii=0; ii < r.message.length; ii++){
				this.completedCourses.add(r.message[ii])
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

const router = new VueRouter({
	routes: routes,
});

frappe.ready(() => {
	window.v = new Vue({
		el: "#academy",
		router: router,
		data: store,
		template: "<academy-root/>",
		components: { AcademyRoot },
		created: function() {
			if(store.checkLogin()){
				store.updateState()
			}
		}
	});
})