import Home from "./pages/Home.vue";
import ProgramPage from "./pages/ProgramPage.vue";
import CoursePage from "./pages/CoursePage.vue";

const routes = [
	{name: 'home', path: '', component: Home},
	{name: 'program', path: '/Program/:program_name', component: ProgramPage, props: true},
	{name: 'content', path: '/Program/:program_name/:course/:type/:content', component: CoursePage, props: true},
];

export default routes;