import { mountVueIsland } from "@framework/ui/island";

import ProjectCosting from "./ProjectCosting.vue";

export const mount = (el, context) => mountVueIsland(el, { ...context, component: ProjectCosting });
