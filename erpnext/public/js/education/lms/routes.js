import Home from "./pages/Home.vue";
import ProgramPage from "./pages/ProgramPage.vue";
import ContentPage from "./pages/ContentPage.vue";
import ListPage from "./pages/ListPage.vue";

const routes = [
	{name: 'home', path: '', component: Home},
	{name: 'program', path: '/Program/:program_name', component: ProgramPage, props: true},
	{name: 'content', path: '/Program/:program_name/:course/:type/:content', component: ContentPage, props: true},
	{name: 'list', path: '/List/:master', component: ListPage, props: true},
	{
		name: 'signup',
		path: '/Signup',
		beforeEnter(to, from, next) {
        	window.location = window.location.origin.toString() +'/login#signup'
    	},
		component: ListPage,
		props: true
	},
];

export default routes;