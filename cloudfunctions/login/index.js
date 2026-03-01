// cloudfunctions/login/index.js
const cloud = require('wx-server-sdk')

// 初始化云开发环境
cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()
const _ = db.command

exports.main = async (event, context) => {
  try {
    const { code, userInfo, role } = event
    
    // 1. 调用微信登录接口获取openid
    const loginRes = await cloud.auth().code2Session({
      js_code: code
    })
    
    const openid = loginRes.openid
    
    // 2. 检查用户是否已存在
    const userRes = await db.collection('users').where({
      openid
    }).get()
    
    let user
    if (userRes.data.length === 0) {
      // 3. 新用户注册
      const addRes = await db.collection('users').add({
        data: {
          openid,
          role,
          avatarUrl: userInfo.avatarUrl,
          nickName: userInfo.nickName,
          createdAt: new Date(),
          updatedAt: new Date()
        }
      })
      
      // 获取新用户信息
      user = {
        _id: addRes._id,
        openid,
        role,
        avatarUrl: userInfo.avatarUrl,
        nickName: userInfo.nickName,
        createdAt: new Date(),
        updatedAt: new Date()
      }
    } else {
      // 4. 老用户更新信息
      user = userRes.data[0]
      await db.collection('users').doc(user._id).update({
        data: {
          role,
          avatarUrl: userInfo.avatarUrl,
          nickName: userInfo.nickName,
          updatedAt: new Date()
        }
      })
      
      // 更新用户信息
      user = {
        ...user,
        role,
        avatarUrl: userInfo.avatarUrl,
        nickName: userInfo.nickName,
        updatedAt: new Date()
      }
    }
    
    return {
      success: true,
      user
    }
  } catch (error) {
    console.error('登录失败:', error)
    return {
      success: false,
      message: '登录失败',
      error: error.message
    }
  }
}