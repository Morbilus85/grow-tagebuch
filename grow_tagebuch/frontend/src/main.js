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
import Seeds from './views/Seeds.vue'
import Inventory from './views/Inventory.vue'
import Schedules from './views/Schedules.vue'
import Training from './views/Training.vue'
import TrainingDetail from './views/TrainingDetail.vue'
import Germination from './views/Germination.vue'
import LivingSoil from './views/LivingSoil.vue'
import Pests from './views/Pests.vue'
import PestCase from './views/PestCase.vue'

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
    { path: '/run/:id/samen', component: Seeds },
    { path: '/inventar', component: Inventory },
    { path: '/schema', component: Schedules },
    { path: '/training', component: Training },
    { path: '/keimung', component: Germination },
    { path: '/living-soil', component: LivingSoil },
    { path: '/schaedlinge', component: Pests },
    { path: '/schaedlinge/:id', component: PestCase },
    { path: '/living-soil/rezept/:key', component: LivingSoil },
    { path: '/keimung/:key', component: Germination },
    { path: '/training/:key', component: TrainingDetail },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

createApp(App).use(router).mount('#app')
