// cloudfunctions/init/index.js
const cloud = require('wx-server-sdk')

// 初始化云开发环境
cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()
const _ = db.command

exports.main = async (event, context) => {
  try {
    // 1. 创建用户集合
    await db.createCollection('users')
    console.log('用户集合创建成功')
    
    // 2. 创建对话记录集合
    await db.createCollection('conversations')
    console.log('对话记录集合创建成功')
    
    // 3. 创建报告集合
    await db.createCollection('reports')
    console.log('报告集合创建成功')
    
    // 4. 创建用户集合索引
    await db.collection('users').createIndex({
      openid: 1
    }, {
      unique: true
    })
    console.log('用户集合索引创建成功')
    
    // 5. 创建对话记录集合索引
    await db.collection('conversations').createIndex({
      userId: 1,
      createdAt: -1
    })
    console.log('对话记录集合索引创建成功')
    
    // 6. 创建报告集合索引
    await db.collection('reports').createIndex({
      userId: 1,
      status: 1,
      createdAt: -1
    })
    console.log('报告集合索引创建成功')
    
    return {
      success: true,
      message: '数据库初始化成功'
    }
  } catch (error) {
    console.error('数据库初始化失败:', error)
    return {
      success: false,
      message: '数据库初始化失败',
      error: error.message
    }
  }
}