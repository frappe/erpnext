import { mountVueIsland } from "@framework/ui/island";

import ProjectTasks from "./ProjectTasks.vue";

export const mount = (el, context) => mountVueIsland(el, { ...context, component: ProjectTasks });
