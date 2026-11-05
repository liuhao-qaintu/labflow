<template>
    <div>
        <el-card style="max-width: 90%;margin:0px auto">
            <template #header>
            <div style = "font-size:16px;font-weight:bold;">
                <span>用户管理</span>
                <el-badge :value="recoveryPending" :hidden="!recoveryPending" style="float:right;margin-right:12px">
                    <el-button @click="recoveryVisible=true">找回密码申请</el-button>
                </el-badge>
            </div>
            </template>
            <div style="margin-bottom: 10px;">
                <el-input placeholder ="请输入账号或者名称查询" 
                v-model="params.keywords"
                style="width:240px;margin-right: 8px;"
                clearable
                @keyup.enter="handlesearch"
                @clear = "handlesearch"></el-input>
                <el-button type="primary" :icon="Search" @click="handlesearch">查询</el-button>
                <el-button type="success" :icon="Plus" @click="handlecreate">新增</el-button>
            </div>
                <el-table :data="tableData" style="width: 100%"
                :header-cell-style = "{backgroundColor:'#f5f7fa',color:'#333'}"
                v-loading = "loading">
                    <el-table-column label="账号" prop="username" />
                    <el-table-column label="名称" prop="name" />
                    <el-table-column label="头像" prop="avatar" >
                        <template #default="{ row }">
                            <div>
                                <img v-if="row.avatar" 
                                :src="row.avatar" 
                                style="display: block; width: 50px; height: 50px; border-radius: 50%;
                                alt:">
                            </div>
                        </template>
                    </el-table-column>
                    <el-table-column label="邮箱" prop="email" />
                    <el-table-column label="手机号" prop="phone" />
                     <el-table-column label="角色" prop="role" width = "100">
                        <template #default="{ row }">
                                {{ row.role ==='admin' ?"管理员" :'学生' }}
                        </template>
                    </el-table-column>
                    <el-table-column label="状态" prop="status" width = "100">
                        <template #default="{ row }">
                            <el-tag :type = "row.status ===1?'success':'error'">
                                {{ row.status ===1 ?"正常" :'禁用' }}
                            </el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column label="操作" header-align="center" min-width="260">
                        <template #default="{ row }">
                            <el-button type="primary" text bg @click="handleEdit(row)">编辑</el-button>
                            <el-button type="danger" text bg @click="handleDelete(row)">删除</el-button>
                            <el-button v-if="row.can_reset_password"
                              :loading="resettingUser === row.id" :disabled="resettingUser !== null" @click="handleResetPassword(row)">重置</el-button>
                        </template>
                    </el-table-column>
                </el-table>
                <div style="margin-top: 10px; 
                display: flex; 
                justify-content: flex-end">         
               <el-config-provider :locale="zhCn">
                <el-pagination
                    v-model:current-page="params.page"
                    v-model:page-size="params.pageSize"
                    :total="total"
                    background
                    layout="total, prev, pager, next"
                    @current-change="load"
                />
                </el-config-provider>
                </div>
           
        </el-card>
        <RecoveryInbox v-model="recoveryVisible" @updated="handleRecoveryUpdated" />
        <el-dialog v-model="dialogTableVisible" :title="form.id? '编辑' : '新增'" width="800">
            <el-form
            ref="formRef"
            style="max-width: 600px"
            :model="form"
            :rules="rules"
            label-width="auto"
            v-loading ="loading"
            >
                <el-form-item label="账号" prop="username" >
                    <el-input :disabled="!!form.id" v-model="form.username" placeholder="请输入账号" />
                </el-form-item>
                <el-form-item v-if="!form.id" label="密码" prop="password" >
                    <el-input type="password" show-password v-model="form.password" placeholder="请输入密码" />
                </el-form-item>
                <el-form-item label="名称" prop="name" >
                    <el-input v-model="form.name" placeholder="请输入名称" />
                </el-form-item>
                <el-form-item label="角色" prop="role" >
                    <el-select v-model="form.role">
                        <el-option label="学生" value="student"></el-option>
                        <el-option label="管理员" value="admin"></el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="邮箱"  >
                    <el-input v-model="form.email"  placeholder="请输入邮箱"/>
                </el-form-item>
                <el-form-item label="手机号" prop="phone" >
                    <el-input v-model="form.phone" placeholder="请输入手机号"  />
                </el-form-item>
                <el-form-item label="状态">
                    <el-radio-group v-model="form.status">
                        <el-radio :value="1">正常</el-radio>
                        <el-radio :value="0">禁用</el-radio>
                    </el-radio-group>
                </el-form-item>
            </el-form>   
            <template #footer>
                <el-button @click = "dialogTableVisible=false">取消</el-button>
                <el-button type="primary" :loading="formLoading" @click= "handleSave">确认</el-button>
            </template>
        </el-dialog>

    </div>
</template>

<script setup>
import { ref,reactive,onMounted } from 'vue'
import { getUserPageList ,createUserApi,updateUserApi,deteleUserApi,resetUserPasswordApi,getRecoveryRequestsApi} from '@/router/user';
import { Plus, Search } from '@element-plus/icons-vue';
import { ElMessage,ElMessageBox } from 'element-plus';
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import RecoveryInbox from '@/components/recoveryInbox.vue'
const recoveryVisible = ref(false),recoveryPending = ref(0)
const loadRecoveryCount = async() => {
    try {
        const res = await getRecoveryRequestsApi({page:1,page_size:1})
        if (res.code ===200) recoveryPending.value = res.data.pending
    } catch {
        // 请求层统一提示。
    }
}
const handleRecoveryUpdated = () => { load(); loadRecoveryCount() }
const resettingUser = ref(null)
const handleResetPassword = async(row) => {
    if (resettingUser.value !== null) return
    try {
        await ElMessageBox.confirm(`确认已核验账号“${row.username}”的申请人身份？重置后原密码及登录状态失效，用户需使用管理员提供的初始密码登录并立即改密。仅有用户名不足以证明身份。`, '确认重置密码', {
            type:'warning',
            confirmButtonText:'已核验，重置',
            cancelButtonText:'取消'
        })
    } catch { return }
    resettingUser.value = row.id
    try {
        const res = await resetUserPasswordApi(row.id)
        if (res.code ===200) {
            ElMessage.success(res.message)
            await load()
        }
    } catch {
        // 请求层统一提示，不输出密码或请求对象。
    } finally {
        resettingUser.value = null
    }
}

const params = reactive ({
    page:1,
    pageSize:10,
    keywords:''
})

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogTableVisible =ref(false)
const formRef = ref()
const form =reactive({
    username:'',
    password:'',
    name:'',
    role:'student',
    email:'',
    phone:'',
    avatar:'',
    status:1
})
const formLoading = ref(false)


const rules = {
    username:[{required:true,message:'请输入账号',trigger:'blur'}],
    password:[
        {required:true,message:'请输入密码',trigger:'blur'},
        {min:3,max:10,message:'密码是3-10位',tirgger:'blur'}
    ],
    name:[{required:true,message:'请输入名称',trigger:'blur'}],
    email: [{type:'email',message:'邮箱格式错误',trigger:'blur'}],
    phone : [{pattern:/^1[3-9]\d{9}$/,message:'手机号格式错误',trigger:'blur'}],
}
// 创建和更新共用一个表单,但是不同情况的值不一样，由id决定
const resetForm = () =>{
    Object.assign(form,{
        id:null,
        username:'',
        password:'',
        name:'',
        email:'',
        phone:'',
        avatar:'',
        role:'student',
        status:1,
    })
}

const handlecreate = () =>{
    resetForm()
    dialogTableVisible.value = true
}

const handleEdit = (row) =>{
    resetForm()
    Object.assign(form,{
        id:row.id,
        username:row.username,
        name:row.name,
        email:row.email,
        phone:row.phone,
        avatar:row.avatar,
        role:row.role,
        status:row.status,
    })
    dialogTableVisible.value =true
}
// 删除用户
const handleDelete = (row) =>{
    ElMessageBox.confirm(`确认删除用户[${row.username}]?`,`确认删除`,{ type:`warning`}).then(
        async() =>{
            const res = await deteleUserApi(row.id)
            if(res.code==200){
            ElMessage.success('删除成功')
            load()       
            }
        }
    )
}
// 保存用户
const handleSave = async () =>{
    const vaild =await formRef.value.validate().catch(() => false)
    if (!vaild) return 
    formLoading.value =true
    try {
        const payload = { ...form }
        if (form.id) delete payload.password
        const res = form.id ? await updateUserApi(form.id,payload):await createUserApi(payload)
        if (res.code ==200) {
            dialogTableVisible.value =false
            ElMessage.success('更新成功')
        }
    }finally {
            formLoading.value = false
        }
}
// 加载分页数据
const load = async () =>{
    loading.value = true
    try{
        const res = await getUserPageList({
            page:params.page,
            page_size:params.pageSize,
            keywords:params.keywords
        }
        )
        if (res.code ==200){
            tableData.value =res.data?.list
            total.value = res.data?.total
        }
    }finally{
        loading.value =false
    }
}

const handlesearch = async () =>{
    params.page = 1
    load()
}

onMounted(() => {
    loadRecoveryCount()
    load()
})
</script>
