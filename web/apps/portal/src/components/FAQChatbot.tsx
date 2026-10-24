import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useExam } from '../contexts/ExamContext';
import { useI18n } from '../contexts/I18nContext';

interface ChatMessage {
  id: number;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface FAQItem {
  id: number;
  question: string;
  answer: string;
  keywords?: string[];
}

interface FAQCategory {
  category: string;
  questions: FAQItem[];
}

// Documentation file index for full-text search (user-facing docs only)
const DOCS_INDEX: Record<string, { title: string; path: string; content: string }> = {
  'email-smtp': {
    title: 'SMTP & Email Configuration',
    path: 'docs/admin/EMAIL_SMTP.md',
    content: `Configure school email in Admin Dashboard -> School Settings -> Email/SMTP or in .env with SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_TLS, or BREVO_API_KEY. Supports test email delivery and sending 24-hour secure password reset links. See [Admin Dashboard](/admin) or [Settings](/settings).`,
  },
  'seb-config': {
    title: 'Safe Exam Browser (SEB) Setup',
    path: 'docs/user/TEACHER_GUIDE.md',
    content: `Configure Safe Exam Browser (SEB) in [Exam Editor](/teacher-exams). Require Browser Exam Key (BEK) or Configuration Key (CK), disable Wi-Fi/Bluetooth, lock down clipboard, and prevent tab switches. Ensure students launch exams with SEB config (.seb).`,
  },
  'admin-guide': {
    title: 'Administrator Guide',
    path: 'docs/admin/ADMIN_GUIDE.md',
    content: `Administrator guide for PlannedEducation. Manage school users, approve teachers, reset student and teacher passwords with 24-hour reset links, configure deployment, manage midnight backups, and configure SMTP email. See [Admin Dashboard](/admin).`,
  },

  'install-windows': {
    title: 'Windows Installation Guide',
    path: 'docs/INSTALL_WINDOWS.md',
    content: `Install PlannedEducation on Windows using PowerShell. Run install.ps1 as Administrator. Choose Native Mode (SQLite/PostgreSQL, no Docker) or Docker Compose Mode. Set ExecutionPolicy Bypass. Configure .env with JWT_SECRET_KEY, DATABASE_URL. Build frontend with npm run build. Start with start_all.bat.`,
  },
  'install-linux': {
    title: 'Linux Installation Guide',
    path: 'docs/INSTALL_LINUX.md',
    content: `Install PlannedEducation on Linux using install.sh. Creates virtual environment, configures SQLite/PostgreSQL, sets up Systemd service. Supports Ubuntu 22.04/24.04, Debian 12, CentOS/RHEL. Run curl or clone repo and execute ./install.sh.`,
  },
  'deployment-guide': {
    title: 'Deployment Guide',
    path: 'docs/DEPLOYMENT.md',
    content: `Deploy PlannedEducation to production. Use Docker Compose with docker-compose.yml. Set environment variables: JWT_SECRET_KEY, DATABASE_URL, REDIS_URL. Run alembic migrations. Build frontend. Use Nginx/Caddy reverse proxy with Let's Encrypt TLS. Configure CORS_ORIGINS and ALLOWED_HOSTS.`,
  },
  'teacher-guide': {
    title: 'Teacher Guide',
    path: 'docs/user/TEACHER_GUIDE.md',
    content: `Teacher guide for PlannedEducation. Self-registration and administrator approval. Classroom and student management. Exam authoring with dynamic math variables. Curriculum modules and question banks. Secure Exam Browser (SEB) lockdown mode. Archive Browser and AI-assisted grading workflow with Presidio PII scrubbing. Teacher review and correction modal. Sealing into encrypted zstd archive. Reviewable and re-correctable anytime.`,
  },
  'student-guide': {
    title: 'Student Guide',
    path: 'docs/user/STUDENT_GUIDE.md',
    content: `Student guide for PlannedEducation. Registration and the 5 recovery codes. Taking exams with Safe Exam Browser (SEB). Offline resilience and auto-save. Password recovery: 3 ways (self-reset with recovery codes, emergency classroom unlock by teacher, in-app password reset request). Reviewing grades and feedback.`,
  },
  'parent-guide': {
    title: 'Parent Guide',
    path: 'docs/user/PARENT_GUIDE.md',
    content: `Parent guide for PlannedEducation. Registration and account linking to child's account. Viewing grades, progress and teacher feedback. Privacy and FERPA compliance. Helping your child recover their password.`,
  },
  'faq': {
    title: 'FAQ - Frequently Asked Questions',
    path: 'docs/user/FAQ.md',
    content: `PlannedEducation FAQ. Getting started: create exam, students join exam, Secure Exam Browser, question bank, reusable modules. Account & security: reset password, admin reset without email, database backups, configure email SMTP, enable 2FA, passkeys. Exams & grading: AI-assisted grading, offline grading, view submissions, AI providers, AI grading review workflow, AI safety controls, AI cost tracking warning. Test packages & sharing.`,
  },
  'install-windows': {
    title: 'Windows Installation Guide',
    path: 'docs/admin/INSTALL_WINDOWS.md',
    content: `Install PlannedEducation on Windows using PowerShell. Run install.ps1 as Administrator. Choose Native Mode (SQLite/PostgreSQL, no Docker) or Docker Compose Mode. Set ExecutionPolicy Bypass. Configure .env with JWT_SECRET_KEY, DATABASE_URL. Build frontend with npm run build. Start with start_all.bat.`,
  },
  'install-linux': {
    title: 'Linux Installation Guide',
    path: 'docs/admin/INSTALL_LINUX.md',
    content: `Install PlannedEducation on Linux using install.sh. Creates virtual environment, configures SQLite/PostgreSQL, sets up Systemd service. Supports Ubuntu 22.04/24.04, Debian 12, CentOS/RHEL. Run curl or clone repo and execute ./install.sh.`,
  },
  'deployment-guide': {
    title: 'Deployment Guide',
    path: 'docs/admin/DEPLOYMENT_GUIDE.md',
    content: `Deploy PlannedEducation to production. Use Docker Compose with docker-compose.yml. Set environment variables: JWT_SECRET_KEY, DATABASE_URL, REDIS_URL. Run alembic migrations. Build frontend. Use Nginx/Caddy reverse proxy with Let's Encrypt TLS. Configure CORS_ORIGINS and ALLOWED_HOSTS.`,
  },
  'backup-restore': {
    title: 'Backup & Restore',
    path: 'docs/admin/BACKUP_RESTORE.md',
    content: `Database backups and disaster recovery. Midnight auto-backup, snapshot management, restore procedures, backup verification, offsite storage options.`,
  },
  'smtp-email': {
    title: 'SMTP & Email Configuration',
    path: 'docs/admin/DEPLOYMENT_GUIDE.md',
    content: `SMTP and email setup for PlannedEducation. Configure BREVO_API_KEY (free 300 emails/day) or school SMTP settings (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM) in .env file. Email OTP reset links expire in 24 hours. Admin can configure email in Admin Dashboard > Deployment & Network. Email is optional - if unconfigured, OTP codes are logged safely for offline school use.`,
  },
};

// FAQ data with categories and common questions
const FAQ_DATA: FAQCategory[] = [
  {
    category: "Getting Started",
    questions: [
      {
        id: 40,
        question: "How does the Archive Browser and AI grading work?",
        keywords: ["archive", "browser", "grading", "ai", "staging", "correction", "workflow"],
        answer: "The Archive Browser in Teacher Dashboard allows you to view class submissions and offline test uploads. Select tests and click 'AI Correct Selected' — Presidio scrubs all student PII before external evaluation. Results are held in a temporary staging state ('pending_approval') on disk. Click 'Review & Correct' to open the TeacherCorrectionModal, adjust scores or feedback, and click 'Approve & Seal' to compress (zstd) and encrypt (AES-GCM) into the permanent archive."
      },
      {
        id: 41,
        question: "How is student privacy protected during AI grading?",
        keywords: ["privacy", "presidio", "anonymizer", "pii", "ferpa", "gdpr", "scrub"],
        answer: "Zero student PII is ever sent to AI. PlannedEducation uses Microsoft Presidio to scrub all names, email addresses, phone numbers, locations, and dates from student answers. The local database securely maintains the association so only the teacher sees real student identities in the dashboard."
      },
      {
        id: 42,
        question: "Can I re-correct or edit an archived graded test?",
        keywords: ["reopen", "re-correct", "edit", "archive", "mistake", "change", "grade"],
        answer: "Yes! In the Archive Browser, any graded exam has a '🔄 Re-correct' button. Clicking it reopens the test, moves it back to staging, and allows you to adjust points, update feedback, and re-approve without losing historical audit logs."
      },
      {
        id: 43,
        question: "What AI providers are supported?",
        keywords: ["ai", "provider", "gemini", "anthropic", "deepseek", "groq", "ollama", "openrouter", "openai"],
        answer: "PlannedEducation supports BYOK (Bring-Your-Own-Key) for Anthropic (Claude), DeepSeek, Groq, Ollama (local/offline), Google Gemini, OpenRouter, Mistral, OpenAI, and custom OpenAI-compatible endpoints. Configure your preferred provider in Settings > AI Keys."
      },
      {
        id: 1,
        question: "How do I create an exam?",
        answer: "To create an exam, go to the Teacher Dashboard, click 'Create New Exam', fill in the exam details, add questions, and save. You can also import questions from a question bank."
      },
      {
        id: 2,
        question: "How do students join an exam?",
        answer: "Students receive an exam code or link from their teacher. They can join by visiting the PlannedEducation portal and entering the exam code, or by clicking the direct link provided by the teacher."
      },
      {
        id: 3,
        question: "What is the Secure Exam Browser (SEB)?",
        answer: "The Secure Exam Browser is a locked-down browser environment that prevents students from accessing other applications or websites during an exam, ensuring test integrity and preventing cheating."
      },
      {
        id: 13,
        question: "How do I create a question bank?",
        answer: "Go to Teacher Dashboard > Question Banks > 'New Bank'. Name it, add subject/tags, then add questions. You can import from existing exams or create new questions."
      },
      {
        id: 14,
        question: "What are reusable modules?",
        answer: "Modules are self-contained question sets with shared context (e.g., a reading passage with 5 questions). Create them in the Exam Editor > 'Create Module', add context and questions, then reuse across exams."
      }
    ]
  },
  {
    category: "Account & Security",
    questions: [
      {
        id: 4,
        question: "How do I reset my password?",
        keywords: ["password", "reset", "forgot", "login"],
answer: "You have 3 ways to reset your password: (1) Use one of your 5 one-time recovery codes on the login screen under 'Forgot Password?' — fastest and independent. (2) Ask your teacher or parent for a quick reset — they click '⚡ Reset Password' next to your name, then you set a new password on the login page. (3) Ask an administrator to reset it from the Admin Panel. Reset links expire in 24 hours.",
      },
      {
        id: 32,
        question: "Can an admin reset user passwords without email?",
        keywords: ["admin", "reset", "password", "without", "email", "lost", "panel"],
        answer: "Yes! Administrators can reset any user's password directly from the Admin Panel > Users tab by clicking '🔑 Reset Password'. They can specify a new password or let the system auto-generate a temporary password, and optionally reset 2FA/Passkeys if the user lost their authenticator device. Teachers can reset student passwords; admins can reset teacher passwords; superadmins can reset admin passwords."
      },
      {
        id: 33,
        question: "How does the optional email service work?",
        keywords: ["email", "smtp", "brevo", "hcaptcha", "mail", "server"],
        answer: "Email is completely optional. If unconfigured, PlannedEducation logs OTP codes safely for offline school use. To enable email, add BREVO_API_KEY (free 300 emails/day) or your school SMTP settings (SMTP_HOST, SMTP_PORT, etc.) to .env. Email OTP reset links expire in 24 hours."
      },
      {
        id: 5,
        question: "How do I enable two-factor authentication?",
        answer: "Go to Settings > Security, click 'Enable 2FA', scan the QR code with your authenticator app, and enter the verification code to complete setup. Save your 5 recovery codes in case you lose your phone."
      },
      {
        id: 34,
        question: "How do I change my own password?",
        keywords: ["change", "my", "password", "settings", "profile"],
        answer: "Go to Settings > Personal Details. Enter your current password, then type your new password twice and click 'Save Changes'. The server verifies your current password before accepting the change."
      },
      {
        id: 35,
        question: "How do I customize my school's header?",
        keywords: ["header", "logo", "branding", "school", "name", "image", "customize"],
        answer: "Admins and superadmins can customize the platform header via Admin Dashboard → School Settings → Header. Choose from three modes: 'text' (shows school name), 'image' (shows a custom header image URL), or 'none' (no header). This makes the platform feel like your own school's system."
      },
      {
        id: 36,
        question: "What is the difference between admin and superadmin?",
        keywords: ["superadmin", "admin", "difference", "roles", "create", "user"],
        answer: "Admins can create users (teachers, students, parents, other admins), manage exams, reset teacher passwords, and configure deployment. Superadmins have all admin capabilities PLUS the ability to create other superadmins. Superadmin creation is restricted to existing superadmins only."
      },
      {
        id: 6,
        question: "What are Passkeys and how do I use them?",
        answer: "Passkeys are a passwordless authentication method using biometrics or device PIN. You can set them up in Settings > Passkeys by registering your device's biometric authentication. Passkeys sync across devices via iCloud Keychain or Google Password Manager."
      },
      {
        id: 15,
        question: "How do I register a Passkey?",
        answer: "Go to Settings > Passkeys, click 'Register Passkey', and use your device's biometric (fingerprint, face ID) or PIN to create the passkey. It will sync across your devices automatically."
      }
    ]
  },
  {
    category: "Exams & Grading",
    questions: [
      {
        id: 7,
        question: "How does AI-assisted grading work?",
        answer: "Teachers can configure their preferred AI provider (Gemini, OpenRouter, Ollama, etc.) in Settings. When grading exams, the AI provides suggestions that teachers can review, edit, or approve before finalizing grades."
      },
      {
        id: 8,
        question: "Can I grade exams offline?",
        answer: "Yes! PlannedEducation supports offline-first exam taking. Students can take exams without internet connection, and their answers are saved locally and synced when connection is restored."
      },
      {
        id: 9,
        question: "How do I view student submissions?",
        answer: "After students submit exams, go to Teacher Dashboard, select the exam, and click 'View Submissions' to see all student answers and AI-generated feedback."
      },
      {
        id: 16,
        question: "Which AI providers are supported?",
        answer: "Gemini (Google), OpenRouter (100+ models), Ollama (local), OpenAI-compatible endpoints, and ChatGPT session (device-code OAuth). Configure in Settings > AI Key Management."
      },
      {
        id: 17,
        question: "How does the AI grading review workflow work?",
        answer: "AI provides score, feedback, confidence, and reasoning for each question. Teachers can Approve (accept as-is), Edit (modify score/feedback), or Reject (grade manually). Bulk actions: 'Approve All High Confidence' or 'Flag Low Confidence for Review'."
      },
      {
        id: 18,
        question: "What are the AI safety controls?",
        answer: "Prompt injection detection (20+ patterns), hallucination detection via consistency checking, output schema validation, confidence threshold (min 0.75), rate limiting (20/min, 200/hour), cost tracking ($5/day budget), provider health monitoring with automatic fallback."
      },
      {
        id: 19,
        question: "Is AI cost tracking accurate?",
        answer: "⚠️ IMPORTANT: AI cost tracking is OPTIONAL and provides ROUGH ESTIMATES ONLY. AI provider pricing changes frequently (per-token costs, model pricing, regional differences, enterprise discounts, cached tokens, batch pricing). We CANNOT and SHALL NOT track ever-changing AI costs per supplier accurately. Limitations: estimates based on static pricing tables that may be outdated; only tracks token counts from API responses; does NOT account for cached tokens, batch discounts, enterprise pricing, regional pricing, model version changes. Should NOT be relied upon for billing, budgeting, or financial decisions. Teachers MUST monitor their own AI provider dashboards for actual costs. Treat as a rough guardrail only; disable if not needed."
      }
    ]
  },
  {
    category: "Test Packages & Sharing",
    questions: [
      {
        id: 19,
        question: "How do I export a test package?",
        answer: "Open an exam in the Exam Editor, click 'Export Package', choose JSON or YAML format, select options (include answers, rubrics, variables), and download the .pepkg.json file."
      },
      {
        id: 20,
        question: "How do I import a test package?",
        answer: "Go to Teacher Dashboard > 'Import Package', drag the .pepkg.json/.yaml file, preview the contents, choose import options (new exam, add to existing, import modules/questions), and confirm."
      },
      {
        id: 21,
        question: "What is the pepkg CLI?",
        answer: "The pepkg CLI is a command-line tool for managing test packages: export/import/validate/list/download packages, publish/unpublish, search, and local validation. Install with 'pip install -e ./pepkg'."
      },
      {
        id: 22,
        question: "How do I share packages with colleagues?",
        answer: "Send .pepkg.json via email/shared drive/USB, or use the pepkg CLI to publish to the registry. Recipients import via 'Import Package' or 'pepkg install'."
      }
    ]
  },
  {
    category: "Proctoring & Monitoring",
    questions: [
      {
        id: 23,
        question: "How do I enable proctoring for an exam?",
        answer: "In exam settings, enable 'Proctoring'. Students will be prompted for camera/microphone permissions and must complete GDPR consent. Events tracked: eye movement, multiple faces, background audio, tab switches, SEB violations."
      },
      {
        id: 24,
        question: "What proctoring events are tracked?",
        answer: "Eye movement (gaze tracking), multiple face detection, background audio levels, tab/window switches, SEB violations. View in Teacher Dashboard > Proctoring tab with real-time feed and session replay."
      }
    ]
  },
  {
    category: "Technical Support",
    questions: [
      {
        id: 10,
        question: "What browsers are supported?",
        answer: "PlannedEducation works best with modern browsers: Chrome, Firefox, Safari, and Edge. For secure exams, we recommend using the Secure Exam Browser (SEB) or Chrome Canary for development."
      },
      {
        id: 11,
        question: "Is my data private and secure?",
        answer: "Yes! PlannedEducation is privacy-first and open-source. All data is stored locally or on your self-hosted server. We use end-to-end encryption for sensitive data and never sell or share your information."
      },
      {
        id: 12,
        question: "How do I get help or report issues?",
        answer: "For technical issues, check the documentation in the docs/ folder. For feature requests or bug reports, visit our GitHub repository and open an issue."
      },
      {
        id: 25,
        question: "What are the system requirements?",
        answer: "Backend: Python 3.12+, PostgreSQL 16, Redis 7. Frontend: Node.js 20+. For SEB: Windows/macOS with SEB installed. For proctoring: camera + microphone permissions."
      },
      {
        id: 26,
        question: "How do I deploy to production?",
        answer: "Use Docker Compose with docker-compose.yml + docker-compose.prod.yml. Set environment variables (JWT_SECRET_KEY, DATABASE_URL, etc.). Run migrations with alembic. Build frontend with 'npm run build'. Use Nginx/Caddy reverse proxy with Let's Encrypt TLS."
      }
    ]
  },
  {
    category: "Installation & Deployment",
    questions: [
      {
        id: 27,
        question: "How do I install PlannedEducation on Windows?",
        keywords: ["windows", "install", "installer", "powershell", "install.ps1", "pc", "setup"],
        answer: "To install on Windows: Open PowerShell as Administrator and run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; .\\install.ps1`. You can choose Native Mode (runs directly on Python with zero-config SQLite or PostgreSQL, no Docker required) or Docker Compose Mode. See docs/INSTALL_WINDOWS.md."
      },
      {
        id: 28,
        question: "How do I install PlannedEducation on Linux?",
        keywords: ["linux", "install", "ubuntu", "debian", "install.sh", "bash", "server"],
        answer: "To install on Linux (Ubuntu 22.04/24.04, Debian 12, CentOS/RHEL): Run `curl -fsSL https://raw.githubusercontent.com/ezixen/PlannedEducation/main/install.sh | bash` or clone the repo and run `./install.sh`. It automatically creates a virtual environment, configures SQLite/PostgreSQL, and sets up a background Systemd service. See docs/INSTALL_LINUX.md."
      },
      {
        id: 29,
        question: "Can I run without Docker?",
        keywords: ["docker", "native", "sqlite", "nodocker", "lightweight", "without"],
        answer: "Yes! Both Windows (install.ps1) and Linux (install.sh) installers provide a Native Mode. PlannedEducation runs directly on host Python 3.12+ with SQLite (zero-config standalone file database) or local PostgreSQL and Redis. This provides fast, lightweight performance for schools without Docker."
      },
      {
        id: 30,
        question: "How do I use the deployment wizard?",
        keywords: ["wizard", "deploy_wizard", "setup", "guided", "interactive"],
        answer: "Run `python deploy_wizard.py` (or `python3 deploy_wizard.py`). This cross-platform CLI wizard detects your environment, generates cryptographically secure JWT and Fernet encryption keys, configures .env, builds frontend assets, and initializes database tables."
      },
      {
        id: 31,
        question: "How do students and teachers connect over school Wi-Fi or LAN?",
        keywords: ["wifi", "lan", "network", "connect", "ip", "school", "firewall", "students", "teachers"],
        answer: "1. Find your server's local IPv4 (e.g., 192.168.1.150). 2. Open port 8000 in your firewall (or port 80 if using Nginx). 3. In .env, set ALLOWED_HOSTS and CORS_ORIGINS to include the server IP. 4. Teachers and students connect by browsing to http://<SERVER_IP>:8000 in any browser or Safe Exam Browser (SEB)."
      }
    ]
  }
];

export function FAQChatbot() {
  const { t } = useI18n();
  const { isExamActive } = useExam();
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  // Disable chatbot during exam taking
  if (isExamActive) {
    return null;
  }

  // Add welcome message when component mounts
  useEffect(() => {
    setMessages([{
      id: 0,
      text: "Hello! I'm the PlannedEducation FAQ assistant. How can I help you today?",
      sender: "bot",
      timestamp: new Date()
    }]);
  }, []);

  // Find answer based on user input - searches FAQ data AND all documentation
  const findAnswer = (query: string) => {
    const lowerQuery = query.toLowerCase().trim();
    
    // Direct matches or keyword-based matches in FAQ data
    for (const category of FAQ_DATA) {
      for (const faq of category.questions) {
        // Direct question match
        if (lowerQuery.includes(faq.question.toLowerCase()) || faq.question.toLowerCase().includes(lowerQuery)) {
          return faq.answer;
        }

        // Targeted keywords check (supports single-word matches for specific topics)
        if (faq.keywords) {
          const queryWords = lowerQuery.split(/\s+/);
          const matchedKeywords = faq.keywords.filter(keyword => {
            const kw = keyword.toLowerCase();
            return lowerQuery.includes(kw) || queryWords.includes(kw);
          });
          if (matchedKeywords.length >= 1) {
            return faq.answer;
          }
        }

        const questionWords = faq.question.toLowerCase().split(' ');
        const queryWords = lowerQuery.split(' ');
        
        // Check if any significant words match
        const matches = questionWords.filter(word => 
          word.length > 3 && queryWords.includes(word)
        );
        
        if (matches.length >= 2) {
          return faq.answer;
        }
      }
    }
    
    // Search through documentation index
    const docMatches = Object.entries(DOCS_INDEX).filter(([, doc]) => {
      const searchable = (doc.title + ' ' + doc.content).toLowerCase();
      const queryWords = lowerQuery.split(' ').filter(w => w.length > 2);
      const matches = queryWords.filter(w => searchable.includes(w));
      return matches.length >= Math.min(2, queryWords.length);
    });
    
    if (docMatches.length > 0) {
      const [, doc] = docMatches[0];
      return `📚 Found in **${doc.title}** (${doc.path}):\n\n${doc.content.substring(0, 500)}...\n\nFor full details, see the documentation file.`;
    }
    
    // Default response if no match found
    return "I'm sorry, I don't have an answer for that question. Please try rephrasing or check our documentation in the docs/ folder (e.g., docs/INSTALL_WINDOWS.md or docs/INSTALL_LINUX.md).";
  };

  // Handle sending message
  const sendMessage = async () => {
    if (!input.trim()) return;
    
    const userMessage: ChatMessage = {
      id: Date.now(),
      text: input,
      sender: "user",
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);
    
    // Simulate bot thinking time
    setTimeout(() => {
      const botResponse: ChatMessage = {
        id: Date.now() + 1,
        text: findAnswer(input),
        sender: "bot",
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, botResponse]);
      setIsTyping(false);
    }, 800);
  };

  // Handle key press
  // Helper to render text with clickable in-app links
  const renderMessageContent = (text: string) => {
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = linkRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }
      const [, label, url] = match;
      if (url.startsWith('/')) {
        parts.push(
          <Link
            key={match.index}
            to={url}
            onClick={() => setIsOpen(false)}
            style={{ color: 'var(--primary-color)', fontWeight: 600, textDecoration: 'underline' }}
          >
            {label}
          </Link>
        );
      } else {
        parts.push(
          <a
            key={match.index}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--primary-color)', fontWeight: 600, textDecoration: 'underline' }}
          >
            {label}
          </a>
        );
      }
      lastIndex = linkRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="faq-chatbot-container">
      {/* Floating Button */}
      <button 
        className="faq-chatbot-button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label={t("faq.open_aria")}
      >
        <span className="faq-chatbot-icon">❓</span>
        <span className="faq-chatbot-label">{t("faq.help_btn")}</span>
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div className="faq-chatbot-window">
          <div className="faq-chatbot-header">
            <h3>{t("faq.title")}</h3>
            <button 
              className="faq-chatbot-close"
              onClick={() => setIsOpen(false)}
              aria-label={t("faq.close_aria")}
            >
              ×
            </button>
          </div>
          
          <div className="faq-chatbot-messages">
            {messages.map(message => (
              <div 
                key={message.id} 
                className={`faq-chatbot-message ${message.sender === 'user' ? 'user' : 'bot'}`}
              >
                <div className="faq-chatbot-message-content">
                  {renderMessageContent(message.text)}
                </div>
                <div className="faq-chatbot-message-time">
                  {message.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                </div>
              </div>
            ))}
            
            {isTyping && (
              <div className="faq-chatbot-message bot typing">
                <div className="faq-chatbot-message-content">
                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>
                  {t("faq.typing")}
                </div>
              </div>
            )}
          </div>
          
          <div className="faq-chatbot-input-area">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("faq.placeholder")}
              className="faq-chatbot-input"
            />
            <button 
              onClick={sendMessage}
              disabled={!input.trim() || isTyping}
              className="faq-chatbot-send-button"
            >
              {t("faq.send")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}