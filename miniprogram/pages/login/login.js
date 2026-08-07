// login.js
Page({
  data: {
    isLoading: false
  },

  // 学生登录
  loginAsStudent() {
    this.handleLogin('student');
  },

  // 教师登录
  loginAsTeacher() {
    this.handleLogin('teacher');
  },

  // 处理登录
  handleLogin(role) {
    // 1. 首先获取用户信息（必须在点击事件直接回调中调用）
    wx.getUserProfile({
      desc: '用于完善用户信息',
      lang: 'zh_CN',
      success: async (userInfoRes) => {
        try {
          this.setData({ isLoading: true });

          // 2. 获取微信登录凭证
          const loginRes = await wx.login({
            timeout: 10000
          });

          if (!loginRes.code) {
            throw new Error('登录失败：无法获取登录凭证');
          }

          // 3. 直接在前端处理登录逻辑（绕过云函数）
          // 模拟登录成功
          const userInfo = {
            openid: 'mock_openid_' + Date.now(),
            role: role,
            avatarUrl: userInfoRes.userInfo.avatarUrl,
            nickName: userInfoRes.userInfo.nickName,
            createdAt: new Date(),
            updatedAt: new Date()
          };

          // 4. 存储用户信息到本地
          wx.setStorageSync('userInfo', userInfo);
          wx.setStorageSync('role', role);
          wx.setStorageSync('openid', userInfo.openid);

          // 5. 根据角色跳转到对应页面
          if (role === 'student') {
            wx.redirectTo({ url: '/pages/student/chat/chat' });
          } else {
            wx.redirectTo({ url: '/pages/teacher/index/index' });
          }
        } catch (error) {
          console.error('登录失败:', error);
          wx.showToast({
            title: '登录失败，请重试',
            icon: 'none',
            duration: 2000
          });
        } finally {
          this.setData({ isLoading: false });
        }
      },
      fail: (error) => {
        console.error('获取用户信息失败:', error);
        wx.showToast({
          title: '授权失败，请重试',
          icon: 'none',
          duration: 2000
        });
      }
    });
  }
});