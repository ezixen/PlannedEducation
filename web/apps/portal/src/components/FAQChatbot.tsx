import { useState, useEffect } from 'react';
import { useExam } from '../contexts/ExamContext';

interface ChatMessage {
  id: number;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

// FAQ data with categories and common questions
const FAQ_DATA = [
  {
    category: "Getting Started",
    questions: [
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
      }
    ]
  },
  {
    category: "Account & Security",
    questions: [
      {
        id: 4,
        question: "How do I reset my password?",
        answer: "Click 'Forgot Password' on the login page, enter your email address, and follow the instructions sent to your email to reset your password."
      },
      {
        id: 5,
        question: "How do I enable two-factor authentication?",
        answer: "Go to Settings > Security, click 'Enable 2FA', scan the QR code with your authenticator app, and enter the verification code to complete setup."
      },
      {
        id: 6,
        question: "What are Passkeys and how do I use them?",
        answer: "Passkeys are a passwordless authentication method using biometrics or device PIN. You can set them up in Settings > Passkeys by registering your device's biometric authentication."
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
      }
    ]
  }
];

export function FAQChatbot() {
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

  // Find answer based on user input
  const findAnswer = (query: string) => {
    const lowerQuery = query.toLowerCase();
    
    // Simple keyword matching
    for (const category of FAQ_DATA) {
      for (const faq of category.questions) {
        const questionWords = faq.question.toLowerCase().split(' ');
        const queryWords = lowerQuery.split(' ');
        
        // Check if any significant words match
        const matches = questionWords.filter(word => 
          word.length > 3 && queryWords.includes(word)
        );
        
        if (matches.length >= 2) { // At least 2 matching words
          return faq.answer;
        }
        
        // Direct question match
        if (lowerQuery.includes(faq.question.toLowerCase())) {
          return faq.answer;
        }
      }
    }
    
    // Default response if no match found
    return "I'm sorry, I don't have an answer for that question. Please try rephrasing or contact support for further assistance.";
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
        aria-label="Open FAQ Chatbot"
      >
        <span className="faq-chatbot-icon">❓</span>
        <span className="faq-chatbot-label">Help</span>
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div className="faq-chatbot-window">
          <div className="faq-chatbot-header">
            <h3>PlannedEducation Help</h3>
            <button 
              className="faq-chatbot-close"
              onClick={() => setIsOpen(false)}
              aria-label="Close chat"
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
                  {message.text}
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
                  Typing...
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
              placeholder="Type your question..."
              className="faq-chatbot-input"
            />
            <button 
              onClick={sendMessage}
              disabled={!input.trim() || isTyping}
              className="faq-chatbot-send-button"
            >
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  );
}