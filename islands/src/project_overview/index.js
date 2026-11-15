import { mountVueIsland } from "@framework/ui/island";

import ProjectOverview from "./ProjectOverview.vue";

export const mount = (el, context) => mountVueIsland(el, { ...context, component: ProjectOverview });
