import React from 'react';

interface SendProps {
  className?: string;
}

const Send: React.FC<SendProps> = ({ className }) => (
    <svg width="16" height="16" viewBox="0 0 400 400" fill="none" xmlns="http://www.w3.org/2000/svg" className={`transition-transform duration-300 ${className || ''}`}>
      <path fillRule="evenodd" clipRule="evenodd" d="M363.455 185.809L51.6551 29.2563C37.6546 24.8007 24.2931 32.4373 27.4739 48.3498L72.0164 167.997L262.915 199.183L72.0164 231.004L27.4739 350.652C24.2934 366.56 37.6546 374.197 51.6551 369.745L363.455 212.558C376.182 207.467 376.182 191.558 363.455 185.827V185.809Z" fill="currentColor" className="fill-current transition-colors group-disabled:fill-[#909090]"/>
    </svg>
  );
  
  export default Send;