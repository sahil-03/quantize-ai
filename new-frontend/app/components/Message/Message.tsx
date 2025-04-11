import { useRef, useState, useLayoutEffect } from 'react';
import { Role } from "../../types";
import Robot from '../LoadingDots/Robot';

export interface MessageProps {
  content: string;
  key?: string;
  role?: Role;
  error?: boolean;
  thinking?: boolean;
}

export default function Message({ content, error, role = 'User', thinking = false }: MessageProps) {
  const rendered = useRef<boolean>(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const [messageHeight, setMessageHeight] = useState<number | null>(null);
  const transitionHandler = useRef<(() => void) | null>(null);
  
  // Determine message type for styling and accessibility
  const isUserMessage = role === 'User';
  const isAssistantMessage = role === 'Assistant';
  const messageType = isUserMessage ? 'user' : 'assistant';

  // Calculate height for smooth animation
  useLayoutEffect(() => {
    if (rendered.current || !contentRef.current) {
      return;
    }

    rendered.current = true;
    const element = contentRef.current;
    const height = element.scrollHeight;

    if (height > 0) {
      setMessageHeight(height);
    }
  }, []);

  // Handle transition end to remove fixed height
  useLayoutEffect(() => {
    if (!contentRef.current) return;

    transitionHandler.current = () => {
      // After animation completes, remove fixed height to allow for content changes
      setMessageHeight(null);
    };

    const element = contentRef.current;
    const handler = transitionHandler.current;

    if (handler) {
      element.addEventListener('transitionend', handler);
    }

    return () => {
      if (handler) {
        element?.removeEventListener('transitionend', handler);
      }
    };
  }, []);

  // Render content based on message type
  const renderContent = () => {
    if (thinking) {
      return <Robot />;
    }
    
    if (error) {
      return (
        <div className="flex items-start gap-2 text-error">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 flex-shrink-0 mt-0.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <div style={{ whiteSpace: 'pre-wrap' }}>{content}</div>
        </div>
      );
    }
    
    return (
      <div style={{ whiteSpace: 'pre-wrap' }}>
        {content}
      </div>
    );
  };

  useLayoutEffect(() => {
    if (contentRef.current) {
      const element = contentRef.current;
      const height = element.scrollHeight;

      if (height > 0) {
        setMessageHeight(height);
      }
    }
  }, [content]);

  return (
    <div
      className={`message message-${messageType} ${error ? 'message-error' : ''} animate-fade-in`}
      aria-live={isAssistantMessage ? "polite" : "off"}
      aria-label={`${messageType} message${error ? ' with error' : ''}`}
    >
      <div 
        className="message-bubble"
        ref={contentRef}
        style={{ 
          height: messageHeight !== null ? `${messageHeight}px` : 'auto',
          overflow: messageHeight !== null ? 'hidden' : 'visible'
        }}
      >
        {renderContent()}
      </div>
    </div>
  );
}