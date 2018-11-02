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
		currentEnrollment: '',
		currentStudentID: '',
	},
	setCourseEnrollment (enrollment) {
	    if (this.debug) console.log('setCourseEnrollment triggered with', enrollment)
	    this.state.currentEnrollment = enrollment
	},
	addCompletedCourses (courseName){
		if (this.debug) console.log('addCompletedCourses triggered with', courseName)
		this.state.completedCourses.add(courseName)
	},
	checkCourseCompletion (courseName){
		return this.state.completedCourses.has(courseName)
	},
	updateState (){
		if (this.debug) console.log('Updating States')
		frappe.call("erpnext.www.academy.get_state").then( r => {
			this.state.completedCourses.clear()
			for(var ii=0; ii < r.message.length; ii++){
				this.state.completedCourses.add(r.message[ii])
			}
		})
		if (this.debug) console.log('Updated State', this.state.completedCourses)
	}
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
			store.updateState()
		}
	});
})