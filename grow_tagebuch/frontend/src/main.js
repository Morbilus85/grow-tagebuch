import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import './style.css'
import App from './App.vue'
import Today from './views/Today.vue'
import PlantView from './views/PlantView.vue'
import Water from './views/Water.vue'
import LogForm from './views/LogForm.vue'
import Climate from './views/Climate.vue'
import Light from './views/Light.vue'
import More from './views/More.vue'
import RunEdit from './views/RunEdit.vue'
import Inventory from './views/Inventory.vue'
import Schedules from './views/Schedules.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: Today },
    { path: '/pflanze/:id', component: PlantView },
    { path: '/giessen', component: Water },
    { path: '/eintrag', component: LogForm },
    { path: '/eintrag/:id', component: LogForm },
    { path: '/klima', component: Climate },
    { path: '/licht', component: Light },
    { path: '/mehr', component: More },
    { path: '/run/:id', component: RunEdit },
    { path: '/inventar', component: Inventory },
    { path: '/schema', component: Schedules },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

createApp(App).use(router).mount('#app')
