import request from '@/utils/request'

// 说白了，保留增删改查四个能力就行，其他是给用户用的
export function getLabPageList(params) {
    return request({
        url:`/router/lab/list`,
        method:'get',
        params
    })
}


export function createLabApi(data){
    return request({
        url:`/router/lab`,
        method:'post',
        data
    })
}

export function updateLabApi(labId,data){
    return request({
        url:`/router/lab/${labId}`,
        method:'put',
        data
    })
}

export function deteleLabApi(labId){
    return request({
        url:`/router/lab/${labId}`,
        method:'delete',
    })
}

// 根据Id查询实验室
export function getLab(lab_id){
    return request({
        url:`/router/lab/${lab_id}`,
        method:'get'
    })
}