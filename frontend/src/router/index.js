import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getUserInfo } from '@/utils/auth'
import { navigationDecision } from '@/utils/access'
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/manager/home' },
    {
      path: '/manager',
      name: 'layout',
      component: () => import('@/layouts/layout.vue'),
      children: [
        { path: 'home', name: 'home', component: () => import('@/components/home.vue') },
        { path: 'lab', name: 'lab', meta: { requiresAdmin: true }, component: () => import('@/components/lab.vue') },
        { path: 'equipment', name: 'equipment', meta: { requiresAdmin: true }, component: () => import('@/components/equipment.vue') },
        { path: 'userinfo', name: 'userinfo', component: () => import('@/components/profile.vue') },
        { path: 'password', name: 'password', component: () => import('@/components/password.vue') },
        { path: 'userlist', name: 'userlist', meta: { requiresAdmin: true }, component: () => import('@/components/userlist.vue') },
        { path:'lablist',name:'lablist',component:()=> import('@/components/lablist.vue')} ,
        { path: 'labEquipment', name: 'labEquipment', component: () => import('@/components/labEquipment.vue') },
        { path: 'myReservation', name: 'myReservation', component: () => import('@/components/myreservation.vue') },
        { path: 'auditReservation', name: 'auditReservation', meta: { requiresAdmin: true }, component: () => import('@/components/auditreservation.vue') },
        { path: 'aichat',name:'aichat',component:() =>import('@/components/aichat.vue')}
      ],
    },
    { path: '/login', name: 'login', component: () => import('@/components/login.vue') },
    { path: '/forgot-password', name: 'forgot-password', component: () => import('@/components/forgotPassword.vue') },
    { path:'/register',name:'register',component:()=> import('@/components/register.vue')},
  ]
})


router.beforeEach(to => navigationDecision(to, getToken(), getUserInfo()))

export default router
