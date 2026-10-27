// Relative URLs: funktionieren direkt und hinter Home-Assistant-Ingress
async function req(method, path, body, isForm = false) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    if (isForm) opts.body = body
    else { opts.body = JSON.stringify(body); opts.headers['Content-Type'] = 'application/json' }
  }
  const r = await fetch('api/' + path, opts)
  if (!r.ok) {
    let msg = `${r.status}`
    try { msg = (await r.json()).detail || msg } catch {}
    throw new Error(msg)
  }
  return r.json()
}
export const api = {
  get: (p) => req('GET', p),
  post: (p, b) => req('POST', p, b ?? {}),
  patch: (p, b) => req('PATCH', p, b),
  put: (p, b) => req('PUT', p, b),
  del: (p) => req('DELETE', p),
  upload: (p, file) => { const f = new FormData(); f.append('file', file); return req('POST', p, f, true) },
}
export const photoUrl = (id, thumb = false) => `api/photos/${id}${thumb ? '?thumb=1' : ''}`
