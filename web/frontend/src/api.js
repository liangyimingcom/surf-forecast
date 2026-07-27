// 统一取数：credentials 带 cookie（登录态），失败抛错供页面降级处理。
export async function getJSON(url) {
  const r = await fetch(url, { credentials: 'include' })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export const api = {
  regions: () => getJSON('/api/regions'),
  recommend: (region) => getJSON(`/api/recommend?region=${encodeURIComponent(region || '')}`),
  flags: () => getJSON('/api/flags'),
  catalog: () => getJSON('/api/catalog'),
}
