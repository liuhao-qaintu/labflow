<template>
    <div>
        <el-card style="max-width: 480px">
            <template #header>
            <div class="card-header">
                <span>个人信息</span>
            </div>
            </template>
            <el-form
            ref="formRef"
            style="max-width: 600px"
            :model="form"
            :rules="rules"
            label-width="auto"
            v-loading ="loading"
            >
                <el-form-item label="头像" >
                    <el-upload ref="uploadRef" action="#" list-type="picture-card" :auto-upload="true" :http-request ="handleFileUpload" accept="image/jpeg,image/png,image/gif,image/webp" :before-upload = "beforeAvatarUpload">
                        <el-dialog v-model="dialogVisible" title="图片预览">
                            <img :src="dialogImageUrl" alt="头像预览" style="display: block; max-width: 40%; margin: 0 auto" />
                        </el-dialog>
                        <el-icon><Plus /></el-icon>
                        <template #file="{ file }">
                            <div>
                                <img class="el-upload-list__item-thumbnail" :src="file.url" alt="" />
                                <span class="el-upload-list__item-actions">
                                    <span class="el-upload-list__item-preview" @click="handlePictureCardPreview(file)">
                                        <el-icon><zoom-in /></el-icon>
                                    </span>
                                    <span  v-if="!disabled"  class="el-upload-list__item-delete" @click="handleDownload(file)">
                                        <el-icon><Download /></el-icon>
                                    </span>
                                    <span v-if="!disabled" class="el-upload-list__item-delete" @click="handleRemove(file)">
                                        <el-icon><Delete /></el-icon>
                                    </span>
                                </span>
                            </div>
                        </template>
                    </el-upload>
                </el-form-item>
                <el-form-item label="账号"  >
                    <el-input disabled v-model="form.username" placeholder="请输入账号" />
                </el-form-item>
                <el-form-item label="名称" prop="name" >
                    <el-input v-model="form.name" placeholder="请输入名称" />
                </el-form-item>
                <el-form-item label="角色" prop="role" >
                    <el-input  disabled v-model="rolelabel"  />
                </el-form-item>
                <el-form-item label="邮箱"  >
                    <el-input v-model="form.email"  placeholder="请输入邮箱"/>
                </el-form-item>
                <el-form-item label="手机号" prop="phone" >
                    <el-input v-model="form.phone" placeholder="请输入手机号"  />
                </el-form-item>
            </el-form>
            <template #footer>
                <div style="display: flex; justify-content: flex-end; gap: 8px">
                    <el-button @click="handleReset">重置</el-button>
                    <el-button type="primary" :loading="submitting" @click="handleSubmit">保存修改</el-button>
                </div>
            </template>
         </el-card>
    </div>
</template>
<style scoped></style>
<script setup>

import { uploadFileApi } from '@/router/file'
import { updateUserInfoApi as updateUserInfo, getUserInfoApi } from '@/router/user'
import { ElMessage } from 'element-plus'
import {ref,reactive, computed, onMounted} from 'vue'
import { useUser } from '@/utils/user'

import { Delete, Download, Plus, ZoomIn } from '@element-plus/icons-vue'

const { updateUser } = useUser()
const loading =ref(false)
const formRef = ref()
const originalForm = ref(null)
const submitting = ref(false)
const form = reactive({
    username:'',
    name:'',
    role:'',
    email:'',
    avatar:'',
})

const rules = {
    name:[{required:true,message:'请输入名称',trigger:'blur'}],
    email: [{type:'email',message:'邮箱格式错误',trigger:'blur'}],
    phone : [{pattern:/^1[3-9]\d{9}$/,message:'手机号格式错误',trigger:'blur'}],
}

const rolelabel = computed(() => {
    return form.role === 'admin'?'管理员' :form.role==='student' ?'学生':'未知npc'
})


const beforeAvatarUpload = (file) => {
    const imageTypes = ['image/jpg','image/jpeg','image/png','image/gif','image/webp']
    if (!imageTypes.includes(file.type)) {
        ElMessage.error ('只能上传图片')
        return false
    }
    if (file.size/ 1024 /1024> 2){
        ElMessage.error('图片大小不能超过 2 MB')
        return false
    }
    return true
}

const handleFileUpload = async ({file})=> {
    try {
        const res = await uploadFileApi(file)
        if (res.code === 200){
            form.avatar = res.data?.url
        } else {
            ElMessage.error(res.message || '图片上传失败')
        }
    } catch (error) {
        ElMessage.error(error?.message || '图片上传失败')
    }
}

const loadUserInfo = async ()=> {
    loading.value = true
    try {
        const res = await getUserInfoApi()
        if (res.code === 200){
            Object.assign(form,res.data)
            originalForm.value = { ...form }
            updateUser(res.data)
        }                                                                        
    } finally {
        loading.value = false
    }
}

const handleSubmit = async() =>{
    const vaild =await formRef.value.validate().catch(() => false)
    if (!vaild) return 
    submitting.value =true
    try {
        const res = await updateUserInfo(form)
        if (res.code ==200) {
            updateUser(res.data)
            ElMessage.success('更新成功')
        }
    }finally {
            submitting.value = false
        }
    }

const handleReset = () => {
    if (!originalForm.value) return

    Object.assign(form, originalForm.value)
    formRef.value?.clearValidate()
    uploadRef.value?.clearFiles()
}

const uploadRef = ref()
const dialogImageUrl = ref('')
const dialogVisible = ref(false)
const disabled = ref(false)
const handleRemove = (file) => {
  uploadRef.value?.handleRemove(file)
  form.avatar = ''
}
const handlePictureCardPreview = (file) => {
  dialogImageUrl.value = file.url
  dialogVisible.value = true
}
const handleDownload = (file) => {
  const link = document.createElement('a')
  link.href = file.url
  link.download = file.name || 'avatar'
  link.click()
}
onMounted (() => {
    loadUserInfo()
})
</script>