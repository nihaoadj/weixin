// index.ts
// 获取应用实例
const app = getApp<IAppOption>()

Page({
  data: {},
  
  onLoad() {
    // 检查是否已登录
    const userInfo = wx.getStorageSync('userInfo');
    const role = wx.getStorageSync('role');
    
    if (userInfo && role) {
      // 已登录，根据角色跳转到对应页面
      if (role === 'student') {
        wx.redirectTo({ url: '/pages/student/chat/chat' });
      } else {
        wx.redirectTo({ url: '/pages/teacher/list/list' });
      }
    } else {
      // 未登录，跳转到登录页面
      wx.redirectTo({ url: '/pages/login/login' });
    }
  },
})
