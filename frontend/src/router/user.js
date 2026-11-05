import request from '@/utils/request'

export function getUserInfoApi(){
    return request({
        url:`/router/user/me`,
        method:'get'
    })
}

export function updateUserInfoApi(data) {
    return request({
        url:`/router/user/me`,
        method:'put',
        data
    })
}

export function updatePasswordAPi(data){
    return request({
        url:`/router/user/password`,
        method:'put',
        data
    })
}

export function getUserPageList(params) {
    return request({
        url:`/router/user/list`,
        method:'get',
        params
    })
}


export function createUserApi(data){
    return request({
        url:`/router/user`,
        method:'post',
        data
    })
}

export function updateUserApi(userId,data){
    return request({
        url:`/router/user/${userId}`,
        method:'put',
        data
    })
}

export function deteleUserApi(userId){
    return request({
        url:`/router/user/${userId}`,
        method:'delete',
    })
}

export function resetUserPasswordApi(userId){
    return request({
        url:`/router/user/${userId}/password/reset`,
        method:'put',
        data:{identity_verified:true}
    })
}

export function getRecoveryRequestsApi(params){
    return request({url:'/router/user/recovery/requests',method:'get',params})
}

export function getRecoveryDetailApi(requestId){
    return request({url:`/router/user/recovery/requests/${requestId}`,method:'get'})
}

export function handleRecoveryApi(requestId,data){
    return request({url:`/router/user/recovery/requests/${requestId}`,method:'put',data})
}
