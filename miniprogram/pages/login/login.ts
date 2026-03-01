// pages/login/login.ts
Page({
  data: {
    isLoading: false
  },

  // 学生登录
  async loginAsStudent() {
    await this.login('student');
  },

  // 教师登录
  async loginAsTeacher() {
    await this.login('teacher');
  },

  // 微信授权登录
  async login(role: string) {
    try {
      this.setData({ isLoading: true });

      // 1. 微信授权登录
      const loginRes = await wx.login({
        timeout: 10000
      });

      if (!loginRes.code) {
        throw new Error('登录失败：无法获取登录凭证');
      }

      // 2. 获取用户信息
      const userInfoRes = await wx.getUserProfile({
        desc: '用于完善用户信息',
        lang: 'zh_CN'
      });

      // 3. 调用云函数进行登录
      const cloudRes = await wx.cloud.callFunction({
        name: 'login',
        data: {
          code: loginRes.code,
          userInfo: userInfoRes.userInfo,
          role
        }
      });

      // 检查云函数调用是否成功
      if (!cloudRes || !cloudRes.result) {
        throw new Error('云函数调用失败');
      }

      // 确保result是一个对象
      const result = cloudRes.result as any;

      if (!result.success) {
        throw new Error(result.message || '登录失败');
      }

      // 4. 存储用户信息到本地
      const userInfo = result.user;
      if (!userInfo) {
        throw new Error('用户信息获取失败');
      }
      wx.setStorageSync('userInfo', userInfo);
      wx.setStorageSync('role', role);
      wx.setStorageSync('openid', userInfo.openid);

      // 5. 根据角色跳转到对应页面
      if (role === 'student') {
        wx.redirectTo({ url: '/pages/student/chat/chat' });
      } else {
        wx.redirectTo({ url: '/pages/teacher/list/list' });
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
  }
});