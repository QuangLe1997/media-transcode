import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiService } from '../api';
import MediaFilter from './MediaFilter';
import ConfirmModal from './ConfirmModal';

const TaskDetails = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedProfiles, setExpandedProfiles] = useState({});
  const [expandedErrors, setExpandedErrors] = useState({});
  const [fileMetadata, setFileMetadata] = useState({});
  const [filteredOutputs, setFilteredOutputs] = useState(null);
  const [copyingResult, setCopyingResult] = useState(false);
  
  // Modal states
  const [showRetryModal, setShowRetryModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [retryDeleteFiles, setRetryDeleteFiles] = useState(false);
  const [deleteTaskFiles, setDeleteTaskFiles] = useState(false);

  // Copy task result as JSON
  const copyTaskResult = async () => {
    setCopyingResult(true);
    try {
      const result = await apiService.getTaskResult(taskId);
      const jsonString = JSON.stringify(result, null, 2);
      
      // Try modern clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(jsonString);
      } else {
        // Fallback for older browsers or HTTP sites
        const textArea = document.createElement('textarea');
        textArea.value = jsonString;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);
        
        if (!successful) {
          throw new Error('execCommand copy failed');
        }
      }
      
      // Show success message briefly
      const originalText = 'Copy JSON Result';
      const button = document.querySelector('.copy-result-btn');
      if (button) {
        button.textContent = '✅ Copied!';
        setTimeout(() => {
          button.textContent = originalText;
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to copy result:', err);
      
      // Show JSON in a modal/alert as last resort
      const result = await apiService.getTaskResult(taskId);
      const jsonString = JSON.stringify(result, null, 2);
      
      // Create a modal to display the JSON
      const modal = document.createElement('div');
      modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
      `;
      
      const content = document.createElement('div');
      content.style.cssText = `
        background: white;
        padding: 20px;
        border-radius: 8px;
        max-width: 80%;
        max-height: 80%;
        overflow: auto;
      `;
      
      content.innerHTML = `
        <h3>Task Result JSON (Copy manually)</h3>
        <textarea readonly style="width: 100%; height: 400px; font-family: monospace; font-size: 12px;">${jsonString}</textarea>
        <div style="margin-top: 10px; text-align: right;">
          <button onclick="this.closest('.modal').remove()" style="padding: 8px 16px; background: #f56565; color: white; border: none; border-radius: 4px; cursor: pointer;">Close</button>
        </div>
      `;
      
      modal.className = 'modal';
      modal.appendChild(content);
      document.body.appendChild(modal);
      
      // Select all text in textarea for easy copying
      const textarea = content.querySelector('textarea');
      textarea.focus();
      textarea.select();
      
    } finally {
      setCopyingResult(false);
    }
  };

  // Get file metadata from URL
  const getFileMetadata = useCallback(async (url, fileKey) => {
    if (fileMetadata[fileKey]) {
      return fileMetadata[fileKey];
    }

    try {
      // First try to get file size from HEAD request
      const response = await fetch(url, { method: 'HEAD' });
      const size = response.headers.get('content-length');
      
      const metadata = {
        size: size ? parseInt(size) : null,
        dimensions: null,
        duration: null,
        fps: null
      };

      setFileMetadata(prev => ({
        ...prev,
        [fileKey]: metadata
      }));

      return metadata;
    } catch (err) {
      console.warn('Failed to get file metadata:', err);
      return {
        size: null,
        dimensions: null,
        duration: null,
        fps: null
      };
    }
  }, [fileMetadata]);

  // Enhanced function to get video metadata using MediaInfo or probe
  const getEnhancedVideoMetadata = useCallback(async (videoElement, fileKey) => {
    try {
      // Debug info available but commented out to reduce console noise

      // Check if dimensions are valid
      if (!videoElement.videoWidth || !videoElement.videoHeight || isNaN(videoElement.videoWidth) || isNaN(videoElement.videoHeight)) {
        console.warn(`❌ Invalid video dimensions for ${fileKey}:`, {
          videoWidth: videoElement.videoWidth,
          videoHeight: videoElement.videoHeight
        });
        return {
          dimensions: null,
          duration: videoElement.duration && !isNaN(videoElement.duration) ? Math.round(videoElement.duration) : null,
          fps: null
        };
      }

      // Use videoElement properties
      const basicMetadata = {
        dimensions: `${videoElement.videoWidth}×${videoElement.videoHeight}`,
        duration: videoElement.duration && !isNaN(videoElement.duration) ? Math.round(videoElement.duration) : null,
        fps: null
      };

      // console.log(`✅ Valid metadata extracted for ${fileKey}:`, basicMetadata);

      // Try to get FPS from video tracks if available
      if (videoElement.captureStream) {
        try {
          const stream = videoElement.captureStream();
          const tracks = stream.getVideoTracks();
          if (tracks.length > 0) {
            const settings = tracks[0].getSettings();
            if (settings.frameRate) {
              basicMetadata.fps = Math.round(settings.frameRate);
            }
          }
        } catch (e) {
          console.log('Cannot get frameRate from captureStream:', e);
        }
      }

      // Fallback: estimate FPS based on common patterns and duration
      if (!basicMetadata.fps && basicMetadata.duration > 0) {
        // Try to estimate based on profile name patterns
        const profileMatch = fileKey.match(/(fps|FPS)[\D]*(\d+)/);
        if (profileMatch) {
          basicMetadata.fps = parseInt(profileMatch[2]);
        } else {
          // Default estimations based on video type
          if (fileKey.includes('thumbs') || fileKey.includes('preview')) {
            basicMetadata.fps = 15; // Usually lower FPS for thumbnails
          } else if (fileKey.includes('high')) {
            basicMetadata.fps = 30; // High quality usually 30fps
          } else if (fileKey.includes('gif')) {
            basicMetadata.fps = 10; // GIFs usually 10fps
          } else {
            basicMetadata.fps = 25; // Standard default
          }
        }
      }

      return basicMetadata;
    } catch (error) {
      console.warn('Error getting enhanced video metadata:', error);
      return {
        dimensions: videoElement.videoWidth && videoElement.videoHeight && !isNaN(videoElement.videoWidth) && !isNaN(videoElement.videoHeight) 
          ? `${videoElement.videoWidth}×${videoElement.videoHeight}` 
          : null,
        duration: videoElement.duration && !isNaN(videoElement.duration) ? Math.round(videoElement.duration) : null,
        fps: null
      };
    }
  }, []);

  const loadTaskDetails = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getTask(taskId);
      
      
      setTask(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load task details:', err);
      let errorMessage = 'Failed to load task details';
      
      if (err.response) {
        const status = err.response.status;
        const detail = err.response?.data?.detail || err.response?.data?.message;
        
        if (status === 404) {
          errorMessage = '📭 Task not found or has been deleted.';
        } else if (status === 500) {
          errorMessage = '🔧 Server error while loading task details.';
        } else {
          errorMessage = `❌ Failed to load task: ${detail || `Server error (${status})`}`;
        }
      } else if (err.request) {
        errorMessage = '🌐 Network error. Please check your connection.';
      } else {
        errorMessage = `❌ ${err.message || 'Unexpected error occurred'}`;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    if (taskId) {
      loadTaskDetails();
    }
  }, [taskId, loadTaskDetails]);

  // Process file metadata from backend response
  useEffect(() => {
    if (task?.outputs) {
      Object.entries(task.outputs).forEach(([profile, urlItems]) => {
        const urlList = Array.isArray(urlItems) ? urlItems : [urlItems];
        urlList.forEach((urlItem, index) => {
          const fileKey = `${profile}-${index}`;
          
          // Check if urlItem is enhanced object with metadata or just URL string
          if (typeof urlItem === 'object' && urlItem.url) {
            // Backend provided enhanced object with metadata from consumer
            const backendMetadata = urlItem.metadata || {};
            const metadata = {
              size: backendMetadata.file_size || urlItem.size, // Try new format first, fallback to old
              dimensions: backendMetadata.dimensions,
              duration: backendMetadata.duration,
              fps: backendMetadata.fps
            };
            
            // console.log(`📊 Backend metadata for ${fileKey}:`, metadata);
            
            setFileMetadata(prev => ({
              ...prev,
              [fileKey]: metadata
            }));
            
            // Try to infer FPS from profile config if available
            if (task.profiles) {
              const matchingProfile = task.profiles.find(p => p.id === profile || p.display_name === profile);
              if (matchingProfile && matchingProfile.full_config) {
                const config = matchingProfile.full_config;
                let inferredFPS = null;
                
                // Try to get FPS from video_config
                if (config.video_config?.fps) {
                  inferredFPS = config.video_config.fps;
                } else if (config.video_config?.max_fps) {
                  inferredFPS = config.video_config.max_fps;
                } else if (config.gif_config?.fps) {
                  inferredFPS = config.gif_config.fps;
                }
                
                if (inferredFPS) {
                  setFileMetadata(prev => ({
                    ...prev,
                    [fileKey]: {
                      ...prev[fileKey],
                      fps: inferredFPS
                    }
                  }));
                }
              }
            }
          } else {
            // Fallback to original method for plain URL
            getFileMetadata(urlItem, fileKey);
          }
        });
      });
    }
  }, [task?.outputs, task?.profiles, getFileMetadata]);

  const getFileName = (url) => {
    return url.split('/').pop().split('?')[0];
  };

  const getFileType = (url) => {
    const ext = url.split('.').pop().toLowerCase();
    if (['mp4', 'webm', 'avi', 'mov', 'mkv'].includes(ext)) return 'video';
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return 'image';
    return 'file';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (status) => {
    const colors = {
      completed: '#48bb78',
      processing: '#4299e1',
      failed: '#f56565',
      pending: '#ed8936'
    };
    return colors[status] || '#666';
  };

  const getStatusIcon = (status) => {
    const icons = {
      completed: '✅',
      processing: '⚙️',
      failed: '❌',
      pending: '⏳'
    };
    return icons[status] || '📄';
  };

  const getProfileTypeInfo = (profileId) => {
    // Determine profile type from ID
    if (profileId.startsWith('main_')) {
      return { type: 'Main Video', color: '#4299e1', icon: '🎬' };
    } else if (profileId.startsWith('preview_')) {
      return { type: 'Preview', color: '#ed8936', icon: '👁️' };
    } else if (profileId.startsWith('thumb_')) {
      return { type: 'Thumbnail', color: '#48bb78', icon: '🖼️' };
    } else if (profileId.startsWith('img_')) {
      return { type: 'Image', color: '#9f7aea', icon: '🖼️' };
    } else {
      return { type: 'Other', color: '#718096', icon: '📄' };
    }
  };

  const toggleProfileExpanded = (profileId) => {
    setExpandedProfiles(prev => ({
      ...prev,
      [profileId]: !prev[profileId]
    }));
  };

  const toggleErrorExpanded = (profileId) => {
    setExpandedErrors(prev => ({
      ...prev,
      [profileId]: !prev[profileId]
    }));
  };

  const copyToClipboard = async (text, profileId) => {
    try {
      await navigator.clipboard.writeText(text);
      // Hiển thị feedback tạm thời
      const button = document.getElementById(`copy-btn-${profileId}`);
      if (button) {
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        button.style.color = '#38a169';
        setTimeout(() => {
          button.textContent = originalText;
          button.style.color = '#4a5568';
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to copy text: ', err);
      // Fallback cho browsers không support clipboard API
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  };

  // Get video metadata when video loads
  const handleVideoLoadedMetadata = async (videoElement, fileKey) => {
    try {
      // Video metadata available but logged only when needed

      const enhancedMetadata = await getEnhancedVideoMetadata(videoElement, fileKey);
      
      // console.log(`📊 Enhanced metadata for ${fileKey}:`, enhancedMetadata);

      setFileMetadata(prev => ({
        ...prev,
        [fileKey]: {
          ...prev[fileKey],
          ...enhancedMetadata
        }
      }));
    } catch (error) {
      console.warn('Error in handleVideoLoadedMetadata:', error);
      
      // Fallback to basic metadata
      const basicMetadata = {
        dimensions: `${videoElement.videoWidth}×${videoElement.videoHeight}`,
        duration: Math.round(videoElement.duration),
        fps: null
      };

      // console.log(`🔧 Fallback metadata for ${fileKey}:`, basicMetadata);

      setFileMetadata(prev => ({
        ...prev,
        [fileKey]: {
          ...prev[fileKey],
          ...basicMetadata
        }
      }));
    }
  };

  // Get image metadata when image loads
  const handleImageLoad = (imgElement, fileKey) => {
    const metadata = {
      dimensions: `${imgElement.naturalWidth}×${imgElement.naturalHeight}`
    };

    // console.log(`🖼️ Image metadata for ${fileKey}:`, imgElement.naturalWidth, imgElement.naturalHeight);

    setFileMetadata(prev => ({
      ...prev,
      [fileKey]: {
        ...prev[fileKey],
        ...metadata
      }
    }));
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  // Format duration
  const formatDuration = (seconds) => {
    if (!seconds) return null;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins > 0 ? `${mins}:${secs.toString().padStart(2, '0')}` : `${secs}s`;
  };

  // Format FPS with appropriate suffix
  const formatFPS = (fps) => {
    if (!fps) return null;
    return `${fps} fps`;
  };

  // Format dimensions with better display
  const formatDimensions = (dimensions) => {
    if (!dimensions) return null;
    return dimensions; // Already formatted as "1920×1080"
  };

  const truncateError = (errorMessage, maxLines = 3) => {
    if (!errorMessage) return 'No error message available';
    
    const lines = errorMessage.split('\n');
    if (lines.length <= maxLines) return errorMessage;
    
    return lines.slice(0, maxLines).join('\n');
  };

  const renderProfileConfigDetails = (profile) => {
    if (!profile.full_config) return null;
    
    const config = profile.full_config;
    const outputType = profile.output_type;
    
    return (
      <div style={{
        marginTop: '12px',
        padding: '12px',
        background: '#f7fafc',
        borderRadius: '6px',
        border: '1px solid #e2e8f0',
        fontSize: '0.85rem'
      }}>
        <div style={{ fontWeight: '600', marginBottom: '8px', color: '#2d3748' }}>
          Configuration Details:
        </div>
        
        {outputType === 'video' && config.video_config && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '6px' }}>
            {config.video_config.codec && (
              <div><strong>Codec:</strong> {config.video_config.codec}</div>
            )}
            {(config.video_config.max_width || config.video_config.max_height) && (
              <div><strong>Max Resolution:</strong> {config.video_config.max_width || 'auto'}x{config.video_config.max_height || 'auto'}</div>
            )}
            {config.video_config.bitrate && (
              <div><strong>Bitrate:</strong> {config.video_config.bitrate}</div>
            )}
            {config.video_config.fps && (
              <div><strong>FPS:</strong> {config.video_config.fps}</div>
            )}
            {config.video_config.preset && (
              <div><strong>Preset:</strong> {config.video_config.preset}</div>
            )}
            {config.video_config.crf && (
              <div><strong>CRF:</strong> {config.video_config.crf}</div>
            )}
          </div>
        )}
        
        {outputType === 'image' && config.image_config && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '6px' }}>
            {config.image_config.format && (
              <div><strong>Format:</strong> {config.image_config.format}</div>
            )}
            {config.image_config.quality && (
              <div><strong>Quality:</strong> {config.image_config.quality}%</div>
            )}
            {(config.image_config.max_width || config.image_config.max_height) && (
              <div><strong>Max Size:</strong> {config.image_config.max_width || 'auto'}x{config.image_config.max_height || 'auto'}</div>
            )}
            {config.image_config.extract_time && (
              <div><strong>Extract Time:</strong> {config.image_config.extract_time}s</div>
            )}
          </div>
        )}
        
        {outputType === 'gif' && config.gif_config && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '6px' }}>
            {config.gif_config.fps && (
              <div><strong>FPS:</strong> {config.gif_config.fps}</div>
            )}
            {(config.gif_config.width || config.gif_config.height) && (
              <div><strong>Size:</strong> {config.gif_config.width || 'auto'}x{config.gif_config.height || 'auto'}</div>
            )}
            {config.gif_config.duration && (
              <div><strong>Duration:</strong> {config.gif_config.duration}s</div>
            )}
            {config.gif_config.quality && (
              <div><strong>Quality:</strong> {config.gif_config.quality}%</div>
            )}
            {config.gif_config.colors && (
              <div><strong>Colors:</strong> {config.gif_config.colors}</div>
            )}
          </div>
        )}
        
        {config.ffmpeg_args && (
          <div style={{ marginTop: '8px' }}>
            <strong>FFmpeg Args:</strong>
            <code style={{ 
              display: 'block', 
              marginTop: '4px', 
              padding: '8px', 
              background: '#2d3748', 
              color: '#f7fafc', 
              borderRadius: '4px',
              fontSize: '0.8rem',
              overflowX: 'auto'
            }}>
              {Array.isArray(config.ffmpeg_args) ? config.ffmpeg_args.join(' ') : config.ffmpeg_args}
            </code>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="card">
        <div className="loading" style={{ padding: '40px' }}>
          <div className="loading-spinner" style={{ width: '40px', height: '40px' }}></div>
          <h3 style={{ marginTop: '20px' }}>Loading task details...</h3>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '20px' }}>😕</div>
          <h3 style={{ color: '#f56565', marginBottom: '16px' }}>Error Loading Task</h3>
          <p style={{ color: '#666', marginBottom: '20px' }}>{error}</p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <button 
              className="btn" 
              onClick={() => navigate('/results')}
            >
              ← Back to Results
            </button>
            <button 
              className="btn btn-success" 
              onClick={loadTaskDetails}
            >
              🔄 Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '20px' }}>📭</div>
          <h3>Task not found</h3>
          <button 
            className="btn" 
            onClick={() => navigate('/results')}
            style={{ marginTop: '20px' }}
          >
            ← Back to Results
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        marginBottom: '20px',
        paddingBottom: '16px',
        borderBottom: '2px solid #e2e8f0'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '2rem' }}>{getStatusIcon(task.status)}</span>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#2d3748' }}>
              Task Details
            </h1>
            <div style={{ fontSize: '1rem', color: '#666', marginTop: '4px' }}>
              {getFileName(task.source_url)}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            className="btn" 
            onClick={() => navigate('/results')}
            style={{ fontSize: '0.9rem' }}
          >
            ← Back to Results
          </button>
          
          {/* Copy JSON Result button */}
          <button
            className="btn copy-result-btn"
            onClick={copyTaskResult}
            disabled={copyingResult}
            style={{
              fontSize: '0.9rem',
              background: '#4f46e5',
              color: 'white',
              opacity: copyingResult ? 0.6 : 1
            }}
          >
            {copyingResult ? '📋 Copying...' : '📋 Copy JSON Result'}
          </button>
          
          {/* Retry button */}
          <button
            onClick={() => setShowRetryModal(true)}
            style={{
              fontSize: '0.9rem',
              background: '#f59e0b',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '8px 12px',
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => e.target.style.background = '#d97706'}
            onMouseLeave={(e) => e.target.style.background = '#f59e0b'}
          >
            🔄 Retry Task
          </button>
          
          {/* Delete button */}
          <button
            onClick={() => setShowDeleteModal(true)}
            style={{
              fontSize: '0.9rem',
              background: '#dc2626',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '8px 12px',
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => e.target.style.background = '#b91c1c'}
            onMouseLeave={(e) => e.target.style.background = '#dc2626'}
          >
            🗑️ Delete Task
          </button>
        </div>
      </div>

      {/* Task Overview */}
      <div style={{ 
        background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)', 
        padding: '20px', 
        borderRadius: '8px',
        marginBottom: '24px',
        border: '1px solid #e2e8f0'
      }}>
        <h2 style={{ fontSize: '1.2rem', marginBottom: '16px', color: '#2d3748' }}>
          📋 Task Overview
        </h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '6px' }}>📋 Task ID</div>
            <code style={{ 
              background: '#fff', 
              padding: '8px 12px', 
              borderRadius: '6px', 
              fontSize: '0.9rem',
              display: 'block',
              border: '1px solid #e2e8f0'
            }}>
              {task.task_id}
            </code>
          </div>
          
          <div>
            <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '6px' }}>📁 Source File</div>
            <div style={{ 
              fontWeight: '500', 
              fontSize: '1rem',
              padding: '8px 12px',
              background: '#fff',
              borderRadius: '6px',
              border: '1px solid #e2e8f0'
            }}>
              {getFileName(task.source_url)}
            </div>
          </div>
          
          <div>
            <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '6px' }}>📊 Status</div>
            <div style={{
              padding: '8px 12px',
              background: '#fff',
              borderRadius: '6px',
              border: '1px solid #e2e8f0'
            }}>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 12px',
                borderRadius: '20px',
                fontSize: '0.85rem',
                fontWeight: '600',
                textTransform: 'uppercase',
                background: getStatusColor(task.status),
                color: 'white'
              }}>
                {getStatusIcon(task.status)} {task.status}
              </span>
            </div>
          </div>
          
          <div>
            <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '6px' }}>📅 Created</div>
            <div style={{ 
              fontSize: '0.95rem',
              padding: '8px 12px',
              background: '#fff',
              borderRadius: '6px',
              border: '1px solid #e2e8f0'
            }}>
              {formatDate(task.created_at)}
            </div>
          </div>
          
          {task.updated_at && (
            <div>
              <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '6px' }}>🔄 Updated</div>
              <div style={{ 
                fontSize: '0.95rem',
                padding: '8px 12px',
                background: '#fff',
                borderRadius: '6px',
                border: '1px solid #e2e8f0'
              }}>
                {formatDate(task.updated_at)}
              </div>
            </div>
          )}
          
          {task.expected_profiles > 0 && (
            <div>
              <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '6px' }}>⚙️ Progress</div>
              <div style={{
                padding: '8px 12px',
                background: '#fff',
                borderRadius: '6px',
                border: '1px solid #e2e8f0'
              }}>
                <div style={{ fontSize: '0.9rem', marginBottom: '8px' }}>
                  <span style={{ color: '#48bb78', fontWeight: '600' }}>{task.completed_profiles || 0}</span> completed, 
                  <span style={{ color: '#f56565', fontWeight: '600' }}> {task.failed_profiles_count || 0}</span> failed / 
                  <span style={{ fontWeight: '600' }}> {task.expected_profiles}</span> total
                </div>
                <div style={{ 
                  width: '100%', 
                  height: '8px', 
                  background: '#e2e8f0', 
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${task.completion_percentage || 0}%`,
                    height: '100%',
                    background: `linear-gradient(90deg, ${getStatusColor(task.status)}, ${getStatusColor(task.status)}dd)`,
                    transition: 'width 0.3s ease'
                  }}></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Face Detection Results */}
      {task.face_detection_status && (
        <div style={{ marginBottom: '24px' }}>
          <h2 style={{ 
            fontSize: '1.2rem', 
            marginBottom: '16px', 
            color: '#2d3748',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            🤖 Face Detection
            <span style={{
              background: task.face_detection_status === 'completed' ? '#e6fffa' : 
                         task.face_detection_status === 'failed' ? '#fed7d7' : '#fef5e7',
              color: task.face_detection_status === 'completed' ? '#2d7a6a' : 
                     task.face_detection_status === 'failed' ? '#c53030' : '#d69e2e',
              padding: '2px 10px',
              borderRadius: '12px',
              fontSize: '0.8rem',
              fontWeight: '600'
            }}>
              {task.face_detection_status}
            </span>
          </h2>

          <div style={{
            background: 'white',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            padding: '16px',
            borderLeft: `4px solid ${
              task.face_detection_status === 'completed' ? '#48bb78' : 
              task.face_detection_status === 'failed' ? '#f56565' : '#ed8936'
            }`
          }}>
            {task.face_detection_status === 'completed' && task.face_detection_results && (
              <div>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '16px'
                }}>
                  <span style={{ fontSize: '1.5rem' }}>✅</span>
                  <div>
                    <div style={{ fontWeight: '600', fontSize: '1rem', color: '#2d3748' }}>
                      Face Detection Completed
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#718096' }}>
                      {task.face_detection_results.faces?.length || 0} face groups detected
                    </div>
                  </div>
                </div>

                {task.face_detection_results.faces && task.face_detection_results.faces.length > 0 && (
                  <div>
                    <h3 style={{ 
                      fontSize: '1rem', 
                      marginBottom: '12px', 
                      color: '#4a5568' 
                    }}>
                      👥 Detected Faces ({task.face_detection_results.faces.length})
                    </h3>
                    
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
                      gap: '12px',
                      marginBottom: '16px'
                    }}>
                      {task.face_detection_results.faces.map((face, index) => (
                        <div key={index} style={{
                          background: '#f8f9fa',
                          border: '1px solid #e2e8f0',
                          borderRadius: '8px',
                          padding: '12px',
                          textAlign: 'center',
                          transition: 'all 0.2s ease',
                          cursor: 'pointer'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = 'translateY(-2px)';
                          e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = 'translateY(0)';
                          e.currentTarget.style.boxShadow = 'none';
                        }}
                        >
                          {(face.avatar_url || face.avatar) && (
                            <img
                              src={face.avatar_url || `data:image/jpeg;base64,${face.avatar}`}
                              alt={`Face ${face.name || index + 1}`}
                              style={{
                                width: '80px',
                                height: '80px',
                                borderRadius: '50%',
                                objectFit: 'cover',
                                border: '2px solid #e2e8f0',
                                marginBottom: '8px'
                              }}
                            />
                          )}
                          <div style={{
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            color: '#2d3748',
                            marginBottom: '4px'
                          }}>
                            {face.name || `Face ${index + 1}`}
                          </div>
                          <div style={{
                            fontSize: '0.7rem',
                            color: '#718096',
                            marginBottom: '2px'
                          }}>
                            {face.group_size || 1} appearances
                          </div>
                          {face.index !== undefined && (
                            <div style={{
                              fontSize: '0.65rem',
                              color: '#a0aec0',
                              marginBottom: '6px'
                            }}>
                              Index: {face.index}
                            </div>
                          )}
                          <div style={{
                            display: 'flex',
                            justifyContent: 'center',
                            gap: '4px',
                            fontSize: '0.7rem',
                            marginBottom: '6px'
                          }}>
                            {face.gender !== undefined && (
                              <span style={{
                                background: face.gender === 1 ? '#e6f3ff' : '#ffe6f3',
                                color: face.gender === 1 ? '#2b77e6' : '#e64980',
                                padding: '2px 6px',
                                borderRadius: '8px',
                                fontWeight: '500'
                              }}>
                                {face.gender === 1 ? '♂' : '♀'}
                              </span>
                            )}
                            {face.age && (
                              <span style={{
                                background: '#f0f9ff',
                                color: '#1e40af',
                                padding: '2px 6px',
                                borderRadius: '8px',
                                fontWeight: '500'
                              }}>
                                {face.age}y
                              </span>
                            )}
                          </div>
                          
                          {/* Advanced details for each face */}
                          <div style={{
                            fontSize: '0.65rem',
                            color: '#a0aec0',
                            borderTop: '1px solid #e2e8f0',
                            paddingTop: '6px',
                            lineHeight: '1.3'
                          }}>
                            {face.detector !== undefined && (
                              <div>Detector: {(face.detector * 100).toFixed(1)}%</div>
                            )}
                            {face.landmarker !== undefined && (
                              <div>Landmarker: {(face.landmarker * 100).toFixed(1)}%</div>
                            )}
                            <div style={{ marginTop: '4px', display: 'flex', gap: '8px', justifyContent: 'center' }}>
                              {face.avatar_url && (
                                <a href={face.avatar_url} target="_blank" rel="noopener noreferrer" 
                                   style={{ color: '#3182ce', textDecoration: 'none' }}>
                                  Avatar
                                </a>
                              )}
                              {face.face_image_url && (
                                <a href={face.face_image_url} target="_blank" rel="noopener noreferrer"
                                   style={{ color: '#3182ce', textDecoration: 'none' }}>
                                  Full
                                </a>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Position Change Detection Label */}
                    <div style={{
                      marginTop: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}>
                      <span style={{ fontSize: '0.85rem', color: '#4a5568', fontWeight: '600' }}>
                        Position Change Detection:
                      </span>
                      <span style={{
                        background: task.face_detection_results.is_change_index ? '#fff3cd' : '#e6fffa',
                        color: task.face_detection_results.is_change_index ? '#d69e2e' : '#2d7a6a',
                        padding: '4px 8px',
                        borderRadius: '12px',
                        fontSize: '0.8rem',
                        fontWeight: '500'
                      }}>
                        {task.face_detection_results.is_change_index ? 'Yes' : 'No'}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {task.face_detection_status === 'processing' && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <div className="loading-spinner" style={{ width: '20px', height: '20px' }}></div>
                <div>
                  <div style={{ fontWeight: '600', fontSize: '1rem', color: '#2d3748' }}>
                    Processing Face Detection...
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#718096' }}>
                    Analyzing video for faces and generating results
                  </div>
                </div>
              </div>
            )}

            {task.face_detection_status === 'failed' && (
              <div>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '12px'
                }}>
                  <span style={{ fontSize: '1.5rem' }}>❌</span>
                  <div>
                    <div style={{ fontWeight: '600', fontSize: '1rem', color: '#2d3748' }}>
                      Face Detection Failed
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#718096' }}>
                      An error occurred during face detection processing
                    </div>
                  </div>
                </div>

                {task.face_detection_error && (
                  <div style={{
                    background: '#fff5f5',
                    border: '1px solid #fed7d7',
                    borderRadius: '6px',
                    padding: '12px',
                    marginTop: '12px'
                  }}>
                    <div style={{
                      fontSize: '0.8rem',
                      fontWeight: '600',
                      color: '#c53030',
                      marginBottom: '6px'
                    }}>
                      Error Details:
                    </div>
                    <div style={{
                      fontSize: '0.8rem',
                      color: '#4a5568',
                      fontFamily: 'ui-monospace, SFMono-Regular, Monaco, Consolas, monospace',
                      whiteSpace: 'pre-wrap',
                      lineHeight: '1.4'
                    }}>
                      {task.face_detection_error}
                    </div>
                  </div>
                )}
              </div>
            )}

            {task.face_detection_status === 'pending' && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <span style={{ fontSize: '1.5rem' }}>⏳</span>
                <div>
                  <div style={{ fontWeight: '600', fontSize: '1rem', color: '#2d3748' }}>
                    Face Detection Pending
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#718096' }}>
                    Waiting for face detection worker to start processing
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Target Profiles */}
      {task.profiles?.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h2 style={{ 
            fontSize: '1.2rem', 
            marginBottom: '16px', 
            color: '#2d3748',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            🎯 Target Profiles
            <span style={{
              background: '#e6fffa',
              color: '#2d7a6a',
              padding: '2px 10px',
              borderRadius: '12px',
              fontSize: '0.8rem',
              fontWeight: '600'
            }}>
              {task.profiles.length} profiles
            </span>
          </h2>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', 
            gap: '16px' 
          }}>
            {task.profiles.map((profile, index) => {
              const profileString = typeof profile === 'string' ? profile : profile?.id || profile?.display_name || 'unknown';
              const profileInfo = getProfileTypeInfo(profileString);
              const isExpanded = expandedProfiles[profileString];
              
              // Check if this profile is failed
              const isFailedProfile = task.failed_profiles && task.failed_profiles[profileString];
              const failedInfo = isFailedProfile ? task.failed_profiles[profileString] : null;
              
              // Check if this profile is completed
              const isCompletedProfile = task.outputs && task.outputs[profileString];
              
              return (
                <div key={index} style={{
                  background: isFailedProfile ? '#fef5e7' : 'white',
                  border: `1px solid ${isFailedProfile ? '#f6ad55' : '#e2e8f0'}`,
                  borderRadius: '8px',
                  padding: '16px',
                  transition: 'all 0.3s ease',
                  borderLeft: `4px solid ${isFailedProfile ? '#f56565' : profileInfo.color}`,
                  cursor: 'pointer',
                  minWidth: 0, // Allow flex items to shrink
                  overflow: 'hidden', // Prevent content overflow
                  boxShadow: isFailedProfile ? '0 2px 8px rgba(245, 101, 101, 0.1)' : '0 1px 3px rgba(0,0,0,0.1)'
                }} onClick={() => toggleProfileExpanded(profileString)}>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '10px',
                    marginBottom: '8px'
                  }}>
                    <span style={{ fontSize: '1.2rem' }}>
                      {isFailedProfile ? '❌' : isCompletedProfile ? '✅' : profileInfo.icon}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ 
                        fontWeight: '600', 
                        fontSize: '1rem',
                        color: isFailedProfile ? '#c53030' : '#2d3748'
                      }}>
                        {profileString}
                        {isFailedProfile && <span style={{ fontSize: '0.8rem', marginLeft: '8px' }}>FAILED</span>}
                        {isCompletedProfile && <span style={{ fontSize: '0.8rem', marginLeft: '8px', color: '#38a169' }}>COMPLETED</span>}
                      </div>
                      <div style={{
                        fontSize: '0.8rem',
                        color: isFailedProfile ? '#c53030' : profileInfo.color,
                        fontWeight: '500'
                      }}>
                        {profileInfo.type}
                      </div>
                      {profile.config_summary && (
                        <div style={{
                          fontSize: '0.75rem',
                          color: '#666',
                          marginTop: '4px'
                        }}>
                          {profile.config_summary}
                        </div>
                      )}
                      
                      {/* Show error message directly if failed */}
                      {isFailedProfile && failedInfo && (
                        <div style={{
                          marginTop: '8px',
                          padding: '8px',
                          background: 'rgba(254, 215, 215, 0.3)',
                          borderRadius: '4px',
                          border: '1px solid rgba(245, 101, 101, 0.2)'
                        }}>
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            marginBottom: '4px'
                          }}>
                            <span style={{ 
                              fontSize: '0.7rem', 
                              fontWeight: '600',
                              color: '#c53030'
                            }}>
                              ⚠️ Error Preview
                            </span>
                            <button
                              id={`copy-btn-profile-${profileString}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                copyToClipboard(failedInfo.error_message || '', `profile-${profileString}`);
                              }}
                              style={{
                                background: 'transparent',
                                border: '1px solid rgba(245, 101, 101, 0.3)',
                                borderRadius: '3px',
                                padding: '2px 6px',
                                fontSize: '0.6rem',
                                color: '#c53030',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease'
                              }}
                              onMouseEnter={(e) => {
                                e.target.style.background = 'rgba(245, 101, 101, 0.1)';
                              }}
                              onMouseLeave={(e) => {
                                e.target.style.background = 'transparent';
                              }}
                            >
                              📋
                            </button>
                          </div>
                          <div style={{
                            fontSize: '0.75rem',
                            color: '#c53030',
                            lineHeight: '1.3',
                            wordBreak: 'break-word',
                            overflow: 'hidden',
                            maxHeight: '3.6em',
                            fontFamily: 'ui-monospace, SFMono-Regular, Monaco, Consolas, monospace'
                          }}>
                            <div style={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              lineHeight: '1.3em'
                            }}>
                              {truncateError(failedInfo.error_message, 2)}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                    <div style={{ 
                      fontSize: '1rem', 
                      color: '#666',
                      transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                      transition: 'transform 0.3s ease'
                    }}>
                      ▶
                    </div>
                  </div>
                  
                  {isExpanded && renderProfileConfigDetails(profile)}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Output Files */}
      {task.outputs && Object.keys(task.outputs).length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h2 style={{ 
            fontSize: '1.2rem', 
            marginBottom: '16px', 
            color: '#2d3748',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            ✅ Output Files
            <span style={{
              background: '#e6fffa',
              color: '#2d7a6a',
              padding: '2px 10px',
              borderRadius: '12px',
              fontSize: '0.8rem',
              fontWeight: '600'
            }}>
              {filteredOutputs ? Object.values(filteredOutputs).flat().length : Object.values(task.outputs).flat().length} files
              {filteredOutputs && Object.keys(filteredOutputs).length !== Object.keys(task.outputs).length && (
                <span style={{ color: '#c53030', marginLeft: '4px' }}>
                  (filtered from {Object.values(task.outputs).flat().length})
                </span>
              )}
            </span>
          </h2>
          
          {/* Media Filter Component */}
          <MediaFilter 
            outputs={task.outputs}
            onFilterChange={setFilteredOutputs}
          />
          
          {filteredOutputs && Object.keys(filteredOutputs).length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '40px',
              background: '#f8f9fa',
              borderRadius: '8px',
              border: '2px dashed #dee2e6',
              color: '#6c757d'
            }}>
              <div style={{ fontSize: '3rem', marginBottom: '16px' }}>🔍</div>
              <h3 style={{ color: '#495057', marginBottom: '8px' }}>No files match your filter</h3>
              <p style={{ marginBottom: '16px' }}>Try adjusting your filter criteria or clear all filters to see all files.</p>
              <button
                onClick={() => setFilteredOutputs(null)}
                style={{
                  background: '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  cursor: 'pointer'
                }}
              >
                🗑️ Clear Filters
              </button>
            </div>
          ) : (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
              gap: '12px'
            }}>
              {Object.entries(filteredOutputs || task.outputs).map(([profile, urlItems]) => {
              const urlList = Array.isArray(urlItems) ? urlItems : [urlItems];
              return urlList.map((urlItem, index) => {
                // Handle both object format {url, size} and string format
                const url = typeof urlItem === 'object' ? urlItem.url : urlItem;
                const filename = getFileName(url);
                const fileType = getFileType(url);
                const fileKey = `${profile}-${index}`;
                const metadata = fileMetadata[fileKey] || {};
                
                return (
                  <div key={`${profile}-${index}`} style={{
                    background: 'white',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    padding: '12px',
                    transition: 'all 0.3s ease'
                  }}>
                    {/* Media Preview */}
                    <div style={{ 
                      width: '100%', 
                      aspectRatio: '3/4',
                      background: 'linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)',
                      borderRadius: '6px',
                      overflow: 'hidden',
                      position: 'relative',
                      marginBottom: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      {fileType === 'video' ? (
                        <video 
                          src={url} 
                          controls
                          muted
                          preload="metadata"
                          style={{ 
                            width: '100%', 
                            height: '100%', 
                            objectFit: 'cover',
                            borderRadius: '6px'
                          }}
                        />
                      ) : fileType === 'image' ? (
                        <img 
                          src={url} 
                          alt={filename}
                          loading="lazy"
                          style={{ 
                            width: '100%', 
                            height: '100%', 
                            objectFit: 'cover',
                            borderRadius: '6px'
                          }}
                        />
                      ) : (
                        <div style={{
                          color: '#a0aec0',
                          textAlign: 'center',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                          height: '100%'
                        }}>
                          <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📄</div>
                          <div style={{ fontSize: '0.8rem' }}>{fileType.toUpperCase()}</div>
                        </div>
                      )}
                      
                      {/* File type badge */}
                      <div style={{
                        position: 'absolute',
                        top: '8px',
                        left: '8px',
                        background: fileType === 'video' ? '#4299e1' : fileType === 'image' ? '#48bb78' : '#ed8936',
                        color: 'white',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        fontWeight: '600',
                        textTransform: 'uppercase'
                      }}>
                        {fileType}
                      </div>
                      
                      {/* Profile badge */}
                      <div style={{
                        position: 'absolute',
                        bottom: '8px',
                        right: '8px',
                        background: 'rgba(0,0,0,0.8)',
                        color: 'white',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        fontWeight: '600'
                      }}>
                        {profile}
                      </div>
                    </div>

                    {/* File info */}
                    <div style={{ marginBottom: '12px' }}>
                      <div style={{ 
                        fontWeight: '600', 
                        fontSize: '0.9rem', 
                        marginBottom: '4px',
                        color: '#2d3748',
                        lineHeight: '1.2'
                      }}>
                        {profile}
                      </div>
                      <div style={{ 
                        fontSize: '0.8rem', 
                        color: '#718096',
                        wordBreak: 'break-word',
                        lineHeight: '1.2',
                        marginBottom: '8px'
                      }}>
                        {filename}
                      </div>
                      
                      {/* File metadata - simplified */}
                      <div style={{
                        fontSize: '0.65rem',
                        color: '#4a5568',
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '6px',
                        marginTop: '4px'
                      }}>
                        {/* File Size */}
                        {metadata.size && (
                          <span style={{ 
                            background: '#e6fffa', 
                            color: '#2d7a6a', 
                            padding: '2px 6px', 
                            borderRadius: '10px',
                            fontWeight: '500'
                          }}>
                            💾 {formatFileSize(metadata.size)}
                          </span>
                        )}

                        {/* Dimensions */}
                        {metadata.dimensions && (
                          <span style={{ 
                            background: '#e6f3ff', 
                            color: '#2b77e6', 
                            padding: '2px 6px', 
                            borderRadius: '10px',
                            fontWeight: '500'
                          }}>
                            📐 {metadata.dimensions}
                          </span>
                        )}

                        {/* Duration - only for video */}
                        {metadata.duration && (
                          <span style={{ 
                            background: '#fff5e6', 
                            color: '#e67e22', 
                            padding: '2px 6px', 
                            borderRadius: '10px',
                            fontWeight: '500'
                          }}>
                            ⏱️ {formatDuration(metadata.duration)}
                          </span>
                        )}

                        {/* FPS - only for video */}
                        {metadata.fps && (
                          <span style={{ 
                            background: '#f3e6ff', 
                            color: '#8e44ad', 
                            padding: '2px 6px', 
                            borderRadius: '10px',
                            fontWeight: '500'
                          }}>
                            🎬 {formatFPS(metadata.fps)}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div style={{
                      display: 'flex',
                      gap: '6px',
                      justifyContent: 'space-between'
                    }}>
                      {/* Copy URL button */}
                      <button
                        onClick={async (event) => {
                          try {
                            await navigator.clipboard.writeText(url);
                            // Show temporary feedback
                            const btn = event.target;
                            const originalText = btn.textContent;
                            btn.textContent = '✓';
                            btn.style.background = '#48bb78';
                            setTimeout(() => {
                              btn.textContent = originalText;
                              btn.style.background = '#4299e1';
                            }, 1500);
                          } catch (err) {
                            // Fallback method
                            const textArea = document.createElement('textarea');
                            textArea.value = url;
                            document.body.appendChild(textArea);
                            textArea.select();
                            document.execCommand('copy');
                            document.body.removeChild(textArea);
                            
                            const btn = event.target;
                            const originalText = btn.textContent;
                            btn.textContent = '✓';
                            btn.style.background = '#48bb78';
                            setTimeout(() => {
                              btn.textContent = originalText;
                              btn.style.background = '#4299e1';
                            }, 1500);
                          }
                        }}
                        style={{
                          flex: 1,
                          background: '#4299e1',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '6px 8px',
                          fontSize: '0.75rem',
                          fontWeight: '500',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '4px'
                        }}
                        onMouseEnter={(e) => {
                          e.target.style.background = '#3182ce';
                          e.target.style.transform = 'translateY(-1px)';
                        }}
                        onMouseLeave={(e) => {
                          if (e.target.textContent !== '✓') {
                            e.target.style.background = '#4299e1';
                          }
                          e.target.style.transform = 'translateY(0)';
                        }}
                      >
                        📋 Copy URL
                      </button>

                      {/* Download button */}
                      <button
                        onClick={() => {
                          const link = document.createElement('a');
                          link.href = url;
                          link.download = filename;
                          link.target = '_blank';
                          document.body.appendChild(link);
                          link.click();
                          document.body.removeChild(link);
                        }}
                        style={{
                          flex: 1,
                          background: '#48bb78',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '6px 8px',
                          fontSize: '0.75rem',
                          fontWeight: '500',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '4px'
                        }}
                        onMouseEnter={(e) => {
                          e.target.style.background = '#38a169';
                          e.target.style.transform = 'translateY(-1px)';
                        }}
                        onMouseLeave={(e) => {
                          e.target.style.background = '#48bb78';
                          e.target.style.transform = 'translateY(0)';
                        }}
                      >
                        ⬇️ Download
                      </button>
                    </div>
                  </div>
                );
              });
            })}
            </div>
          )}
        </div>
      )}

      {/* Failed Profiles */}
      {task.failed_profiles && Object.keys(task.failed_profiles).length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h2 style={{ 
            fontSize: '1.2rem', 
            marginBottom: '16px', 
            color: '#f56565',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            ❌ Failed Profiles
            <span style={{
              background: '#fed7d7',
              color: '#c53030',
              padding: '2px 10px',
              borderRadius: '12px',
              fontSize: '0.8rem',
              fontWeight: '600'
            }}>
              {Object.keys(task.failed_profiles).length} failed
            </span>
          </h2>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '16px' 
          }}>
            {Object.entries(task.failed_profiles).map(([profile, info]) => {
              
              return (
                <div key={profile} style={{
                  background: '#fff5f5',
                  border: '1px solid #fed7d7',
                  borderLeft: '4px solid #f56565',
                  borderRadius: '8px',
                  padding: '16px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ 
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '12px',
                    marginBottom: '12px'
                  }}>
                    <div style={{
                      minWidth: '24px',
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      background: '#f56565',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.8rem'
                    }}>
                      ❌
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ 
                        fontWeight: '600', 
                        fontSize: '1rem',
                        color: '#2d3748',
                        marginBottom: '4px',
                        wordBreak: 'break-word'
                      }}>
                        {profile}
                      </div>
                      <div style={{
                        fontSize: '0.8rem',
                        color: '#718096',
                        marginBottom: '8px'
                      }}>
                        {info?.failed_at ? formatDate(info.failed_at) : 'Unknown time'}
                      </div>
                    </div>
                  </div>
                  
                  <div style={{
                    background: '#fff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    padding: '12px'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '8px'
                    }}>
                      <div style={{
                        fontSize: '0.8rem',
                        fontWeight: '600',
                        color: '#e53e3e',
                        textTransform: 'uppercase',
                        letterSpacing: '0.025em'
                      }}>
                        Error Details
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          id={`copy-btn-${profile}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            copyToClipboard(info?.error_message || '', profile);
                          }}
                          style={{
                            background: 'transparent',
                            border: '1px solid #e2e8f0',
                            borderRadius: '4px',
                            padding: '4px 8px',
                            fontSize: '0.7rem',
                            color: '#4a5568',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            transition: 'all 0.2s ease'
                          }}
                          onMouseEnter={(e) => {
                            e.target.style.background = '#f7fafc';
                            e.target.style.borderColor = '#cbd5e0';
                          }}
                          onMouseLeave={(e) => {
                            e.target.style.background = 'transparent';
                            e.target.style.borderColor = '#e2e8f0';
                          }}
                        >
                          📋 Copy
                        </button>
                        {info?.error_message && info.error_message.split('\n').length > 3 && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleErrorExpanded(profile);
                            }}
                            style={{
                              background: 'transparent',
                              border: '1px solid #e2e8f0',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              fontSize: '0.7rem',
                              color: '#4a5568',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              transition: 'all 0.2s ease'
                            }}
                            onMouseEnter={(e) => {
                              e.target.style.background = '#f7fafc';
                              e.target.style.borderColor = '#cbd5e0';
                            }}
                            onMouseLeave={(e) => {
                              e.target.style.background = 'transparent';
                              e.target.style.borderColor = '#e2e8f0';
                            }}
                          >
                            {expandedErrors[profile] ? '📄 Collapse' : '📖 Expand'}
                          </button>
                        )}
                      </div>
                    </div>
                    <div style={{
                      fontSize: '0.8rem',
                      lineHeight: '1.4',
                      color: '#4a5568',
                      wordBreak: 'break-word',
                      fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                      background: '#f8f9fa',
                      padding: '10px',
                      borderRadius: '4px',
                      border: '1px solid #e9ecef',
                      whiteSpace: 'pre-wrap',
                      overflow: 'auto',
                      maxHeight: expandedErrors[profile] ? 'none' : '120px'
                    }}>
                      {expandedErrors[profile] 
                        ? (info?.error_message || 'No error message available')
                        : truncateError(info?.error_message, 3)
                      }
                      {!expandedErrors[profile] && info?.error_message && info.error_message.split('\n').length > 3 && (
                        <div style={{
                          marginTop: '8px',
                          fontSize: '0.75rem',
                          color: '#718096',
                          fontStyle: 'italic'
                        }}>
                          ... (click Expand to see full error)
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Debug info - only in development */}
                  {process.env.NODE_ENV === 'development' && (
                    <details style={{ marginTop: '12px' }}>
                      <summary style={{ 
                        fontSize: '0.75rem',
                        color: '#718096',
                        cursor: 'pointer',
                        padding: '4px 0'
                      }}>
                        Debug Info
                      </summary>
                      <pre style={{ 
                        fontSize: '0.7rem', 
                        marginTop: '8px',
                        padding: '8px',
                        background: '#f7fafc',
                        border: '1px solid #e2e8f0',
                        borderRadius: '4px',
                        overflow: 'auto',
                        maxHeight: '150px'
                      }}>
                        {JSON.stringify(info, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* General Error */}
      {task.error_message && (
        <div style={{
          background: 'linear-gradient(135deg, #fed7d7 0%, #feb2b2 100%)',
          border: '1px solid #fc8181',
          borderRadius: '8px',
          padding: '16px',
          color: '#742a2a',
          marginBottom: '24px'
        }}>
          <div style={{ 
            fontWeight: '600', 
            fontSize: '1rem', 
            marginBottom: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            ❌ General Error
          </div>
          <div style={{ fontSize: '0.9rem', lineHeight: '1.4' }}>
            {task.error_message}
          </div>
        </div>
      )}

      {/* Retry Confirmation Modal */}
      <ConfirmModal
        isOpen={showRetryModal}
        onClose={() => {
          setShowRetryModal(false);
          setRetryDeleteFiles(false);
        }}
        onConfirm={async (deleteFiles) => {
          setShowRetryModal(false);
          try {
            const response = await apiService.retryTask(taskId, deleteFiles);
            let message = `Task retry initiated: ${response.published_profiles}/${response.total_profiles} profiles queued`;
            if (response.face_detection_retried) {
              message += '\nFace detection task also requeued.';
            }
            if (deleteFiles && response.deleted_outputs?.length > 0) {
              message += `\n${response.deleted_outputs.length} output files deleted.`;
            }
            if (response.failed_deletions?.length > 0) {
              message += `\n${response.failed_deletions.length} files failed to delete.`;
            }
            alert(message);
            window.location.reload();
          } catch (error) {
            alert(`Retry failed: ${error.response?.data?.detail || error.message}`);
          }
          setRetryDeleteFiles(false);
        }}
        title="Retry Task"
        message="Are you sure you want to retry this task? This will clear all existing results and restart processing."
        confirmText="🔄 Retry Task"
        cancelText="Cancel"
        type="warning"
        showDeleteFilesOption={true}
        deleteFiles={retryDeleteFiles}
        onDeleteFilesChange={setRetryDeleteFiles}
      />

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setDeleteTaskFiles(false);
        }}
        onConfirm={async (deleteFiles) => {
          setShowDeleteModal(false);
          try {
            const response = await apiService.deleteTask(taskId, deleteFiles);
            let message = 'Task deleted successfully from database.';
            if (deleteFiles) {
              if (response.deleted_files?.length > 0) {
                message = `Task deleted: ${response.deleted_files.length} files removed from S3.`;
              }
              if (response.failed_deletions?.length > 0) {
                message += `\n${response.failed_deletions.length} files failed to delete.`;
              }
            } else {
              message += ' S3 files were preserved.';
            }
            alert(message);
            navigate('/results');
          } catch (error) {
            alert(`Delete failed: ${error.response?.data?.detail || error.message}`);
          }
          setDeleteTaskFiles(false);
        }}
        title="Delete Task"
        message="Are you sure you want to delete this task? This action cannot be undone."
        confirmText="🗑️ Delete Task"
        cancelText="Cancel"
        type="danger"
        showDeleteFilesOption={true}
        deleteFiles={deleteTaskFiles}
        onDeleteFilesChange={setDeleteTaskFiles}
      />
    </div>
  );
};

export default TaskDetails;