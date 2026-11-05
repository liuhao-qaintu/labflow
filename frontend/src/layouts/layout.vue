<template>
    <div>
         <el-container style="min-height: 100vh">
      <el-header class="top-header">
        <div class="brand">
          <span class="brand-name">{{ PRODUCT_NAME }}</span>
          <span class="brand-description">{{ PRODUCT_SUBTITLE }}</span>
        </div>
        <div class="user-profile">
        <el-dropdown @command="handleDropdownCommand"> 
            <div  style="display: flex;align-items:center ;cursor: pointer;">
                <el-avatar :size="40" :src="userInfo?.avatar" style="margin-right:10px">{{ userInfo?.username?.slice(0,1).toUpperCase() || 'U' }}</el-avatar>
                <span>{{ userInfo?.username }}</span>
            </div>
            <template #dropdown>
                <el-dropdown-menu>
                <el-dropdown-item v-if="!userInfo?.must_change_password" command ="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command ="password">修改密码</el-dropdown-item>
                <el-dropdown-item divided command ="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
            </template>
        </el-dropdown>
        </div>
      </el-header>
      <el-container>
        <el-aside width="200px">
          <el-menu v-if="!userInfo?.must_change_password" router style="height: 100%" :default-active="router.currentRoute.value.path">
            <el-menu-item index="/manager/home">
              <el-icon> <House /> </el-icon> 
              <span>工作台</span>
            </el-menu-item>
            <el-menu-item v-if="userInfo?.role === 'student' "index="/manager/lablist">
              <el-icon><OfficeBuilding /></el-icon>
              <span>浏览实验室</span>
            </el-menu-item>
            <el-menu-item v-if="userInfo?.role === 'student' "index="/manager/myReservation">
              <el-icon><Tickets /></el-icon>
              <span>我的预约</span>
            </el-menu-item>
            <el-menu-item  index="/manager/aichat" >
              <el-icon><OfficeBuilding /></el-icon>
              <span>资源协作助手</span>
            </el-menu-item>
            <el-menu-item v-if="userInfo?.role === 'admin' "index="/manager/equipment">
              <el-icon><Setting /></el-icon>
              <span>设备列表管理</span>
            </el-menu-item>
            <el-menu-item v-if="userInfo?.role === 'admin' "index="/manager/lab">
              <el-icon><Monitor /></el-icon>
              <span>实验室管理</span>
            </el-menu-item>
            <el-menu-item v-if="userInfo?.role === 'admin' "index="/manager/auditReservation">
              <el-icon><DocumentChecked /></el-icon>
              <span>预约审核</span>
            </el-menu-item>
            <el-menu-item v-if="userInfo?.role === 'admin' "index="/manager/userlist">
              <el-icon><Avatar /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
          </el-menu>
          <el-menu v-else router :default-active="router.currentRoute.value.path">
            <el-menu-item index="/manager/password">修改初始密码</el-menu-item>
          </el-menu>
        </el-aside>
        <el-main style="background-color: #f4f7fa;">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
    </div>
</template>

<script setup>
import { PRODUCT_NAME, PRODUCT_SUBTITLE } from '@/branding'
import { Avatar,Monitor,Setting,House,OfficeBuilding,Tickets,DocumentChecked } from '@element-plus/icons-vue'
import router from '@/router';
import { useUser } from '@/utils/user'
import { logout } from '@/utils/auth';
const { userInfo } = useUser()
const login_out = () =>{
    router.push('/login')
}

const handleDropdownCommand = (command) => {
  if (command === 'profile') {
    router.push('/manager/userinfo')
  } else if (command === 'logout') {
    logout()
    router.push('/login')
  } else if (command ==='password') {
    router.push('/manager/password')
  }
}
</script>

<style scoped>
.top-header {
  --profile-right-gap: 24px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #ddd;
  background-color: #fff;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 24px;
  font-weight: bold;
}
.brand-name { color:#176d78; letter-spacing:-.7px; }
.brand-description { border-left:1px solid #dbe4e8; padding-left:14px; color:#526673; font-size:14px; font-weight:500; }
.top-header { min-height:74px; border-bottom-color:#e0e8ed; }
@media(max-width:650px) { .brand-description { display:none; } }

.user-profile {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  margin-right: var(--profile-right-gap);
}

.user-profile img {
  width: 30px;
  border-radius: 50%;
}
</style>
