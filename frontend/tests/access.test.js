import test from 'node:test'
import assert from 'node:assert/strict'
import { navigationDecision } from '../src/utils/access.js'

const adminPage = { path: '/manager/userlist', matched: [{ meta: { requiresAdmin: true } }] }
test('anonymous users cannot open business pages', () => {
  assert.equal(navigationDecision(adminPage, null, null), '/login')
})
test('ordinary users cannot bypass the menu by typing an admin URL', () => {
  assert.equal(navigationDecision(adminPage, 'token', { role: 'student' }), '/manager/home')
})
test('missing identity fails closed on admin pages', () => {
  assert.equal(navigationDecision(adminPage, 'token', null), '/manager/home')
})
test('resource admins retain their management page', () => {
  assert.equal(navigationDecision(adminPage, 'token', { role: 'admin' }), true)
})
test('login and ordinary resource pages remain usable', () => {
  assert.equal(navigationDecision({ path: '/login' }, null, null), true)
  assert.equal(navigationDecision({ path: '/manager/lablist', matched: [] }, 'token', { role: 'student' }), true)
})

// 初始密码登录只允许进入改密页，刷新后也遵守此规则。
test('temporary login redirects business and admin pages to password change', () => {
  for (const path of ['/manager/home', '/manager/aichat', '/manager/userlist']) {
    assert.equal(navigationDecision({path}, 'token', {role:'admin', must_change_password:true}), '/manager/password')
  }
})

test('temporary login can change password and return to login for logout', () => {
  const user = {role:'student', must_change_password:true}
  assert.equal(navigationDecision({path:'/manager/password'}, 'token', user), true)
  assert.equal(navigationDecision({path:'/login'}, 'token', user), true)
})

test('completed password change keeps ordinary navigation available', () => {
  assert.equal(navigationDecision({path:'/manager/home'}, 'token', {role:'student', must_change_password:false}), true)
})
