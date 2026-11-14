import { mountVueIsland } from "@framework/ui/island";

import Page from "./plant_builder.vue";

export const mount = (el, context) => mountVueIsland(el, { ...context, component: Page });
