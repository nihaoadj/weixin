const port = Number(process.env.WECHAT_AUTO_PORT || 9420)
const socket = new WebSocket(`ws://127.0.0.1:${port}`)
const pending = new Map()
let sequence = 0

function request(method, params = {}, timeout = 10000) {
  const id = `probe-${++sequence}`
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id)
      reject(new Error(`timeout:${method}`))
    }, timeout)
    pending.set(id, { resolve, reject, timer })
    socket.send(JSON.stringify({ id, method, params }))
  })
}

socket.onmessage = ({ data }) => {
  let response
  try {
    response = JSON.parse(String(data))
  } catch {
    return
  }
  const operation = pending.get(response.id)
  if (!operation) return
  clearTimeout(operation.timer)
  pending.delete(response.id)
  if (response.error) operation.reject(new Error(`protocol-error:${response.error.code || 'unknown'}`))
  else operation.resolve(response.result)
}

try {
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('timeout:websocket')), 10000)
    socket.onopen = () => {
      clearTimeout(timer)
      resolve()
    }
    socket.onerror = () => {
      clearTimeout(timer)
      reject(new Error('unavailable:websocket'))
    }
  })
  const info = await request('Tool.getInfo')
  console.log(JSON.stringify({ toolVersion: info.version || null, baseLibraryVersion: info.SDKVersion || null }))
  const current = await request('App.getCurrentPage')
  console.log(JSON.stringify({ currentPath: current.path || null, pageIdAvailable: Boolean(current.pageId) }))
  const element = await request('Page.getElement', {
    pageId: current.pageId,
    selector: '.role-button.student',
  })
  console.log(JSON.stringify({ elementFound: Boolean(element?.elementId), tagName: element?.tagName || null }))
} catch (error) {
  console.error(error instanceof Error ? error.message : 'FAIL: protocol probe')
  process.exitCode = 1
} finally {
  for (const operation of pending.values()) {
    clearTimeout(operation.timer)
    operation.reject(new Error('probe-closed'))
  }
  pending.clear()
  socket.close()
}
