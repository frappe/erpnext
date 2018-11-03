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
	debug: true,
	state: {
		completedCourses: new Set(),
		enrolledPrograms: new Set(),
		enrolledCourses: new Set(),
		currentEnrollment: '',
		student: '',
		isLogin: false
	},

	setCurrentEnrollment (enrollment) {
	    if (this.debug) console.log('setCourseEnrollment triggered with', enrollment)
	    this.state.currentEnrollment = enrollment
	},

	getCurrentEnrollment () {
	    if (this.debug) console.log('getCourseEnrollment triggered')
	    return this.state.currentEnrollment
	},

	addCompletedCourses (courseName){
		if (this.debug) console.log('addCompletedCourses triggered with', courseName)
		this.state.completedCourses.add(courseName)
	},

	checkCourseCompletion (courseName){
		return this.state.completedCourses.has(courseName)
	},

	checkProgramEnrollment (programName){
		return this.state.enrolledPrograms.has(programName)
	},

	updateEnrolledPrograms (){
		if (this.debug) console.log('Updating enrolledPrograms')
		frappe.call("erpnext.www.academy.get_program_enrollments").then( r => {
			for(var ii=0; ii < r.message.length; ii++){
				this.state.enrolledPrograms.add(r.message[ii])
			}
		})
		if (this.debug) console.log('Updated State', this.state.enrolledPrograms)
	},

	updateEnrolledCourses (){
		if (this.debug) console.log('Updating enrolledCourses')
		frappe.call("erpnext.www.academy.get_course_enrollments").then( r => {
			for(var ii=0; ii < r.message.length; ii++){
				this.state.enrolledCourses.add(r.message[ii])
			}
		})
		if (this.debug) console.log('Updated State', this.state.enrolledCourses)
	},

	updateCompletedCourses (){
		if (this.debug) console.log('Updating States')
		frappe.call("erpnext.www.academy.get_completed_courses").then( r => {
			for(var ii=0; ii < r.message.length; ii++){
				this.state.completedCourses.add(r.message[ii])
			}
		})
		if (this.debug) console.log('Updated State', this.state.completedCourses)
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