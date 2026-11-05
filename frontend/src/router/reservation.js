import request from "@/utils/request"

export function createReservationApi(data){
    return request({
        url:'/router/reservation',
        method:'post',
        data
})
}

export function getReservationPageListApi(params){
    return request({
        url:'/router/reservation/list',
        method:'get',
        params
    })
}


export function cancelReservationApi(id){
    return request({
        url:`/router/reservation/${id}/cancel`,
        method:'put',
    })
}

export function auditReservationApi(id,status){
    return request({
        url:`/router/reservation/${id}/audit`,
        method:'put',
        data:{status}
    })
}