<template>
    <div class="auth-page">
        <div class ='login-container'>
            <div class="auth-brand">{{ PRODUCT_NAME }}</div>
            <h1>{{ PRODUCT_SUBTITLE }}</h1>
            <p class="auth-intro">查找资源、核对规则，在确认后提交预约。</p>
            <el-form ref="formRef" :model="form" :rules="rules" label-width="auto" style="max-width: 600px">
                <el-form-item label="账号" prop="username">
                    <el-input v-model="form.username" style ="background-color: white;" placeholder="请输入账号" :prefix-icon="User" />
                </el-form-item>
                <el-form-item label="密码" prop="password">
                    <el-input type="password" v-model="form.password" style ="background-color: white;" placeholder="请输入密码" :prefix-icon="Lock"  show-password/>
                </el-form-item>
                <div class="login-actions">
                    <el-button type="primary" class="login_width" @click="login" :loading ="loadingValue" :loading-icon="Eleme">登 录</el-button>
                </div>
                <div class="recovery-entry"><RouterLink to="/forgot-password">忘记密码？</RouterLink></div>
                <div style="text-align: right;
                    margin-top: 15px;">还没有账号？请<a class="custom-class" href="/register" >注册</a></div>
            </el-form>
        </div>
    </div>
</template>

<style scoped>
.login-container{
    width:min(430px,100%); background:#fff; border:1px solid #e0e8ed;
    border-radius:18px; box-shadow:0 22px 70px #203b4c12; padding:38px;
}
.auth-page { min-height:100vh; display:grid; place-items:center; padding:24px; background:linear-gradient(145deg,#eef6f5,#f6f8fc); }
.auth-brand { color:#176d78; font-size:32px; font-weight:750; letter-spacing:-1px; }
h1 { margin:8px 0; font-size:21px; color:#203b4c; }
.auth-intro { margin-bottom:28px; font-size:13px; line-height:1.8; color:#74838d; }
.login_width{
    width:100%;
    text-align: center;
    --el-button-bg-color:#176d78; --el-button-border-color:#176d78;
}
.login-actions {
    display: flex;
    justify-content: center;
}
.recovery-entry { margin-top:14px; font-size:13px; color:#176d78; }
.custom-class {
  --el-color-primary: rgb(79, 138, 172);
  color:var(--el-color-primary)
}
</style>

<script setup>
import { reactive ,ref} from 'vue'
import { PRODUCT_NAME, PRODUCT_SUBTITLE } from '@/branding'
import {User,Lock} from "@element-plus/icons-vue"
import { ElMessage,ElMessageBox } from 'element-plus'
import router from '@/router';
import { Eleme } from '@element-plus/icons-vue'
import { loginApi } from '@/router/auth';
import { useUser } from '@/utils/user';


const { saveLoginData } = useUser()

const formRef = ref()

const rules = {
    username: [
        {required:true,message:'请输入账号',trigger:'blur'}
    ],
    password:[
        {required:true,message:'请输入密码',trigger:'blur'}
    ]
}
const form =reactive({
    username:'',
    password:'',

})
const loadingValue =ref(false)

const login = async () => {
    const valid =await formRef.value.validate().catch(()=> false)
    if (!valid) return
    loadingValue.value = true
    try{
        const res = await loginApi(form)
        if (res.code ===200){
            saveLoginData(res.data)
            if (res.data.user.must_change_password) {
                await router.push('/manager/password')
                await ElMessageBox.alert('管理员已重置你的密码。请先修改初始密码，完成后重新登录即可使用系统。', '请修改初始密码', {
                    confirmButtonText:'去修改密码',
                    showClose:false,
                    closeOnClickModal:false,
                    closeOnPressEscape:false
                })
                return
            }
            ElMessage.success('登录成功')
            router.push('/manager/home')
        }
} finally {
    loadingValue.value = false
}
}



</script>
