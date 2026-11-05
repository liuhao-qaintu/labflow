<template>
    <div class="auth-page">
        <div class ='register-container'>
            <div class="auth-brand">{{ PRODUCT_NAME }}</div>
            <h1>创建协作账户</h1>
            <p class="auth-intro">{{ PRODUCT_SUBTITLE }} · 新账户以普通使用者身份加入。</p>
            <el-form ref="formRef"  :model="form" :rules="rules" label-width="auto" style="max-width: 600px">
                <el-form-item label="账号" prop = "username">
                    <el-input size="large" type="username" v-model="form.username" style ="background-color: white;" placeholder="请输入账号" :prefix-icon="User" />
                </el-form-item>
                <el-form-item label="密码" prop="password">
                    <el-input size="large" type="password" v-model="form.password" style ="background-color: white;" placeholder="请输入密码" :prefix-icon="Lock"  show-password/>
                </el-form-item>
                <el-form-item label="确认密码" prop="confirmpassword">
                    <el-input size="large" type="password" v-model="form.confirmpassword" style ="background-color: white;" placeholder="请确认密码" :prefix-icon="Lock"  show-password/>
                </el-form-item>
                <div class="register-actions">
                    <el-button type="primary" class="register_width"  @click="register" :loading="loadingValue">注 册</el-button>
                </div>
                <div style="text-align: right;
                    margin-top: 15px;">已有账号？请<a class="custom-class" href="/login" >登 录</a></div>
            </el-form>
        </div>
    </div>
</template>

<style scoped>
.register-container{
    width:min(430px,100%); background:#fff; border:1px solid #e0e8ed;
    border-radius:18px; box-shadow:0 22px 70px #203b4c12; padding:38px;
}
.auth-page { min-height:100vh; display:grid; place-items:center; padding:24px; background:linear-gradient(145deg,#eef6f5,#f6f8fc); }
.auth-brand { color:#176d78; font-size:32px; font-weight:750; letter-spacing:-1px; }
h1 { margin:8px 0; font-size:21px; color:#203b4c; }
.auth-intro { margin-bottom:28px; font-size:13px; line-height:1.8; color:#74838d; }
.register_width{
    width:100%;
    text-align: center;
    --el-button-bg-color:#176d78; --el-button-border-color:#176d78;
}
.register-actions {
    display: flex;
    justify-content: center;
}
.custom-class {
  --el-color-primary: rgb(79, 138, 172);
   color: var(--el-color-primary);
}
</style>

<script setup>
import { reactive ,ref} from 'vue';
import { PRODUCT_NAME, PRODUCT_SUBTITLE } from '@/branding'
import {User,Lock} from "@element-plus/icons-vue";
import { ElMessage } from 'element-plus';
import { registerApi } from '@/router/auth';
import router from '@/router';
const formRef = ref()

const validatePass = (rule,value,callback) =>{
    if (value ===''){
        callback(new Error("请输入密码"))
    }else {
        if(value!== form.password) {
            callback(new Error('两次密码输入不一致'))
        } else {
            callback()
        }
    }
}
const rules = {
    username: [
        {required:true,message:'请输入账号',trigger:'blur'}
    ],
    password:[
        {required:true,message:'请输入密码',trigger:'blur'}
    ],
    confirmpassword:[
        {validator:validatePass,trigger:'blur'}
    ]
}
const form =reactive({
    username:'',
    password:'',
    confirmpassword:'',

})
const loadingValue = ref(false)

const register = async () => {
    const valid =await formRef.value.validate().catch(()=> false)
    if (!valid) return
    loadingValue.value = true
    try{
        const res = await registerApi(form)
        setTimeout(() => {
            if (res.code ===200){
                ElMessage.success('注册成功')
                router.push('/login')
            }
        }, 2000)
} finally {
    loadingValue.value = false
}
}

</script>
