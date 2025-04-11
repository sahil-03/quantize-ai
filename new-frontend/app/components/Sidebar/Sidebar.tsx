import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Box, Button, TextField, Typography, CircularProgress, Alert, FormControl, InputLabel, Select, MenuItem } from '@mui/material';

export default function Sidebar() {
  const [selectedModel, setSelectedModel] = useState('claude-3-5-sonnet');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedKeyPaths, setSelectedKeyPaths] = useState<File | null>(null);
  const [sidebarWidth, setSidebarWidth] = useState(350);
  const [isDragging, setIsDragging] = useState(false);
  const [ipAddress, setIpAddress] = useState('');
  const [huggingFaceLink, setHuggingFaceLink] = useState('');
  const [huggingFaceToken, setHuggingFaceToken] = useState('');
  const [sshUser, setSSHUser] = useState('');
  const [deploymentStatus, setDeploymentStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [deploymentMessage, setDeploymentMessage] = useState('');
  const [sshKeyFile, setSshKeyFile] = useState<File | null>(null);
  const [sshKeyFileName, setSshKeyFileName] = useState<string>('No file selected');
  const [serverDropdownOpen, setServerDropdownOpen] = useState<boolean>(true);
  const [modelDropdownOpen, setModelDropdownOpen] = useState<boolean>(true);
  const [modelSource, setModelSource] = useState<'huggingface' | 'local'>('huggingface');
  const sidebarRef = useRef<HTMLDivElement>(null);
  const minWidth = 200;
  const maxWidth = 800;

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>, type: 'file' | 'sshKey') => {
    const file = event.target.files?.[0];
    if (file) {
      if (type === 'file') {
        setSelectedFile(file);
        console.log('File selected:', file.name);
      } else {
        setSshKeyFile(file);
        setSshKeyFileName(file.name);
        console.log('SSH key selected:', file.name);
      }
    }
  };

  const handleModelChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedModel(event.target.value);
  };

  const handleIpAddressChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setIpAddress(event.target.value);
  };

  const handleHuggingFaceLinkChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setHuggingFaceLink(event.target.value);
  };

  const handleHuggingFaceTokenChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setHuggingFaceToken(event.target.value);
  };

  const handleSSHUserChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSSHUser(event.target.value);
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;
    
    const newWidth = e.clientX;
    
    if (newWidth >= minWidth && newWidth <= maxWidth) {
      setSidebarWidth(newWidth);
    }
  }, [isDragging, minWidth, maxWidth]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const toggleServerDropdown = () => {
    setServerDropdownOpen(!serverDropdownOpen);
  };

  const toggleModelDropdown = () => {
    setModelDropdownOpen(!modelDropdownOpen);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.classList.add('resize-cursor');
  };

  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.classList.remove('resize-cursor');
    };
  }, [handleMouseMove, handleMouseUp]);

  const handleConnect = async () => {
    try {
      setDeploymentStatus('loading');
      setDeploymentMessage('Preparing deployment data...');
      
      // First, transfer the SSH key to the server if one was uploaded
      let sshKeyPath = "~/.ssh/id_rsa"; // Default fallback path
      
      if (sshKeyFile) {
        setDeploymentMessage('Uploading SSH key...');
        
        // Create a FormData object to send the file
        const formData = new FormData();
        formData.append('sshKey', sshKeyFile);
        
        try {
          // Create an endpoint on the server to handle file uploads
          const uploadResponse = await fetch('http://localhost:8000/upload-ssh-key', {
            method: 'POST',
            body: formData,
          });
          
          if (!uploadResponse.ok) {
            const errorText = await uploadResponse.text();
            throw new Error(`SSH key upload failed: ${errorText || ''}`);
          }
          
          const uploadResult = await uploadResponse.json();
          console.log('SSH key upload result:', uploadResult);
          
          if (uploadResult.status === 'error') {
            throw new Error(uploadResult.message);
          }
          
          // Use the path returned by the server
          sshKeyPath = uploadResult.key_path;
          setDeploymentMessage('SSH key uploaded successfully. Preparing deployment...');
        } catch (uploadError) {
          console.error('SSH key upload error:', uploadError);
          setDeploymentMessage(`SSH key upload failed: ${uploadError.message}. Using default key path.`);
          // Continue with deployment using the default key path
        }
      } else {
        // If no SSH key was uploaded, try to transfer the default one
        setDeploymentMessage('Using default SSH key...');
      }
      
      // Validate required fields
      if (!ipAddress) {
        setDeploymentStatus('error');
        setDeploymentMessage('Server IP address is required');
        return;
      }
      
      // Validate model source specific fields
      if (modelSource === 'huggingface') {
        if (!huggingFaceLink) {
          setDeploymentStatus('error');
          setDeploymentMessage('HuggingFace model link is required');
          return;
        }
      } else {
        // Local model
        if (!selectedFile) {
          setDeploymentStatus('error');
          setDeploymentMessage('Please upload a model file');
          return;
        }
      }
      
      // Use default SSH user if not provided
      const sshUserValue = sshUser || 'root';
      
      // Prepare data object matching the DeploymentConfig expected by the server
      const deploymentConfig: any = {
        host: ipAddress,
        ssh_user: sshUserValue,
        ssh_key: sshKeyPath,
        model_source: modelSource
      };
      
      // Add source-specific configuration
      if (modelSource === 'huggingface') {
        deploymentConfig.hf = huggingFaceLink;
        deploymentConfig.hf_token = huggingFaceToken || "";
      }
      
      // For local model, we'll need to upload the file first
      if (modelSource === 'local' && selectedFile) {
        setDeploymentMessage('Uploading model file...');
        
        // Create a FormData object to send the file
        const formData = new FormData();
        formData.append('model_file', selectedFile);
        
        try {
          // Upload the model file to the server
          const uploadResponse = await fetch('http://localhost:8000/upload-model-file', {
            method: 'POST',
            body: formData,
          });
          
          if (!uploadResponse.ok) {
            const errorText = await uploadResponse.text();
            throw new Error(`Model file upload failed: ${errorText || ''}`);
          }
          
          const uploadResult = await uploadResponse.json();
          console.log('Model file upload result:', uploadResult);
          
          if (uploadResult.status === 'error') {
            throw new Error(uploadResult.message);
          }
          
          // Add the model file path to the deployment config
          deploymentConfig.model_file_path = uploadResult.file_path;
          setDeploymentMessage('Model file uploaded successfully. Preparing deployment...');
        } catch (uploadError) {
          console.error('Model file upload error:', uploadError);
          setDeploymentStatus('error');
          setDeploymentMessage(`Model file upload failed: ${uploadError.message}`);
          return;
        }
      }
      
      // Set up server URL for the deployment endpoint
      const deploymentServerUrl = 'http://localhost:8000/deploy';
      
      setDeploymentMessage('Sending data to deployment server...');
      
      // Create an AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
      
      try {
        // Send the data to the deployment server with timeout
        const response = await fetch(deploymentServerUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(deploymentConfig),
          signal: controller.signal,
        });
        
        // Clear the timeout since the request completed
        clearTimeout(timeoutId);
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Deployment failed with status: ${response.status}. ${errorText || ''}`);
        }
        
        const result = await response.json();
        
        // Update the UI with success
        setDeploymentStatus('success');
        setDeploymentMessage(result.Response || 'Deployment initiated successfully!');
        
        console.log('Deployment initiated:', result);
        
        // Also set up the query endpoint for the chat interface
        let queryServerUrl = ipAddress;
        if (!queryServerUrl.startsWith('http://') && !queryServerUrl.startsWith('https://')) {
          queryServerUrl = `http://${queryServerUrl}`;
        }
        
        if (!queryServerUrl.endsWith('/query')) {
          queryServerUrl = `${queryServerUrl}/query`;
        }
        
        const event = new CustomEvent('serverUrlChange', {
          detail: { serverUrl: queryServerUrl }
        });
        window.dispatchEvent(event);
      } catch (fetchError) {
        // Clear the timeout if there was an error
        clearTimeout(timeoutId);
        throw fetchError;
      }
      
    } catch (error) {
      console.error('Detailed deployment error:', error);
      
      // Provide more specific error messages based on error type
      if (error.name === 'AbortError') {
        setDeploymentStatus('error');
        setDeploymentMessage('Connection timed out. The server might be down or unreachable.');
      } else if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        setDeploymentStatus('error');
        setDeploymentMessage('Network error: Could not connect to the deployment server. Please check if the server is running and accessible.');
      } else {
        setDeploymentStatus('error');
        setDeploymentMessage(error instanceof Error ? 
          `Deployment failed: ${error.message}` : 
          'An unknown error occurred during deployment');
      }
      
      // Try to ping the server to check if it's reachable
      try {
        const pingController = new AbortController();
        const pingTimeoutId = setTimeout(() => pingController.abort(), 5000);
        
        fetch('http://localhost:8000/health', { 
          method: 'GET',
          signal: pingController.signal
        })
          .then(response => {
            clearTimeout(pingTimeoutId);
            if (response.ok) {
              console.log('Server is reachable, but deployment endpoint failed');
            }
          })
          .catch(pingError => {
            clearTimeout(pingTimeoutId);
            console.error('Server ping failed:', pingError);
          });
      } catch (pingError) {
        console.error('Error while pinging server:', pingError);
      }
    }
  };

  return (
    <div className="flex h-full relative">
      <aside 
        ref={sidebarRef}
        style={{ width: `${sidebarWidth}px` }}
        className="h-screen bg-background border-r border-input p-6 flex flex-col gap-6 overflow-y-auto"
      >
        <div className="flex flex-col h-full p-4 space-y-4 overflow-y-auto">
          <div className="flex items-center gap-2 mb-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6 text-primary">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
            <h1 className="text-xl font-semibold text-text-primary">Quantize AI</h1>
          </div>
          
          {/* <h2 className="text-lg font-semibold text-text-primary">🚀 Deploy Model</h2> */}
          
          {/* Server Connection Dropdown */}
          <div className="border border-border rounded-md overflow-hidden">
            <button 
              className="w-full flex justify-between items-center p-3 bg-background-secondary text-text-primary hover:bg-background-tertiary"
              onClick={toggleServerDropdown}
            >
              <span className="font-medium">🖥️ Server Connection</span>
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                className={`h-5 w-5 transition-transform ${serverDropdownOpen ? 'transform rotate-180' : ''}`} 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {serverDropdownOpen && (
              <div className="p-3 space-y-3 border-t border-border">
                <div className="space-y-2">
                  <label htmlFor="ip-address" className="block text-sm font-medium text-text-secondary">
                    Server IP Address
                  </label>
                  <input
                    id="ip-address"
                    type="text"
                    value={ipAddress}
                    onChange={handleIpAddressChange}
                    placeholder="0.0.0.0"
                    className="input w-full"
                    aria-label="IP address"
                  />
                </div>
                
                <div className="space-y-2">
                  <label htmlFor="ssh-username" className="block text-sm font-medium text-text-secondary">
                    SSH Username
                  </label>
                  <input
                    id="ssh-username"
                    type="text"
                    value={sshUser}
                    onChange={handleSSHUserChange}
                    placeholder="ubuntu"
                    className="input w-full"
                  />
                </div>
                
                <div className="space-y-2">
                  <label htmlFor="ssh-key-upload" className="block text-sm font-medium text-text-secondary">
                    Upload SSH Key
                  </label>
                  <div className="flex flex-col gap-2">
                    <input
                      id="ssh-key-upload"
                      type="file"
                      onChange={(e) => handleFileSelect(e, 'sshKey')}
                      className="block w-full text-sm text-text-secondary
                        file:mr-4 file:py-2 file:px-4
                        file:rounded-md file:border-0
                        file:text-sm file:font-medium
                        file:bg-primary/10 file:text-primary
                        hover:file:bg-primary/20 cursor-pointer"
                    />
                    {sshKeyFileName !== 'No file selected' && (
                      <p className="text-sm text-text-secondary flex items-center gap-1">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 text-success">
                          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                          <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                        {sshKeyFileName}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
          
          {/* Model Configuration Dropdown */}
          <div className="border border-border rounded-md overflow-hidden">
            <button 
              className="w-full flex justify-between items-center p-3 bg-background-secondary text-text-primary hover:bg-background-tertiary"
              onClick={toggleModelDropdown}
            >
              <span className="font-medium">Model Configuration</span>
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                className={`h-5 w-5 transition-transform ${modelDropdownOpen ? 'transform rotate-180' : ''}`} 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {modelDropdownOpen && (
              <div className="p-3 space-y-3 border-t border-border">
                {/* Toggle switch for model source */}
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-text-secondary">Model Source</span>
                  <div className="flex items-center space-x-2">
                    <span className={`text-xs ${modelSource === 'huggingface' ? 'text-primary font-medium' : 'text-text-tertiary'}`}>
                      🤗
                    </span>
                    <button 
                      onClick={() => setModelSource(modelSource === 'huggingface' ? 'local' : 'huggingface')}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full border ${
                        modelSource === 'local' 
                          ? 'bg-primary border-primary' 
                          : 'bg-background-tertiary border-border'
                      }`}
                      aria-label={`Switch to ${modelSource === 'huggingface' ? 'local' : 'huggingface'} model source`}
                    >
                      <span 
                        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${
                          modelSource === 'local' ? 'translate-x-5' : 'translate-x-1'
                        }`} 
                      />
                    </button>
                    <span className={`text-xs ${modelSource === 'local' ? 'text-primary font-medium' : 'text-text-tertiary'}`}>
                      💻
                    </span>
                  </div>
                </div>

                {/* Conditional rendering based on model source */}
                {modelSource === 'huggingface' ? (
                  <>
                    <div className="space-y-2">
                      <label htmlFor="huggingface-token" className="block text-sm font-medium text-text-secondary">
                        🤗 HuggingFace Token
                      </label>
                      <input
                        id="huggingface-token"
                        type="text"
                        value={huggingFaceToken}
                        onChange={handleHuggingFaceTokenChange}
                        placeholder="hf_..."
                        className="input w-full"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <label htmlFor="huggingface-link" className="block text-sm font-medium text-text-secondary">
                        🤗 HuggingFace Model Link
                      </label>
                      <input
                        id="huggingface-link"
                        type="text"
                        value={huggingFaceLink}
                        onChange={handleHuggingFaceLinkChange}
                        placeholder="https://huggingface.co/..."
                        className="input w-full"
                      />
                    </div>
                  </>
                ) : (
                  <div className="space-y-2">
                    <label htmlFor="file-upload" className="block text-sm font-medium text-text-secondary">
                      💻 Upload Model File
                    </label>
                    <div className="flex flex-col gap-2">
                      <input
                        id="file-upload"
                        type="file"
                        onChange={(e) => handleFileSelect(e, 'file')}
                        className="block w-full text-sm text-text-secondary
                          file:mr-4 file:py-2 file:px-4
                          file:rounded-md file:border-0
                          file:text-sm file:font-medium
                          file:bg-primary/10 file:text-primary
                          hover:file:bg-primary/20 cursor-pointer"
                      />
                      {selectedFile && (
                        <p className="text-sm text-text-secondary flex items-center gap-1">
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 text-success">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                            <polyline points="22 4 12 14.01 9 11.01"></polyline>
                          </svg>
                          {selectedFile.name}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* Deployment Status */}
          {deploymentStatus !== 'idle' && (
            <div className={`p-4 rounded-md ${
              deploymentStatus === 'loading' ? 'bg-info/10 text-info' :
              deploymentStatus === 'success' ? 'bg-success/10 text-success' :
              'bg-error/10 text-error'
            }`}>
              <div className="flex items-center gap-2">
                {deploymentStatus === 'loading' && (
                  <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"></div>
                )}
                <p>{deploymentMessage}</p>
              </div>
            </div>
          )}
          
          <button
            className="btn btn-primary mt-auto"
            onClick={handleConnect}
            disabled={deploymentStatus === 'loading'}
          >
            {deploymentStatus === 'loading' ? '🚀 Deploying...' : '🚀 Deploy Model'}
          </button>
        </div>
      </aside>
      
      <button 
        className="w-4 cursor-col-resize h-full absolute top-0 z-20 flex items-center justify-center focus:outline-none hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
        onMouseDown={handleMouseDown}
        style={{ left: `${sidebarWidth - 2}px` }}
        aria-label="Resize sidebar"
        tabIndex={0}
      >
        <div className="h-full w-full flex items-center justify-center">
          <div className="w-px h-16 bg-gray-200 dark:bg-gray-700"></div>
        </div>
      </button>
    </div>
  );
}