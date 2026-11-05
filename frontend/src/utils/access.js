export function navigationDecision(to, token, user) {
  if (['/login', '/register', '/forgot-password'].includes(to.path)) return true
  if (!token) return '/login'
  if (user?.must_change_password && to.path !== '/manager/password') return '/manager/password'
  if (to.matched?.some(record => record.meta?.requiresAdmin) && user?.role !== 'admin') return '/manager/home'
  return true
}
