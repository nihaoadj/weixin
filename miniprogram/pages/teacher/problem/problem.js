// pages/teacher/problem/problem.js
Component({
  data: {
    currentStatus: 'pending',
    pendingCount: 0,
    problemList: [],
    allProblems: [],
    isLoading: false,
    page: 1,
    pageSize: 10,
    hasMore: true
  },

  lifetimes: {
    attached() {
      this.loadProblems();
    }
  },

  pageLifetimes: {
    show() {
      this.loadProblems();
    }
  },

  methods: {
    // 加载问题列表
    loadProblems() {
      wx.showLoading({ title: '正在加载问题...' });

      try {
        this.setData({ page: 1 });

        let problems = wx.getStorageSync('problems') || [];

        if (!Array.isArray(problems)) {
          problems = [];
        }

        const pendingCount = problems.filter(p => p && p.status === '待审核').length;

        this.setData({
          allProblems: problems,
          pendingCount
        });

        this.filterProblems(this.data.currentStatus);
        console.log('加载问题列表成功:', problems.length, '条问题');
      } catch (error) {
        console.error('加载问题列表失败:', error);
        this.setData({
          allProblems: [],
          problemList: []
        });
      } finally {
        wx.hideLoading();
      }
    },

    // 过滤问题
    filterProblems(status) {
      let filtered = [];

      if (status === 'pending') {
        filtered = this.data.allProblems.filter(p => p.status === '待审核');
      } else if (status === 'published') {
        filtered = this.data.allProblems.filter(p => p.status === '已发布');
      }

      filtered.sort((a, b) => new Date(b.time) - new Date(a.time));

      const pageData = filtered.slice(0, this.data.pageSize);

      this.setData({
        problemList: pageData,
        hasMore: filtered.length > this.data.pageSize
      });
    },

    // 切换状态
    switchStatus(e) {
      const status = e.currentTarget.dataset.status;
      this.setData({
        currentStatus: status,
        page: 1
      });
      this.filterProblems(status);
    },

    // 加载更多
    loadMoreProblems() {
      if (this.data.isLoading || !this.data.hasMore) return;

      this.setData({ isLoading: true });

      setTimeout(() => {
        const nextPage = this.data.page + 1;
        const start = (nextPage - 1) * this.data.pageSize;
        const end = nextPage * this.data.pageSize;

        let filtered = [];
        if (this.data.currentStatus === 'pending') {
          filtered = this.data.allProblems.filter(p => p.status === '待审核');
        } else if (this.data.currentStatus === 'published') {
          filtered = this.data.allProblems.filter(p => p.status === '已发布');
        }

        filtered.sort((a, b) => new Date(b.time) - new Date(a.time));

        const moreData = filtered.slice(start, end);

        if (moreData.length > 0) {
          this.setData({
            problemList: [...this.data.problemList, ...moreData],
            page: nextPage,
            hasMore: filtered.length > end
          });
        } else {
          this.setData({ hasMore: false });
        }

        this.setData({ isLoading: false });
      }, 500);
    },

    // 拒绝问题
    rejectProblem(e) {
      const id = e.currentTarget.dataset.id;

      wx.showModal({
        title: '确认拒绝',
        content: '确定要拒绝此问题吗？',
        success: (res) => {
          if (res.confirm) {
            const updatedProblems = this.data.allProblems.map(p => {
              if (p.id === id) {
                return { ...p, status: '已拒绝' };
              }
              return p;
            });

            wx.setStorageSync('problems', updatedProblems);

            this.setData({
              allProblems: updatedProblems,
              pendingCount: updatedProblems.filter(p => p.status === '待审核').length
            });

            this.filterProblems(this.data.currentStatus);

            wx.showToast({
              title: '已拒绝',
              icon: 'success'
            });
          }
        }
      });
    },

    // 编辑问题
    editProblem(e) {
      const id = e.currentTarget.dataset.id;
      const problem = this.data.allProblems.find(p => p.id === id);

      wx.navigateTo({
        url: `/pages/teacher/problem-edit/problem-edit?id=${id}&problem=${encodeURIComponent(JSON.stringify(problem))}`
      });
    },

    // 发布问题
    publishProblem(e) {
      const id = e.currentTarget.dataset.id;

      wx.showModal({
        title: '确认发布',
        content: '确定要发布此问题吗？',
        success: (res) => {
          if (res.confirm) {
            const now = new Date();
            const publishTime = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

            const updatedProblems = this.data.allProblems.map(p => {
              if (p.id === id) {
                return {
                  ...p,
                  status: '已发布',
                  publishTime
                };
              }
              return p;
            });

            wx.setStorageSync('problems', updatedProblems);

            this.setData({
              allProblems: updatedProblems,
              pendingCount: updatedProblems.filter(p => p.status === '待审核').length
            });

            this.filterProblems(this.data.currentStatus);

            wx.showToast({
              title: '发布成功',
              icon: 'success'
            });
          }
        }
      });
    },

    // 查看问题详情
    viewProblemDetail(e) {
      const id = e.currentTarget.dataset.id;
      wx.navigateTo({
        url: `/pages/teacher/problem-detail/problem-detail?id=${id}`
      });
    },

    // 查看统计
    viewStats(e) {
      const id = e.currentTarget.dataset.id;
      wx.navigateTo({
        url: `/pages/teacher/problem-stats/problem-stats?id=${id}`
      });
    },

    // 添加问题
    addProblem() {
      wx.navigateTo({
        url: '/pages/teacher/problem-edit/problem-edit'
      });
    },

    // 重置数据
    resetData() {
      wx.showModal({
        title: '确认重置',
        content: '确定要重置所有问题数据吗？',
        success: (res) => {
          if (res.confirm) {
            const now = new Date();
            const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

            const sampleProblems = [
              {
                id: 'prob_001',
                type: '医学常识',
                title: '肺炎的典型症状有哪些？',
                description: '请详细列举肺炎的主要临床症状和体征',
                target: 'all',
                status: '待审核',
                time: today
              },
              {
                id: 'prob_002',
                type: '病例分析',
                title: '高血压病例分析',
                description: '患者男性，55岁，血压160/100mmHg，有头痛、头晕症状。请分析诊断和治疗方案。',
                target: 'all',
                status: '待审核',
                time: today
              },
              {
                id: 'prob_003',
                type: '模拟诊疗',
                title: '发热咳嗽病例模拟诊疗',
                description: '医生，我身体不舒服...我发热3天了，体温一直在38度以上，咳嗽的时候胸口还有点疼，咳出来的痰是黄色的。这是怎么回事啊？',
                target: 'all',
                status: '待审核',
                time: today
              }
            ];

            wx.setStorageSync('problems', sampleProblems);
            wx.showToast({
              title: '已重置',
              icon: 'success'
            });

            setTimeout(() => {
              this.loadProblems();
            }, 1000);
          }
        }
      });
    },

    // 刷新方法（供父组件调用）
    refresh() {
      this.loadProblems();
    }
  }
});
