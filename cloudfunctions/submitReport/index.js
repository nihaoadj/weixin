// cloudfunctions/submitReport/index.js
const cloud = require('wx-server-sdk')

// 初始化云开发环境
cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()
const _ = db.command

exports.main = async (event, context) => {
  try {
    const { openid, role, reportData, reportId, teacherScore, teacherFeedback } = event
    
    if (role === 'student' && reportData) {
      // 学生提交报告
      const addRes = await db.collection('reports').add({
        data: {
          userId: openid,
          conversationId: reportData.conversationId,
          messages: reportData.messages,
          analysis: reportData.analysis,
          status: '待批阅',
          createdAt: new Date(),
          updatedAt: new Date()
        }
      })
      
      return {
        success: true,
        reportId: addRes._id
      }
    } else if (role === 'teacher' && reportId && teacherScore) {
      // 教师批阅报告
      const updateRes = await db.collection('reports').doc(reportId).update({
        data: {
          status: '已批阅',
          teacherScore,
          teacherFeedback,
          updatedAt: new Date()
        }
      })
      
      if (updateRes.stats.updated === 0) {
        return {
          success: false,
          message: '报告不存在或已被批阅'
        }
      }
      
      return {
        success: true,
        message: '批阅成功'
      }
    } else {
      return {
        success: false,
        message: '参数错误'
      }
    }
  } catch (error) {
    console.error('提交报告失败:', error)
    return {
      success: false,
      message: '提交报告失败',
      error: error.message
    }
  }
}