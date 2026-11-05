<template>
    <div>
        <el-card style="max-width: 480px">
            <template #header>
            <div class="card-header">
                <span>修改密码</span>
            </div>
            </template>
            <el-alert v-if="userInfo?.must_change_password" title="请先修改管理员提供的初始密码" description="完成改密并重新登录后，即可使用预约和资源协作功能。" type="warning" :closable="false" show-icon style="margin-bottom:20px" />
            <el-form
            ref="formRef"
            style="max-width: 600px"
            :model="form"
            :rules="rules"
            label-width="auto"
            >
                <el-form-item label="原密码" prop ="oldPassword" >
                    <el-input required v-model="form.oldPassword" placeholder="请输入原密码或管理员提供的初始密码" show-password />
                </el-form-item>
                <el-form-item label="新密码" prop="newPassword" >
                    <el-input required v-model="form.newPassword" placeholder="至少8个字符，不超过72个UTF-8字节" show-password autocomplete="new-password" />
                </el-form-item>
                <el-form-item label="确认密码" prop="confirmPassword" >
                    <el-input required v-model="form.confirmPassword" placeholder="确认新密码" show-password @keyup.enter="handleSubmit" />
                </el-form-item>
            </el-form>
            <template #footer>
                <div style="display: flex; justify-content: flex-end; gap: 8px">
                    <el-button @click="handleReset">重置</el-button>
                    <el-button type="primary" :loading="submitting" @click="handleSubmit">确认修改</el-button>
                </div>
            </template>
         </el-card>
    </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import {ref,reactive} from 'vue'
import  router  from '@/router'
import { updatePasswordAPi } from '@/router/user'
import { logout } from '@/utils/auth'
import { useUser } from '@/utils/user'

const { userInfo } = useUser()

const submitting = ref(false)
const formRef = ref()
const form = reactive({
    oldPassword:'',
    newPassword:'',
    confirmPassword:'',
}
)

const validatePass = (rule,value,callback) => {
    if (value === ''){
        callback(new Error ('请确认密码'))
    } else if (value !==form.newPassword){
        callback(new Error ('两次输入的密码不一致'))
    } else {
        callback()
    }
}

const validateNewPass = (rule,value,callback) => {
    if ([...value].length < 8 || new TextEncoder().encode(value).length > 72) {
        callback(new Error('密码至少8个字符，且不超过72个UTF-8字节'))
    } else if (value === form.oldPassword) {
        callback(new Error('新密码不能与原密码相同'))
    } else {
        callback()
    }
}

const rules = {
    oldPassword:[{required:true , message:"请输入原密码",trigger:'blur'}],
    newPassword:[{required:true , message:"请输入新密码",trigger:'blur'},{validator:validateNewPass,trigger:'blur'}],
    confirmPassword:[{validator: validatePass  ,trigger:'blur'}]
}
const handleSubmit = async() =>{
    if (submitting.value) return
    const vaild =await formRef.value.validate().catch(() => false)
    if (!vaild) return 
    submitting.value =true
    try {
        const res = await updatePasswordAPi({old_password:form.oldPassword,new_password:form.newPassword})
        if (res.code ===200) {
            ElMessage.success('密码修改成功，请重新登录')
            logout()
            await router.push('/login')
        }
    }finally {
            submitting.value = false
        }
    }

const handleReset = () => {
  form.oldPassword = ''
  form.newPassword = ''
  form.confirmPassword = ''
  formRef.value?.clearValidate()
}
</script>
