// chat.js
Page({
  data: {
    messages: [],
    inputValue: '',
    lastMessageId: '',
    conversationId: '',
    isLoading: false
  },

  onLoad(options) {
    // 权限检查
    const role = wx.getStorageSync('role');
    if (role !== 'student') {
      wx.showToast({
        title: '无权限访问此页面',
        icon: 'none',
        duration: 2000
      });
      wx.navigateBack();
      return;
    }

    // 检查是否有对话ID参数
    const conversationId = options.conversationId;
    if (conversationId) {
      // 加载历史对话
      this.loadHistoryConversation(conversationId);
    } else {
      // 初始化新对话
      this.initConversation();
    }
  },

  // 初始化对话
  initConversation() {
    this.setData({
      conversationId: `conv_${Date.now()}`,
      messages: []
    });
  },

  // 快速提问
  quickAsk(e) {
    const question = e.currentTarget.dataset.question;
    if (question) {
      this.setData({
        inputValue: question
      });
      this.sendMessage();
    }
  },

  // 加载历史对话
  loadHistoryConversation(conversationId) {
    // 从本地存储加载历史对话
    const history = wx.getStorageSync('conversationHistory') || [];
    const conversation = history.find((item) => item.conversationId === conversationId);
    
    if (conversation) {
      this.setData({
        conversationId: conversation.conversationId,
        messages: conversation.messages
      });
    } else {
      // 对话不存在，初始化新对话
      this.initConversation();
    }
  },

  // 输入框内容变化
  onInputChange(e) {
    this.setData({
      inputValue: e.detail.value
    });
  },

  // 发送消息
  sendMessage() {
    const { inputValue, messages, conversationId } = this.data;
    
    if (!inputValue.trim()) return;

    // 添加用户消息
    const userMessage = {
      role: 'user',
      content: inputValue.trim(),
      timestamp: this.formatTime(new Date())
    };

    const newMessages = [...messages, userMessage];
    this.setData({
      messages: newMessages,
      inputValue: '',
      lastMessageId: `msg_${newMessages.length - 1}`
    });

    // 调用AI API获取回复
    this.getAIResponse(inputValue.trim(), conversationId);
  },

  // 调用AI API获取回复
  getAIResponse(userInput, conversationId) {
    this.setData({ isLoading: true });

    // 这里使用DeepSeek V3.2大模型API
    this.callDeepSeekAPI(userInput).then(response => {
      // 添加AI回复
      const aiMessage = {
        role: 'assistant',
        content: response,
        timestamp: this.formatTime(new Date())
      };

      const newMessages = [...this.data.messages, aiMessage];
      this.setData({
        messages: newMessages,
        lastMessageId: `msg_${newMessages.length - 1}`,
        isLoading: false
      });

      // 存储对话记录到本地
      this.saveConversation(newMessages, conversationId);
    }).catch(error => {
      console.error('AI回复失败:', error);
      this.setData({ isLoading: false });
      
      // 添加错误消息
      const errorMessage = {
        role: 'assistant',
        content: '抱歉，AI服务暂时不可用，请稍后再试',
        timestamp: this.formatTime(new Date())
      };

      const newMessages = [...this.data.messages, errorMessage];
      this.setData({
        messages: newMessages,
        lastMessageId: `msg_${newMessages.length - 1}`
      });
    });
  },

  // 调用DeepSeek V3.2大模型API
  callDeepSeekAPI(prompt) {
    return new Promise((resolve, reject) => {
      // DeepSeek V3.2大模型API调用
      const API_KEY = ''; // 安全起见不在客户端保存密钥；生产环境必须通过服务端调用
      const API_URL = 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'; // DeepSeek API地址
      const MODEL = 'ep-20260203151007-9brbk'; // DeepSeek V3.2模型
      
      try {
        // 检查API密钥是否设置
        if (API_KEY === '') {
          // API密钥未设置，返回错误
          reject(new Error('API密钥未设置，请在代码中配置实际的API密钥'));
          return;
        }

        // 构建请求参数
        const requestData = {
          model: MODEL,
          messages: [
            {
              role: 'system',
              content: '你是一个医学知识问答助手，专注于回答医学相关的问题，提供准确、专业的医学知识。'
            },
            {
              role: 'user',
              content: prompt
            }
          ],
          temperature: 0.7,
          max_tokens: 1024
        };

        // 发送请求
        wx.request({
          url: API_URL,
          method: 'POST',
          header: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${API_KEY}`
          },
          data: requestData,
          success: (response) => {
            if (response.statusCode === 200 && response.data && response.data.choices) {
              resolve(response.data.choices[0].message.content);
            } else {
              // 处理API密钥无效的情况
              if (response.statusCode === 401 && response.data?.error?.message?.includes('Authentication Fails')) {
                reject(new Error('API密钥无效，请检查并更新API密钥'));
              } else {
                reject(new Error(`API调用失败: ${response.statusCode} - ${response.data?.error?.message || '未知错误'}`));
              }
            }
          },
          fail: (error) => {
            reject(error);
          }
        });
      } catch (error) {
        console.error('DeepSeek API调用失败:', error);
        reject(error);
      }
    });
  },

  // 结束对话并生成报告
  endConversation() {
    const { messages, conversationId } = this.data;
    
    if (messages.length === 0) return;

    wx.showLoading({ title: '正在生成报告...' });

    // 1. 分析对话内容
    const analysisResult = this.analyzeConversation(messages);

    // 2. 生成报告
    const report = {
      conversationId,
      messages,
      analysis: analysisResult,
      createdAt: new Date().toISOString()
    };

    // 3. 存储报告到本地
    this.saveReport(report);

    // 4. 存储对话记录到本地
    this.saveConversation(messages, conversationId);

    // 5. 跳转到报告页面
    wx.hideLoading();
    wx.navigateTo({
      url: `/pages/report/report?conversationId=${conversationId}`
    });
  },

  // 分析对话内容
  analyzeConversation(messages) {
    // 提取学生的问题和回答
    const studentMessages = messages.filter(msg => msg.role === 'user');
    
    // 分析学生回答中的知识点错误和逻辑漏洞
    // 这里使用模拟分析，实际开发中可以使用AI模型进行更深入的分析
    const errors = this.detectErrors(studentMessages);
    
    // 计算得分
    const score = this.calculateScore(errors, studentMessages.length);
    
    // 生成总结
    const summary = this.generateSummary(errors, score);
    
    return {
      errors,
      score,
      summary
    };
  },

  // 检测错误
  detectErrors(studentMessages) {
    // 模拟错误检测，实际开发中需要根据医学知识进行更准确的检测
    const errors = [];
    
    // 示例：检测医学术语使用是否准确
    if (studentMessages.some(msg => msg.content.includes('肺炎') && !msg.content.includes('病原体'))) {
      errors.push({
        content: '部分医学术语使用不准确，如在描述肺炎时未提及病原体类型',
        suggestion: '建议参考最新版医学教材中的术语定义，在描述疾病时应包含病原体、病理生理等关键信息'
      });
    }
    
    // 示例：检测病理机制解释是否完整
    if (studentMessages.some(msg => msg.content.includes('治疗') && !msg.content.includes('副作用'))) {
      errors.push({
        content: '治疗方案描述不完整，未提及可能的副作用',
        suggestion: '建议在描述治疗方案时，应包括药物名称、剂量、疗程以及可能的副作用和注意事项'
      });
    }
    
    // 示例：检测临床症状描述是否全面
    if (studentMessages.some(msg => msg.content.includes('症状') && msg.content.split('，').length < 3)) {
      errors.push({
        content: '临床症状描述不够全面',
        suggestion: '建议从主观症状、客观体征等多个方面全面描述疾病的临床表现'
      });
    }
    
    // 如果没有检测到错误，添加一个默认的正面评价
    if (errors.length === 0) {
      errors.push({
        content: '未检测到明显错误',
        suggestion: '继续保持，建议进一步拓展相关知识点的学习'
      });
    }
    
    return errors;
  },

  // 计算得分
  calculateScore(errors, messageCount) {
    // 基础分
    let baseScore = 90;
    
    // 根据错误数量扣分
    const errorPenalty = errors.length * 5;
    
    // 根据对话长度加分
    const lengthBonus = Math.min(messageCount * 2, 10);
    
    // 计算最终得分
    let finalScore = baseScore - errorPenalty + lengthBonus;
    
    // 确保得分在0-100之间
    finalScore = Math.max(0, Math.min(100, finalScore));
    
    return finalScore;
  },

  // 生成总结
  generateSummary(_errors, score) {
    if (score >= 90) {
      return '表现优秀，医学知识掌握扎实，逻辑清晰，建议继续深入学习前沿医学知识。';
    } else if (score >= 70) {
      return '表现良好，医学知识掌握基本到位，但仍有一些细节需要注意，建议加强知识点的系统性学习。';
    } else if (score >= 60) {
      return '表现一般，医学知识掌握不够扎实，存在一些概念性错误，建议重点复习基础医学知识。';
    } else {
      return '表现较差，医学知识掌握存在较多问题，建议重新学习相关章节内容，并多做练习巩固。';
    }
  },

  // 存储对话记录
  saveConversation(messages, conversationId) {
    // 这里使用本地存储作为临时解决方案
    // 实际开发中需要存储到微信云数据库
    const history = wx.getStorageSync('conversationHistory') || [];
    history.unshift({
      conversationId,
      messages,
      createdAt: new Date().toISOString()
    });
    // 只保留最近10条对话
    if (history.length > 10) {
      history.splice(10);
    }
    wx.setStorageSync('conversationHistory', history);
  },

  // 存储报告到数据库
  saveReport(report) {
    // 这里使用本地存储作为临时解决方案
    // 实际开发中需要存储到微信云数据库
    const reports = wx.getStorageSync('reports') || [];
    reports.push(report);
    wx.setStorageSync('reports', reports);
  },

  // 加载更多历史消息
  loadMoreHistory() {
    // 这里可以实现加载更多历史消息的逻辑
  },

  // 跳转到历史记录页面
  goToHistory() {
    wx.navigateTo({
      url: '/pages/student/history/history'
    });
  },

  // 跳转到问题页面
  goToQuestion() {
    wx.navigateTo({
      url: '/pages/student/question/question'
    });
  },

  // 格式化时间
  formatTime(date) {
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  }
});
