// cloudfunctions/getReport/index.js
const cloud = require('wx-server-sdk')

// 初始化云开发环境
cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()
const _ = db.command

exports.main = async (event, context) => {
  try {
    const { openid, role, reportId } = event
    
    if (reportId) {
      // 获取单个报告详情
      const reportRes = await db.collection('reports').doc(reportId).get()
      
      if (!reportRes.data) {
        return {
          success: false,
          message: '报告不存在'
        }
      }
      
      // 权限检查
      if (role === 'student' && reportRes.data.userId !== openid) {
        return {
          success: false,
          message: '无权限查看此报告'
        }
      }
      
      return {
        success: true,
        report: reportRes.data
      }
    } else {
      // 获取报告列表
      let query = db.collection('reports')
      
      if (role === 'student') {
        // 学生只能查看自己的报告
        query = query.where({
          userId: openid
        })
      } else if (role === 'teacher') {
        // 教师可以查看所有待批阅的报告
        query = query.where({
          status: '待批阅'
        })
      }
      
      // 按创建时间倒序排列
      const reportsRes = await query.orderBy('createdAt', 'desc').get()
      
      return {
        success: true,
        reports: reportsRes.data
      }
    }
  } catch (error) {
    console.error('获取报告失败:', error)
    return {
      success: false,
      message: '获取报告失败',
      error: error.message
    }
  }
}