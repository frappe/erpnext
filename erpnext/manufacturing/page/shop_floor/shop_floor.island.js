import { mountVueIsland } from "@framework/ui/island";

import Page from "./shop_floor.vue";

export const mount = (el, context) => mountVueIsland(el, { ...context, component: Page });
