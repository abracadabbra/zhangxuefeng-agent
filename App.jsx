import { useState, useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';

/* ─── EDITMODE TWEAKS ─── */
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accentColor": "#ffa000",
  "surfaceRadius": "16px",
  "chatBubbleRadius": "18px",
  "darkMode": false
}/*EDITMODE-END*/;

/* ─── DESIGN TOKENS ─── */
const C = {
  indigo900: '#1a237e',
  indigo800: '#283593',
  indigo700: '#303f9f',
  indigo600: '#3949ab',
  indigo100: '#c5cae9',
  indigo50: '#e8eaf6',
  amber700: '#ffa000',
  amber600: '#ffb300',
  amber500: '#ffc107',
  amber100: '#ffecb3',
  amber50: '#fff8e1',
  surface: '#fefdfb',
  surfaceAlt: '#f5f0ea',
  text: '#1c1917',
  textMuted: '#57534e',
  textLight: '#a8a29e',
  border: '#e7e5e4',
  white: '#ffffff',
  success: '#2e7d32',
  error: '#c62828',
  green50: '#e8f5e9',
  blue50: '#e3f2fd',
};

const FONT = "'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', Georgia, serif";
const FONT_SANS = "'Noto Sans SC', 'Source Han Sans SC', 'PingFang SC', -apple-system, sans-serif";

/* ─── GRAIN OVERLAY SVG ─── */
const GRAIN_SVG = `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E")`;

/* ─── ICON COMPONENTS ─── */
function IconGraduation() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
      <path d="M6 12v5c0 2 4 3 6 3s6-1 6-3v-5"/>
    </svg>
  );
}

function IconBook() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>
      <path d="M8 7h6"/>
      <path d="M8 11h8"/>
    </svg>
  );
}

function IconBriefcase() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2"/>
      <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>
      <path d="M12 12v2"/>
    </svg>
  );
}

function IconArrow() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14"/>
      <path d="m12 5 7 7-7 7"/>
    </svg>
  );
}

function IconBack() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m15 18-6-6 6-6"/>
    </svg>
  );
}

function IconData() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2"/>
      <path d="M8 16V12"/>
      <path d="M12 16V8"/>
      <path d="M16 16v-2"/>
    </svg>
  );
}

function IconChat() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  );
}

function IconSend() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
    </svg>
  );
}

function IconBrain() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a4 4 0 0 0-4 4c0 .74.2 1.43.56 2.03A4 4 0 0 0 5 12c0 .74.2 1.43.56 2.03A4 4 0 0 0 6 18a4 4 0 0 0 4 4h4a4 4 0 0 0 4-4 4 4 0 0 0-.56-2.03A4 4 0 0 0 19 12a4 4 0 0 0-3.56-3.97A4 4 0 0 0 16 6a4 4 0 0 0-4-4z"/>
      <path d="M12 2v20"/>
    </svg>
  );
}

/* ─── MOCK DATA ─── */
const SCENARIOS = [
  {
    id: 'gaokao',
    title: '高考志愿填报',
    subtitle: '用数据说话，不让你踩坑',
    desc: '基于你的分数、省份和偏好，给出最务实的志愿方案。985/211/专业优先，哪个适合你，我帮你算清楚。',
    icon: IconGraduation,
    color: C.indigo800,
    gradient: `linear-gradient(135deg, ${C.indigo900}, ${C.indigo700})`,
    questions: [
      { key: 'province', label: '你是哪个省的？', placeholder: '例：山东、河南、广东', type: 'text' },
      { key: 'score', label: '你考了多少分？', placeholder: '输入你的高考总分', type: 'number' },
      { key: 'category', label: '文理科/选科是什么？', placeholder: '例：物理类、历史类、理科', type: 'text' },
      { key: 'familyBudget', label: '家里经济条件怎么样？', placeholder: '我能告诉你该不该出省', type: 'select', options: ['年收入10万以下', '年收入10-30万', '年收入30万以上'] },
      { key: 'priority', label: '你最看重什么？', placeholder: '', type: 'select', options: ['学校名气（985/211优先）', '专业实力（王牌专业优先）', '就业前景（好找工作优先）', '城市位置（想去大城市）'] },
    ]
  },
  {
    id: 'kaoyan',
    title: '考研择校规划',
    subtitle: '选对学校，少走三年弯路',
    desc: '考研不是高考，信息差才是最大的敌人。院校报录比、导师资源、就业数据，我帮你全部查清楚。',
    icon: IconBook,
    color: C.amber700,
    gradient: `linear-gradient(135deg, ${C.amber700}, #e65100)`,
    questions: [
      { key: 'undergraduate', label: '你本科哪个学校什么专业？', placeholder: '例：XX大学 计算机科学', type: 'text' },
      { key: 'gpa', label: '本科成绩大概什么水平？', placeholder: '绩点或排名', type: 'text' },
      { key: 'targetMajor', label: '想考什么方向的研究生？', placeholder: '可以跨考，但要想清楚', type: 'text' },
      { key: 'targetSchool', label: '有目标院校吗？', placeholder: '没有也行，我帮你选', type: 'text' },
      { key: 'priority', label: '你最看重什么？', placeholder: '', type: 'select', options: ['学校层次（非985不去）', '专业排名（学科实力强）', '就业前景（毕业好找工作）', '容易上岸（求稳）'] },
    ]
  },
  {
    id: 'career',
    title: '职业发展规划',
    subtitle: '别被"兴趣"骗了，先看市场需求',
    desc: '你以为的热门可能已经饱和了。行业趋势、薪资数据、真实就业率，用数据帮你做最理性的选择。',
    icon: IconBriefcase,
    color: '#2e7d32',
    gradient: 'linear-gradient(135deg, #1b5e20, #2e7d32)',
    questions: [
      { key: 'education', label: '你现在的学历和专业是什么？', placeholder: '例：本科 市场营销', type: 'text' },
      { key: 'stage', label: '你现在处于什么阶段？', placeholder: '', type: 'select', options: ['在校大学生', '应届毕业生', '工作1-3年', '工作3年以上'] },
      { key: 'interest', label: '你对什么方向感兴趣？', placeholder: '可以说具体一点', type: 'text' },
      { key: 'concern', label: '你最担心什么？', placeholder: '', type: 'select', options: ['找不到工作', '薪资太低', '行业没前途', '不确定该转行还是坚持'] },
    ]
  },
];

const CHAT_MESSAGES_GAOKAO = [
  {
    role: 'assistant',
    content: '同学你好，我是你的高考志愿咨询师。\n\n我看了你的信息：**山东考生，物理类，620分**。先说结论：这个分数在山东不算特别有优势，但也绝对不差。\n\n在给你方案之前，我要先问你一个灵魂问题：\n\n**你家里经济条件怎么样？能不能接受你出省？**\n\n这个问题很关键，因为它直接决定你的选择范围。',
    sources: [
      { title: '2024年山东省高考一分一段表', url: '#', freshness: '2024年数据' },
      { title: '山东省2024年本科批次线', url: '#', freshness: '438分（一段线）' },
    ],
    toolCall: { name: 'search_admission_data', args: '{"province":"山东","year":2024,"category":"物理类"}' },
  },
  {
    role: 'user',
    content: '家里条件一般，能出省但不想去太远的地方。',
  },
  {
    role: 'assistant',
    content: '明白了。条件一般、不想出远门，那我帮你把范围缩到**华东地区**。\n\n给你三个梯队的方案：\n\n**第一梯队（冲一冲）：**\n- 合肥工业大学 · 计算机科学（去年投档线625）\n- 南京邮电大学 · 通信工程（去年投档线622）\n\n**第二梯队（稳一稳）：**\n- 山东大学 · 软件工程（去年投档线615）\n- 中国海洋大学 · 计算机（去年投档线612）\n\n**第三梯队（保底）：**\n- 济南大学 · 计算机科学（去年投档线598）\n\n⚠️ **提醒你一句：** 今年山东物理类600分以上人数比去年多了3000多人，所以你的位次比分数更重要。\n\n你想深入了解哪个学校？我可以给你查详细的就业数据。',
    sources: [
      { title: '华东地区211高校2024年山东投档线汇总', url: '#', freshness: '2024年数据' },
      { title: '2024年山东高考物理类一分一段表', url: '#', freshness: '2024年6月' },
      { title: '计算机科学与技术专业就业质量报告', url: '#', freshness: '2024年' },
    ],
  },
];

/* ─── MAIN APP ─── */
function App() {
  const [screen, setScreen] = useState('home'); // home | form | chat
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [formStep, setFormStep] = useState(0);
  const [formData, setFormData] = useState({});
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isTyping]);

  function handleScenarioSelect(scenario) {
    setSelectedScenario(scenario);
    setFormStep(0);
    setFormData({});
    setScreen('form');
  }

  function handleFormNext(value) {
    const scenario = selectedScenario;
    const currentQ = scenario.questions[formStep];
    setFormData(prev => ({ ...prev, [currentQ.key]: value }));

    if (formStep < scenario.questions.length - 1) {
      setFormStep(prev => prev + 1);
    } else {
      // Go to chat with mock messages
      setChatMessages(CHAT_MESSAGES_GAOKAO);
      setScreen('chat');
    }
  }

  function handleSendMessage() {
    if (!chatInput.trim()) return;
    const userMsg = { role: 'user', content: chatInput };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput('');
    setIsTyping(true);

    // Simulate assistant reply
    setTimeout(() => {
      setIsTyping(false);
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: '我理解你的问题。让我先查一下相关的数据……\n\n基于我掌握的信息，有几个关键点你需要知道：\n\n1. **数据不会说谎**——我会基于真实录取数据给你分析\n2. **没有完美的选择**——但有最适合你情况的选择\n3. **我的建议可能不好听**——但都是为你好\n\n你想从哪个方面开始聊？',
        sources: [
          { title: '全国高校2024年录取数据', url: '#', freshness: '2024年更新' },
        ],
      }]);
    }, 2000);
  }

  return (
    <div style={{
      '--accent': TWEAK_DEFAULTS.accentColor,
      '--radius': TWEAK_DEFAULTS.surfaceRadius,
      '--chat-radius': TWEAK_DEFAULTS.chatBubbleRadius,
    }}>
      <style>{GLOBAL_CSS}</style>

      {/* ── HOMEPAGE ── */}
      {screen === 'home' && (
        <HomePage onSelect={handleScenarioSelect} />
      )}

      {/* ── FORM ── */}
      {screen === 'form' && selectedScenario && (
        <FormScreen
          scenario={selectedScenario}
          step={formStep}
          formData={formData}
          onNext={handleFormNext}
          onBack={() => {
            if (formStep > 0) setFormStep(prev => prev - 1);
            else setScreen('home');
          }}
        />
      )}

      {/* ── CHAT ── */}
      {screen === 'chat' && (
        <ChatScreen
          scenario={selectedScenario}
          messages={chatMessages}
          input={chatInput}
          setInput={setChatInput}
          onSend={handleSendMessage}
          isTyping={isTyping}
          chatEndRef={chatEndRef}
          onBack={() => setScreen('home')}
          formData={formData}
        />
      )}
    </div>
  );
}

/* ─── HOMEPAGE ─── */
function HomePage({ onSelect }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => { requestAnimationFrame(() => setVisible(true)); }, []);

  return (
    <div className="home-root">
      {/* Hero */}
      <header className="home-hero">
        <div className="home-hero-grain" />
        <div className="home-hero-inner">
          <div className={`home-hero-content ${visible ? 'visible' : ''}`}>
            <div className="home-badge">
              <IconBrain />
              <span>基于真实数据的 AI 咨询</span>
            </div>
            <h1 className="home-title">
              <span className="home-title-amp">「</span>
              先查数据，再下判断
              <span className="home-title-amp">」</span>
            </h1>
            <p className="home-subtitle">
              我不是那种给你一堆信息让你自己选的 AI。<br />
              我会根据你的具体情况，<strong>直接告诉你该怎么做</strong>。
            </p>

            <div className="home-stats">
              <div className="home-stat">
                <span className="home-stat-num">3,200+</span>
                <span className="home-stat-label">高校数据</span>
              </div>
              <div className="home-stat-divider" />
              <div className="home-stat">
                <span className="home-stat-num">800+</span>
                <span className="home-stat-label">专业覆盖</span>
              </div>
              <div className="home-stat-divider" />
              <div className="home-stat">
                <span className="home-stat-num">31省</span>
                <span className="home-stat-label">录取数据</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Scenario Cards */}
      <section className="home-scenarios">
        <div className="home-scenarios-inner">
          <h2 className="home-section-title">选择你的咨询场景</h2>
          <p className="home-section-desc">不同场景，不同的灵魂追问。选一个开始吧。</p>

          <div className="home-cards">
            {SCENARIOS.map((s, i) => (
              <button
                key={s.id}
                className="home-card"
                style={{ animationDelay: `${200 + i * 120}ms` }}
                onClick={() => onSelect(s)}
              >
                <div className="home-card-icon" style={{ background: s.gradient }}>
                  <s.icon />
                </div>
                <div className="home-card-body">
                  <h3 className="home-card-title">{s.title}</h3>
                  <p className="home-card-subtitle">{s.subtitle}</p>
                  <p className="home-card-desc">{s.desc}</p>
                </div>
                <div className="home-card-arrow">
                  <IconArrow />
                </div>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Trust Section */}
      <section className="home-trust">
        <div className="home-trust-inner">
          <div className="home-trust-item">
            <IconData />
            <h3>数据驱动</h3>
            <p>每一条建议都有数据支撑，不靠经验主义。</p>
          </div>
          <div className="home-trust-item">
            <IconChat />
            <h3>说真话</h3>
            <p>可能不好听，但都是为了你的前途着想。</p>
          </div>
          <div className="home-trust-item">
            <IconBrain />
            <h3>灵魂追问</h3>
            <p>不问清楚你的情况，我不会随便给建议。</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="home-footer">
        <p>基于真实高校数据 · 不是随便给你一堆信息让你自己选</p>
      </footer>
    </div>
  );
}

/* ─── FORM SCREEN (SOUL QUESTIONS) ─── */
function FormScreen({ scenario, step, formData, onNext, onBack }) {
  const [inputValue, setInputValue] = useState('');
  const [selectedOption, setSelectedOption] = useState('');
  const question = scenario.questions[step];
  const totalSteps = scenario.questions.length;
  const progress = ((step + 1) / totalSteps) * 100;

  function handleSubmit(e) {
    e.preventDefault();
    const value = question.type === 'select' ? selectedOption : inputValue;
    if (!value.trim()) return;
    onNext(value);
    setInputValue('');
    setSelectedOption('');
  }

  const Icon = scenario.icon;

  return (
    <div className="form-root">
      <div className="form-container">
        {/* Header */}
        <div className="form-header">
          <button className="form-back-btn" onClick={onBack}>
            <IconBack />
            <span>返回</span>
          </button>
          <div className="form-header-title">
            <div className="form-header-icon" style={{ background: scenario.gradient }}>
              <Icon />
            </div>
            <span>{scenario.title}</span>
          </div>
          <div className="form-step-count">{step + 1}/{totalSteps}</div>
        </div>

        {/* Progress */}
        <div className="form-progress-track">
          <div className="form-progress-fill" style={{ width: `${progress}%`, background: scenario.gradient }} />
        </div>

        {/* Question */}
        <div className="form-question-area">
          <div className="form-question-number" style={{ color: scenario.color }}>
            问题 {step + 1}
          </div>
          <h2 className="form-question-text">{question.label}</h2>
          <p className="form-question-hint">
            {step === 0 ? '我需要了解你的基本情况，才能给出靠谱的建议。' : '继续，快了。'}
          </p>
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="form-input-area">
          {question.type === 'select' ? (
            <div className="form-options">
              {question.options.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  className={`form-option ${selectedOption === opt ? 'selected' : ''}`}
                  onClick={() => { setSelectedOption(opt); }}
                  style={selectedOption === opt ? { borderColor: scenario.color, background: `${scenario.color}08` } : {}}
                >
                  <span className="form-option-radio" style={selectedOption === opt ? { background: scenario.color, borderColor: scenario.color } : {}} />
                  {opt}
                </button>
              ))}
            </div>
          ) : (
            <div className="form-input-wrapper">
              <input
                type={question.type === 'number' ? 'number' : 'text'}
                className="form-input"
                placeholder={question.placeholder}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                autoFocus
              />
            </div>
          )}

          <button
            type="submit"
            className="form-submit-btn"
            disabled={question.type === 'select' ? !selectedOption : !inputValue.trim()}
            style={{ background: scenario.gradient }}
          >
            {step < totalSteps - 1 ? '下一个问题' : '开始咨询'}
            <IconArrow />
          </button>
        </form>

        {/* Collected answers */}
        {Object.keys(formData).length > 0 && (
          <div className="form-answers">
            <div className="form-answers-title">已收集的信息：</div>
            <div className="form-answers-chips">
              {Object.entries(formData).map(([key, val]) => {
                const q = scenario.questions.find(q => q.key === key);
                return (
                  <span key={key} className="form-chip">
                    {q?.label.replace('？', '')}：<strong>{val}</strong>
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── CHAT SCREEN ─── */
function ChatScreen({ scenario, messages, input, setInput, onSend, isTyping, chatEndRef, onBack, formData }) {
  const Icon = scenario?.icon || IconChat;

  return (
    <div className="chat-root">
      {/* Chat Header */}
      <div className="chat-header">
        <button className="chat-back-btn" onClick={onBack}>
          <IconBack />
        </button>
        <div className="chat-header-center">
          <div className="chat-header-icon" style={{ background: scenario?.gradient || `linear-gradient(135deg, ${C.indigo900}, ${C.indigo700})` }}>
            <Icon />
          </div>
          <div>
            <div className="chat-header-name">{scenario?.title || '在线咨询'}</div>
            <div className="chat-header-status">
              <span className="chat-status-dot" />
              AI 咨询师在线
            </div>
          </div>
        </div>
        <div className="chat-header-badge">数据驱动</div>
      </div>

      {/* Profile Summary */}
      {Object.keys(formData).length > 0 && (
        <div className="chat-profile-bar">
          {Object.entries(formData).map(([key, val]) => (
            <span key={key} className="chat-profile-chip">{val}</span>
          ))}
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <ChatBubble key={i} message={msg} index={i} />
        ))}

        {isTyping && (
          <div className="chat-typing">
            <div className="chat-typing-avatar">
              <IconBrain />
            </div>
            <div className="chat-typing-bubble">
              <span className="chat-typing-dot" />
              <span className="chat-typing-dot" />
              <span className="chat-typing-dot" />
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-bar">
        <input
          type="text"
          className="chat-input"
          placeholder="输入你的问题…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(); } }}
        />
        <button
          className="chat-send-btn"
          onClick={onSend}
          disabled={!input.trim()}
        >
          <IconSend />
        </button>
      </div>
    </div>
  );
}

/* ─── CHAT BUBBLE ─── */
function ChatBubble({ message, index }) {
  const isUser = message.role === 'user';

  // Simple markdown-like bold rendering
  function renderContent(text) {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      // Split newlines
      return part.split('\n').map((line, j) => (
        <span key={`${i}-${j}`}>
          {j > 0 && <br />}
          {line}
        </span>
      ));
    });
  }

  return (
    <div className={`chat-bubble-row ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && (
        <div className="chat-bubble-avatar">
          <IconBrain />
        </div>
      )}
      <div className={`chat-bubble ${isUser ? 'user' : 'assistant'}`}>
        <div className="chat-bubble-content">
          {renderContent(message.content)}
        </div>

        {/* Tool Call */}
        {message.toolCall && (
          <div className="chat-tool-call">
            <span className="chat-tool-icon">⚡</span>
            <span className="chat-tool-name">{message.toolCall.name}</span>
            <span className="chat-tool-args">{message.toolCall.args}</span>
          </div>
        )}

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="chat-sources">
            <div className="chat-sources-title">
              <IconData />
              <span>数据来源</span>
            </div>
            <div className="chat-sources-list">
              {message.sources.map((src, i) => (
                <div key={i} className="chat-source-item">
                  <span className="chat-source-title">{src.title}</span>
                  <span className="chat-source-freshness">{src.freshness}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── GLOBAL CSS ─── */
const GLOBAL_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700;900&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --accent: ${TWEAK_DEFAULTS.accentColor};
  --radius: ${TWEAK_DEFAULTS.surfaceRadius};
  --chat-radius: ${TWEAK_DEFAULTS.chatBubbleRadius};
  --indigo900: ${C.indigo900};
  --indigo800: ${C.indigo800};
  --indigo700: ${C.indigo700};
  --amber700: ${C.amber700};
  --amber600: ${C.amber600};
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}

body {
  font-family: ${FONT_SANS};
  color: ${C.text};
  background: ${C.surface};
  line-height: 1.6;
  overflow-x: hidden;
}

/* ─── HOMEPAGE ─── */

.home-root {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.home-hero {
  position: relative;
  background: linear-gradient(160deg, ${C.indigo900} 0%, ${C.indigo800} 40%, ${C.indigo700} 100%);
  padding: clamp(2.5rem, 8vw, 5rem) clamp(1rem, 4vw, 2rem) clamp(2rem, 6vw, 4rem);
  overflow: hidden;
}

.home-hero::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 600px;
  height: 600px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,179,0,0.15) 0%, transparent 70%);
  pointer-events: none;
}

.home-hero::after {
  content: '';
  position: absolute;
  bottom: -30%;
  left: -10%;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,160,0,0.1) 0%, transparent 70%);
  pointer-events: none;
}

.home-hero-grain {
  position: absolute;
  inset: 0;
  background-image: ${GRAIN_SVG};
  background-repeat: repeat;
  pointer-events: none;
  opacity: 0.5;
}

.home-hero-inner {
  position: relative;
  max-width: 800px;
  margin: 0 auto;
  text-align: center;
  z-index: 1;
}

.home-hero-content {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.home-hero-content.visible {
  opacity: 1;
  transform: translateY(0);
}

.home-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 100px;
  color: rgba(255,255,255,0.85);
  font-size: 0.8rem;
  font-weight: 500;
  margin-bottom: 1.5rem;
  backdrop-filter: blur(8px);
}

.home-badge svg {
  width: 16px;
  height: 16px;
  color: var(--accent);
}

.home-title {
  font-family: ${FONT};
  font-size: clamp(2rem, 6vw, 3.2rem);
  font-weight: 900;
  color: ${C.white};
  line-height: 1.25;
  margin-bottom: 1rem;
  letter-spacing: 0.02em;
}

.home-title-amp {
  color: var(--accent);
  font-weight: 700;
}

.home-subtitle {
  font-size: clamp(0.95rem, 2.5vw, 1.1rem);
  color: rgba(255,255,255,0.7);
  line-height: 1.8;
  max-width: 560px;
  margin: 0 auto 2rem;
}

.home-subtitle strong {
  color: rgba(255,255,255,0.95);
  font-weight: 600;
}

.home-stats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  padding: 1rem 1.5rem;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  backdrop-filter: blur(8px);
}

.home-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.home-stat-num {
  font-family: ${FONT};
  font-size: clamp(1.2rem, 3vw, 1.6rem);
  font-weight: 700;
  color: var(--accent);
}

.home-stat-label {
  font-size: 0.75rem;
  color: rgba(255,255,255,0.55);
  font-weight: 400;
}

.home-stat-divider {
  width: 1px;
  height: 32px;
  background: rgba(255,255,255,0.15);
}

/* Scenarios Section */
.home-scenarios {
  padding: clamp(2.5rem, 6vw, 4rem) clamp(1rem, 4vw, 2rem);
  background: ${C.surfaceAlt};
  position: relative;
}

.home-scenarios::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: ${GRAIN_SVG};
  background-repeat: repeat;
  pointer-events: none;
  opacity: 0.3;
}

.home-scenarios-inner {
  position: relative;
  max-width: 960px;
  margin: 0 auto;
  z-index: 1;
}

.home-section-title {
  font-family: ${FONT};
  font-size: clamp(1.3rem, 3.5vw, 1.8rem);
  font-weight: 700;
  color: ${C.indigo900};
  text-align: center;
  margin-bottom: 0.5rem;
}

.home-section-desc {
  text-align: center;
  color: ${C.textMuted};
  font-size: 0.95rem;
  margin-bottom: 2.5rem;
}

.home-cards {
  display: grid;
  gap: 1.25rem;
}

@media (min-width: 768px) {
  .home-cards {
    grid-template-columns: repeat(3, 1fr);
  }
}

.home-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  padding: 1.75rem;
  background: ${C.white};
  border: 1px solid ${C.border};
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
  animation: cardEnter 0.5s ease backwards;
  width: 100%;
  font-family: ${FONT_SANS};
}

.home-card:hover {
  border-color: ${C.indigo100};
  box-shadow: 0 8px 32px rgba(26,35,126,0.08), 0 2px 8px rgba(0,0,0,0.04);
  transform: translateY(-3px);
}

.home-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 14px;
  color: white;
  margin-bottom: 1.25rem;
  flex-shrink: 0;
}

.home-card-body {
  flex: 1;
}

.home-card-title {
  font-family: ${FONT};
  font-size: 1.2rem;
  font-weight: 700;
  color: ${C.indigo900};
  margin-bottom: 0.35rem;
}

.home-card-subtitle {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 0.75rem;
}

.home-card-desc {
  font-size: 0.875rem;
  color: ${C.textMuted};
  line-height: 1.7;
}

.home-card-arrow {
  position: absolute;
  top: 1.75rem;
  right: 1.75rem;
  color: ${C.textLight};
  transition: all 0.2s ease;
}

.home-card:hover .home-card-arrow {
  color: var(--accent);
  transform: translateX(3px);
}

@keyframes cardEnter {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Trust Section */
.home-trust {
  padding: clamp(2rem, 5vw, 3rem) clamp(1rem, 4vw, 2rem);
  max-width: 960px;
  margin: 0 auto;
}

.home-trust-inner {
  display: grid;
  gap: 1.5rem;
  text-align: center;
}

@media (min-width: 768px) {
  .home-trust-inner {
    grid-template-columns: repeat(3, 1fr);
  }
}

.home-trust-item {
  padding: 1.5rem;
}

.home-trust-item svg {
  color: var(--accent);
  margin-bottom: 0.75rem;
}

.home-trust-item h3 {
  font-family: ${FONT};
  font-size: 1.05rem;
  font-weight: 700;
  color: ${C.indigo900};
  margin-bottom: 0.5rem;
}

.home-trust-item p {
  font-size: 0.875rem;
  color: ${C.textMuted};
  line-height: 1.6;
}

/* Footer */
.home-footer {
  padding: 1.5rem;
  text-align: center;
  border-top: 1px solid ${C.border};
  background: ${C.white};
}

.home-footer p {
  font-size: 0.8rem;
  color: ${C.textLight};
}

/* ─── FORM SCREEN ─── */

.form-root {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: clamp(1rem, 4vw, 2rem);
  background: ${C.surfaceAlt};
}

.form-container {
  width: 100%;
  max-width: 600px;
  padding-top: clamp(1rem, 4vw, 3rem);
}

.form-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.form-back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: none;
  color: ${C.textMuted};
  font-size: 0.875rem;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  font-family: ${FONT_SANS};
  transition: background 0.15s;
}

.form-back-btn:hover {
  background: rgba(0,0,0,0.05);
}

.form-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: ${FONT};
  font-weight: 600;
  font-size: 0.95rem;
  color: ${C.indigo900};
}

.form-header-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.form-header-icon svg {
  width: 16px;
  height: 16px;
}

.form-step-count {
  font-size: 0.8rem;
  color: ${C.textLight};
  font-weight: 500;
  padding: 4px 10px;
  background: ${C.white};
  border-radius: 100px;
  border: 1px solid ${C.border};
}

.form-progress-track {
  height: 4px;
  background: ${C.indigo50};
  border-radius: 100px;
  margin-bottom: 2.5rem;
  overflow: hidden;
}

.form-progress-fill {
  height: 100%;
  border-radius: 100px;
  transition: width 0.4s ease;
}

.form-question-area {
  margin-bottom: 2rem;
}

.form-question-number {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.form-question-text {
  font-family: ${FONT};
  font-size: clamp(1.3rem, 4vw, 1.7rem);
  font-weight: 700;
  color: ${C.indigo900};
  line-height: 1.4;
  margin-bottom: 0.5rem;
}

.form-question-hint {
  font-size: 0.9rem;
  color: ${C.textMuted};
}

.form-input-area {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-input-wrapper {
  position: relative;
}

.form-input {
  width: 100%;
  padding: 1rem 1.25rem;
  font-size: 1rem;
  font-family: ${FONT_SANS};
  border: 2px solid ${C.border};
  border-radius: 12px;
  background: ${C.white};
  color: ${C.text};
  outline: none;
  transition: border-color 0.2s;
}

.form-input:focus {
  border-color: ${C.indigo800};
}

.form-input::placeholder {
  color: ${C.textLight};
}

.form-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.form-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 1rem 1.25rem;
  background: ${C.white};
  border: 2px solid ${C.border};
  border-radius: 12px;
  cursor: pointer;
  font-size: 0.95rem;
  font-family: ${FONT_SANS};
  color: ${C.text};
  text-align: left;
  transition: all 0.2s;
  width: 100%;
}

.form-option:hover {
  border-color: ${C.indigo100};
}

.form-option.selected {
  border-color: var(--accent);
  background: ${C.amber50};
}

.form-option-radio {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid ${C.border};
  flex-shrink: 0;
  transition: all 0.2s;
}

.form-option.selected .form-option-radio {
  background: var(--accent);
  border-color: var(--accent);
  box-shadow: inset 0 0 0 3px ${C.white};
}

.form-submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 1rem 2rem;
  border: none;
  border-radius: 12px;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  font-family: ${FONT_SANS};
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 0.5rem;
}

.form-submit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.form-submit-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(26,35,126,0.2);
}

.form-answers {
  margin-top: 2rem;
  padding: 1rem;
  background: ${C.indigo50};
  border-radius: 12px;
}

.form-answers-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: ${C.indigo800};
  margin-bottom: 0.75rem;
}

.form-answers-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.form-chip {
  display: inline-block;
  padding: 4px 12px;
  background: ${C.white};
  border: 1px solid ${C.indigo100};
  border-radius: 100px;
  font-size: 0.8rem;
  color: ${C.indigo800};
}

.form-chip strong {
  font-weight: 600;
}

/* ─── CHAT SCREEN ─── */

.chat-root {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f0ece4;
  position: relative;
}

.chat-header {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  background: ${C.white};
  border-bottom: 1px solid ${C.border};
  gap: 0.75rem;
  flex-shrink: 0;
  z-index: 10;
}

.chat-back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  color: ${C.textMuted};
  transition: background 0.15s;
}

.chat-back-btn:hover {
  background: rgba(0,0,0,0.05);
}

.chat-header-center {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.chat-header-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.chat-header-icon svg {
  width: 18px;
  height: 18px;
}

.chat-header-name {
  font-family: ${FONT};
  font-weight: 600;
  font-size: 0.95rem;
  color: ${C.indigo900};
}

.chat-header-status {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.75rem;
  color: ${C.textMuted};
}

.chat-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: ${C.success};
  animation: pulse 2s ease infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.chat-header-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 3px 10px;
  background: ${C.amber50};
  color: ${C.amber700};
  border-radius: 100px;
  border: 1px solid ${C.amber100};
}

.chat-profile-bar {
  display: flex;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  background: ${C.indigo50};
  border-bottom: 1px solid ${C.indigo100};
  overflow-x: auto;
  flex-shrink: 0;
}

.chat-profile-chip {
  display: inline-block;
  padding: 3px 10px;
  background: ${C.white};
  border: 1px solid ${C.indigo100};
  border-radius: 100px;
  font-size: 0.75rem;
  color: ${C.indigo800};
  white-space: nowrap;
  font-weight: 500;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem clamp(0.75rem, 3vw, 2rem);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.chat-bubble-row {
  display: flex;
  gap: 10px;
  max-width: 85%;
  animation: msgIn 0.3s ease backwards;
}

.chat-bubble-row.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.chat-bubble-row.assistant {
  align-self: flex-start;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-bubble-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, ${C.indigo900}, ${C.indigo700});
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
  margin-top: 2px;
}

.chat-bubble-avatar svg {
  width: 16px;
  height: 16px;
}

.chat-bubble {
  padding: 1rem 1.25rem;
  border-radius: var(--chat-radius);
  font-size: 0.9rem;
  line-height: 1.7;
  position: relative;
}

.chat-bubble.assistant {
  background: ${C.white};
  color: ${C.text};
  border-bottom-left-radius: 6px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.chat-bubble.user {
  background: linear-gradient(135deg, ${C.indigo800}, ${C.indigo700});
  color: ${C.white};
  border-bottom-right-radius: 6px;
}

.chat-bubble strong {
  font-weight: 600;
}

.chat-bubble.user strong {
  color: var(--accent);
}

.chat-tool-call {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 0.75rem;
  padding: 8px 12px;
  background: ${C.amber50};
  border: 1px solid ${C.amber100};
  border-radius: 8px;
  font-size: 0.75rem;
  font-family: 'Menlo', 'Consolas', monospace;
  color: ${C.textMuted};
  overflow: hidden;
}

.chat-tool-icon {
  font-size: 0.85rem;
}

.chat-tool-name {
  font-weight: 600;
  color: ${C.amber700};
}

.chat-tool-args {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-sources {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid ${C.border};
}

.chat-sources-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.75rem;
  font-weight: 600;
  color: ${C.indigo800};
  margin-bottom: 0.5rem;
}

.chat-sources-title svg {
  width: 14px;
  height: 14px;
}

.chat-sources-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.chat-source-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px;
  background: ${C.surfaceAlt};
  border-radius: 8px;
  font-size: 0.75rem;
}

.chat-source-title {
  color: ${C.indigo800};
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-source-freshness {
  color: ${C.success};
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

/* Typing Indicator */
.chat-typing {
  display: flex;
  gap: 10px;
  align-self: flex-start;
}

.chat-typing-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, ${C.indigo900}, ${C.indigo700});
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.chat-typing-avatar svg {
  width: 16px;
  height: 16px;
}

.chat-typing-bubble {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 14px 18px;
  background: ${C.white};
  border-radius: var(--chat-radius);
  border-bottom-left-radius: 6px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.chat-typing-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: ${C.textLight};
  animation: typingBounce 1.2s ease infinite;
}

.chat-typing-dot:nth-child(2) { animation-delay: 0.15s; }
.chat-typing-dot:nth-child(3) { animation-delay: 0.3s; }

@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* Chat Input */
.chat-input-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem clamp(0.75rem, 3vw, 1.5rem);
  background: ${C.white};
  border-top: 1px solid ${C.border};
  flex-shrink: 0;
}

.chat-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid ${C.border};
  border-radius: 12px;
  font-size: 0.9rem;
  font-family: ${FONT_SANS};
  color: ${C.text};
  background: ${C.surfaceAlt};
  outline: none;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: ${C.indigo800};
  background: ${C.white};
}

.chat-input::placeholder {
  color: ${C.textLight};
}

.chat-send-btn {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, ${C.indigo900}, ${C.indigo700});
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.chat-send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.chat-send-btn:not(:disabled):hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(26,35,126,0.25);
}

/* ─── REDUCED MOTION ─── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

/* ─── RESPONSIVE ─── */
@media (max-width: 640px) {
  .home-cards {
    grid-template-columns: 1fr;
  }
  .home-trust-inner {
    grid-template-columns: 1fr;
  }
  .home-stats {
    gap: 1rem;
    flex-wrap: wrap;
  }
  .chat-bubble-row {
    max-width: 92%;
  }
  .chat-header-badge {
    display: none;
  }
  .form-submit-btn {
    width: 100%;
  }
}
`;

/* ─── RENDER ─── */
const root = createRoot(document.getElementById('root'));
root.render(<App />);
