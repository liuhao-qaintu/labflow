import service from "@/utils/request";



export function loginApi(data) {
    return service({
        url:'/router/auth/login',
        method:'post',
        data
    })
}

export function registerApi(data) {
    return service({
        url:'/router/auth/register',
        method:'post',
        data
    })
}

export function submitRecoveryApi(data) {
    return service({url:'/router/auth/recovery/requests',method:'post',data})
}

export function lookupRecoveryApi(data) {
    return service({url:'/router/auth/recovery/lookup',method:'post',data})
}

export function supplementRecoveryApi(data) {
    return service({url:'/router/auth/recovery/supplement',method:'post',data})
}
