import React, { useRef, useEffect, useCallback, useState } from 'react';
import { Form, useNavigation, Link, useLocation, useNavigate } from '@remix-run/react';

import SendIcon from '../components/Icons/Send';
import Message from '../components/Message';

interface ChatCompletionRequestMessage {
  content: string;
  role: 'User' | 'Assistant' | 'System';
}

export interface ChatHistoryProps extends ChatCompletionRequestMessage {
  error?: boolean;
}

// Dummy action function since we're handling responses entirely on the client.
export async function action({ request }: { request: Request }) {
  return new Response(null);
}

interface ServerUrlChangeEvent extends CustomEvent {
  detail: {
    serverUrl: string;
  };
}

const ThinkingMessage = () => {
  console.log('Rendering ThinkingMessage component - waiting for backend response');
  return (
    <div className="message message-assistant animate-fade-in">
      <div className="message-bubble flex items-start gap-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="w-5 h-5"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v.01" />
            <path d="M12 8v4" />
          </svg>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 bg-text-tertiary rounded-full animate-pulse-subtle" style={{ '--delay': '0' } as React.CSSProperties}></div>
            <div className="w-2 h-2 bg-text-tertiary rounded-full animate-pulse-subtle" style={{ '--delay': '1' } as React.CSSProperties}></div>
            <div className="w-2 h-2 bg-text-tertiary rounded-full animate-pulse-subtle" style={{ '--delay': '2' } as React.CSSProperties}></div>
            <span className="text-sm text-text-secondary font-medium">Thinking...</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default function IndexPage() {
  const minTextareaRows = 1;
  const maxTextareaRows = 3;
  
  // Refs and state
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const navigation = useNavigation();
  const [chatHistory, setChatHistory] = useState<ChatHistoryProps[]>([]);
  // const [serverUrl, setServerUrl] = useState('http://localhost:8000/query');
  const [serverUrl, setServerUrl] = useState('http://localhost:8080/query');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const handleServerUrlChange = (event: ServerUrlChangeEvent) => {
      console.log('Server URL changed:', event.detail.serverUrl);
      setServerUrl(event.detail.serverUrl);
    };
    window.addEventListener('serverUrlChange', handleServerUrlChange as EventListener);
    return () => {
      window.removeEventListener('serverUrlChange', handleServerUrlChange as EventListener);
    };
  }, []);

  const location = useLocation();
  const navigate = useNavigate();
  const isSubmitting = navigation.state === 'submitting';

  // Adjust textarea height dynamically.
  const handleTextareaChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (!inputRef.current) return;
    inputRef.current.rows = minTextareaRows;
    const lineHeight = parseInt(window.getComputedStyle(inputRef.current).lineHeight);
    const paddingTop = parseInt(window.getComputedStyle(inputRef.current).paddingTop);
    const paddingBottom = parseInt(window.getComputedStyle(inputRef.current).paddingBottom);
    const scrollHeight = inputRef.current.scrollHeight - paddingTop - paddingBottom;
    const currentRows = Math.floor(scrollHeight / lineHeight);
    if (currentRows >= maxTextareaRows) {
      inputRef.current.rows = maxTextareaRows;
      inputRef.current.scrollTop = event.target.scrollHeight;
    } else {
      inputRef.current.rows = currentRows;
    }
  };

  const pushChatHistory = useCallback((message: ChatHistoryProps) => {
    console.log('Adding to chat history:', message.role, message.error ? '(error)' : '');
    setChatHistory(prev => [...prev, message]);
    setTimeout(() => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTop = 0;
      }
    }, 100);
  }, []);

  const saveUserMessage = (content: string) => {
    console.log('Saving user message:', content.substring(0, 50) + (content.length > 50 ? '...' : ''));
    const userMessage: ChatHistoryProps = { role: 'User', content };
    pushChatHistory(userMessage);
  };

  const handleFormSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const message = formData.get('message') as string;
    if (!message || message.trim() === '') return;
    
    // Add user's message immediately.
    const userMessage = { role: 'User', content: message };
    const newChatHistory = [...chatHistory, userMessage];
    setChatHistory(newChatHistory);
    
    // Create the full prompt from chat history.
    const fullChatHistory = newChatHistory.map(msg => `${msg.role}: ${msg.content}`).join('\n');
    
    // Clear the input.
    if (inputRef.current) {
      inputRef.current.value = '';
      inputRef.current.style.height = 'auto';
    }
    
    // Set loading state to show thinking bubble.
    setIsLoading(true);
    
    // Determine if we're streaming or doing a normal query.
    const isStreaming = serverUrl.endsWith('stream');
    
    try {
      const response = await fetch(serverUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: fullChatHistory,
          max_length: 1024,
          temperature: isStreaming ? 0.2 : 0.5,
          top_p: 0.5,
          top_k: isStreaming ? 25 : 50,
          ...(isStreaming ? {} : { num_return_sequences: 1 }),
        }),
      });
      
      if (!response.ok) {
        console.error('API request failed');
        pushChatHistory({
          role: 'Assistant',
          content: 'Error: Unable to get a response from the backend.',
          error: true,
        });
        setIsLoading(false);
        return;
      }
      
      if (isStreaming && response.body) {
        // Streaming response handling.
        const assistantMessage = { role: 'Assistant', content: '' };
        pushChatHistory(assistantMessage);
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let done = false;
        let streamingContent = '';
        while (!done) {
          const { done: doneReading, value } = await reader.read();
          done = doneReading;
          if (value) {
            const chunk = decoder.decode(value);
            streamingContent += chunk;
            setChatHistory(prev => {
              const updated = [...prev];
              updated[updated.length - 1].content = streamingContent;
              return updated;
            });
          }
        }
      } else {
        // Normal query: expect complete JSON response.
        const data = await response.json();
        console.log('Received response:', data);
        const answer = data.generated_text[0] || '';
        pushChatHistory({
          role: 'Assistant',
          content: answer,
        });
      }
    } catch (error) {
      console.error('Error during API call:', error);
      pushChatHistory({
        role: 'Assistant',
        content: 'Error: Failed to process the response.',
        error: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Use formRef.current.requestSubmit() to trigger a proper form submission.
  const handleKeyDown = useCallback((event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && (event.target as HTMLTextAreaElement).value.trim().length > 2) {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  }, []);

  const scrollToBottom = useCallback((animationDuration: number = 300) => {
    const body = document.body;
    const html = document.documentElement;
    const startTime = performance.now();
    const step = (currentTime: number) => {
      const targetScrollTop = Math.max(
        body.scrollHeight,
        body.offsetHeight,
        html.clientHeight,
        html.scrollHeight,
        html.offsetHeight
      );
      const progress = (currentTime - startTime) / animationDuration;
      window.scrollTo({ top: targetScrollTop });
      if (progress < 1) window.requestAnimationFrame(step);
    };
    window.requestAnimationFrame(step);
  }, []);

  // Optionally restore chat history from location state.
  const setChat = useCallback(() => {
    if (location.state && (location.state as any).chatHistory) {
      setChatHistory((location.state as any).chatHistory);
      scrollToBottom();
    }
  }, [location, scrollToBottom]);

  useEffect(() => {
    if (!inputRef.current) return;
    if (navigation.state === 'submitting') {
      inputRef.current.value = '';
      inputRef.current.rows = 1;
    } else {
      inputRef.current.focus();
    }
  }, [navigation.state]);

  useEffect(() => {
    if (!location.state) {
      setChatHistory([]);
      scrollToBottom();
    }
  }, [location, scrollToBottom]);

  useEffect(() => {
    setChat();
  }, [setChat]);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory]);

  return (
    <div className="flex flex-col h-full">
      <div 
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto flex flex-col-reverse p-4 md:p-6"
      >
        <div className="flex flex-col gap-4 max-w-3xl mx-auto w-full">
          {chatHistory.map((chat, index) => (
            <Message
              key={`message-${index}`}
              error={chat.error}
              content={chat.content}
              role={chat.role}
            />
          ))}
          {isLoading && <ThinkingMessage />}
        </div>
      </div>

      <div className="sticky bottom-0 bg-background border-t border-input p-4 md:p-6">
        <Form method="post" ref={formRef} onSubmit={handleFormSubmit} replace className="max-w-3xl mx-auto">
          <div className="relative flex items-end rounded-3xl border border-input bg-input-gradient shadow-md hover:shadow-lg transition-all focus-subtle">
            <textarea
              ref={inputRef}
              name="message"
              placeholder="Ask a question..."
              rows={1}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              className="flex-1 resize-none border-0 bg-transparent p-4 pr-12 text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-0 focus-visible:ring-0 focus-visible:ring-offset-0 sm:text-sm"
              style={{ minHeight: `${minTextareaRows * 24}px`, maxHeight: `${maxTextareaRows * 24}px` }}
            />
            <input type="hidden" name="serverUrl" value={serverUrl} />
            <button
              type="submit"
              disabled={isLoading || isSubmitting}
              className="absolute bottom-3 right-3 p-2 rounded-full bg-primary text-white hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:pointer-events-none shadow-sm hover-scale"
              aria-label="Send message"
            >
              <SendIcon className="w-5 h-5" />
            </button>
          </div>
        </Form>
      </div>
    </div>
  );
}

export function ErrorBoundary({ error }: { error: Error }) {
  return (
    <main className="container mx-auto rounded-lg h-full grid grid-rows-layout p-4 pb-0 sm:p-8 sm:pb-0 max-w-full sm:max-w-auto">
      <div className="chat-container">
        <div className="intro grid place-items-center h-full text-center">
          <div className="intro-content inline-block px-4 py-8 border border-error rounded-lg">
            <h1 className="text-3xl font-semibold">Oops, something went wrong!</h1>
            <p className="mt-4 text-error">{error.message}</p>
            <p className="mt-4"><Link to="/">Back to chat</Link></p>
          </div>
        </div>
      </div>
    </main>
  );
}