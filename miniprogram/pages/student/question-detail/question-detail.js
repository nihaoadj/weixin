// question-detail.js
Page({
  data: {
    question: {},
    answer: '',
    messages: [],
    isLoading: false,
    lastMessageId: ''
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

    // 获取问题ID
    const questionId = options.id;
    if (questionId) {
      // 加载问题详情
      this.loadQuestionDetail(questionId);
    }
  },

  // 加载问题详情
  loadQuestionDetail(questionId) {
    // 模拟问题数据，实际开发中应从服务器获取
    const questions = [
      {
        id: '1',
        title: '肺炎的典型症状有哪些？',
        type: '医学常识',
        time: '2026-03-08',
        status: '未回答'
      },
      {
        id: '2',
        title: '高血压的诊断标准是什么？',
        type: '医学常识',
        time: '2026-03-07',
        status: '未回答'
      },
      {
        id: '3',
        title: '糖尿病的并发症有哪些？',
        type: '医学常识',
        time: '2026-03-06',
        status: '未回答'
      },
      {
        id: '4',
        title: '医生您好，我今年65岁，从2小时前开始胸口就有点疼，像压了块石头似的，一直没缓解，我有点担心，这是怎么回事啊？',
        type: '模拟诊疗',
        time: '2026-03-05',
        status: '未回答'
      },
      {
        id: '5',
        title: '分析急性阑尾炎的诊断思路和治疗方案',
        type: '病例分析',
        time: '2026-03-04',
        status: '未回答'
      },
      {
        id: '6',
        title: '医生，我45岁，最近不知道怎么回事，总是特别渴，老想喝水，尿也特别多，而且这段时间体重掉了不少，我是不是得了什么病啊？',
        type: '模拟诊疗',
        time: '2026-03-02',
        status: '未回答'
      }
    ];

    const question = questions.find(q => q.id === questionId);
    if (question) {
      this.setData({
        question
      });
    } else {
      wx.showToast({
        title: '问题不存在',
        icon: 'none',
        duration: 2000
      });
      wx.navigateBack();
    }
  },

  // 返回上一页
  goBack() {
    wx.navigateBack();
  },

  // 回答内容变化
  onAnswerChange(e) {
    this.setData({
      answer: e.detail.value
    });
  },

  // 提交回答给AI解析
  submitAnswer() {
    const { question, answer, messages } = this.data;

    if (!answer.trim()) return;

    // 添加用户消息
    const userMessage = {
      role: 'user',
      content: answer.trim()
    };

    const newMessages = [...messages, userMessage];
    this.setData({
      messages: newMessages,
      answer: '',
      lastMessageId: `msg_${newMessages.length - 1}`,
      isLoading: true
    });

    // 调用AI API解析回答，传递完整对话历史
    this.callAIAPI(question, newMessages).then(analysis => {
      // 添加AI回复
      const aiMessage = {
        role: 'assistant',
        content: analysis
      };

      const updatedMessages = [...newMessages, aiMessage];
      this.setData({
        messages: updatedMessages,
        lastMessageId: `msg_${updatedMessages.length - 1}`,
        isLoading: false
      });
    }).catch(error => {
      // 添加错误消息
      const errorMessage = {
        role: 'assistant',
        content: '抱歉，AI解析失败，请稍后再试'
      };

      const updatedMessages = [...newMessages, errorMessage];
      this.setData({
        messages: updatedMessages,
        lastMessageId: `msg_${updatedMessages.length - 1}`,
        isLoading: false
      });
      console.error('AI解析失败:', error);
    });
  },

  // 构建系统提示词
  getSystemPrompt(questionType) {
    const prompts = {
      '医学常识': '你是一个医学知识问答助手，专注于回答医学常识问题，提供专业、准确的医学知识解答。在回答时，请结合临床实际，用通俗易懂的语言解释医学概念，并适当举例说明。',
      '模拟诊疗': '你是一个模拟患者（经验丰富的临床医生扮演），需要扮演一个患病的病人与学生进行多轮模拟问诊。请根据学生的提问，逐步提供症状信息，引导学生进行诊断。当学生完成诊断后，对其整体的诊断思路、问诊流程、诊断结论进行全面分析和总结评价。请注意保持角色，一直等到学生做出明确诊断后再进行总结。',
      '病例分析': '你是一个医学教育专家，专注于分析学生的病例分析能力。根据学生提供的病例分析回答，你需要：1. 判断学生的回答是否正确；2. 指出可能的错误或不足之处；3. 提供专业的改进建议；4. 给出正确的分析思路和结论。请始终保持专业、客观的评价态度。'
    };
    return prompts[questionType] || prompts['医学常识'];
  },

  // 调用AI API解析回答（支持多轮对话）
  callAIAPI(question, messages) {
    return new Promise((resolve, reject) => {
      // DeepSeek V3.2大模型API调用
      const API_KEY = ''; // 安全起见不在客户端保存密钥；生产环境必须通过服务端调用
      const API_URL = 'https://ark.cn-beijing.volces.com/api/v3/chat/completions';
      const MODEL = 'ep-20260203151007-9brbk';

      try {
        if (API_KEY === '') {
          reject(new Error('API密钥未设置，请在代码中配置实际的API密钥'));
          return;
        }

        // 构建对话历史消息
        const conversationMessages = messages.map(msg => ({
          role: msg.role,
          content: msg.content
        }));

        // 添加系统提示词
        const systemPrompt = this.getSystemPrompt(question.type);

        // 构建API请求的messages数组
        const requestMessages = [
          {
            role: 'system',
            content: systemPrompt
          },
          {
            role: 'user',
            content: `【问题】\n类型：${question.type}\n标题：${question.title}\n\n请基于以上问题，与我进行对话。`
          }
        ];

        // 将历史对话添加到messages中
        const allMessages = [...requestMessages, ...conversationMessages];

        const requestData = {
          model: MODEL,
          messages: allMessages,
          temperature: 0.7,
          max_tokens: 2048
        };

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
        console.error('AI API调用失败:', error);
        reject(error);
      }
    });
  }
});
