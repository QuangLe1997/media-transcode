import React, {useEffect, useState} from 'react';
import {useNavigate} from 'react-router-dom';
import axios from 'axios';
import api from '../api';
import Editor from '@monaco-editor/react';
import ProfileTemplateManager from './ProfileTemplateManager';

const Upload = () => {
  const navigate = useNavigate();
  const [uploadType, setUploadType] = useState('file'); // 'file' or 'url'
  const [files, setFiles] = useState([]);
  const [mediaUrls, setMediaUrls] = useState(['']);
  const [profilesJson, setProfilesJson] = useState(JSON.stringify([
    {
      "id_profile": "720p_h264",
      "output_type": "video",
      "video_config": {
        "codec": "libx264",
        "max_width": 1280,
        "max_height": 720,
        "bitrate": "2M"
      }
    },
    {
      "id_profile": "thumbnail",
      "output_type": "image", 
      "image_config": {
        "max_width": 400,
        "max_height": 300,
        "quality": 80,
        "format": "jpeg"
      }
    }
  ], null, 2));
  const [s3ConfigJson, setS3ConfigJson] = useState(JSON.stringify({
    "base_path": "transcode-outputs",
    "folder_structure": "{task_id}/{profile_id}"
  }, null, 2));
  const [configFile, setConfigFile] = useState(null);
  const [callbackUrl, setCallbackUrl] = useState('');
  const [callbackType, setCallbackType] = useState('webhook'); // 'webhook' or 'pubsub'
  const [pubsubTopic, setPubsubTopic] = useState('');
  const [callbackAuth, setCallbackAuth] = useState({
    type: 'none',
    token: '',
    username: '',
    password: '',
    headers: {}
  });
  const [activeTab, setActiveTab] = useState('profiles');
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [message, setMessage] = useState(null);
  
  // Face detection state
  const [faceDetectionEnabled, setFaceDetectionEnabled] = useState(false);
  const [faceDetectionConfig, setFaceDetectionConfig] = useState(JSON.stringify({
    "enabled": true,
    "similarity_threshold": 0.6,
    "min_faces_in_group": 1,
    "sample_interval": 5,
    "face_detector_size": "640x640",
    "face_detector_score_threshold": 0.5,
    "save_faces": true,
    "avatar_size": 112,
    "avatar_quality": 85
  }, null, 2));
  
  // Config template management
  const [configTemplates, setConfigTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [templateName, setTemplateName] = useState('');

    // Profile template management
    const [showProfileManager, setShowProfileManager] = useState(false);

  // Quick templates for profiles (v1 format - API compatible)
  const profileTemplates = {
    quick_web_video: {
      "id_profile": "quick_web_video",
      "output_type": "video",
      "input_type": "video",
      "video_config": {
        "codec": "libx264",
        "max_width": 1280,
        "max_height": 720,
        "crf": 23,
        "preset": "fast",
        "profile": "main",
        "level": "4.0",
        "pixel_format": "yuv420p",
        "audio_codec": "aac",
        "audio_bitrate": "128k"
      }
    },
    quick_mobile_preview: {
      "id_profile": "quick_mobile_preview",
      "output_type": "webp",
      "input_type": "video",
      "webp_config": {
        "width": 640,
        "height": 360,
        "quality": 80,
        "fps": 15,
        "duration": 5.0,
        "start_time": 1.0,
        "animated": true,
        "lossless": false,
        "method": 2,
        "preset": "default",
        "loop": 0
      }
    },
    quick_thumbnail: {
      "id_profile": "quick_thumbnail",
      "output_type": "image",
      "input_type": "video",
      "image_config": {
        "max_width": 400,
        "max_height": 300,
        "quality": 85,
        "format": "jpeg",
        "start_time": 3.0
      }
    },
    quick_gif_preview: {
      "id_profile": "quick_gif_preview",
      "output_type": "gif",
      "input_type": "video",
      "gif_config": {
        "width": 480,
        "height": 270,
        "fps": 12,
        "duration": 3.0,
        "start_time": 2.0,
        "quality": 75,
        "loop": 0
      }
    },
    social_square_video: {
      "id_profile": "social_square_video",
      "output_type": "video",
      "input_type": "video",
      "video_config": {
        "codec": "libx264",
        "max_width": 1080,
        "max_height": 1080,
        "crf": 25,
        "preset": "fast",
        "profile": "main",
        "pixel_format": "yuv420p",
        "audio_codec": "aac",
        "audio_bitrate": "128k"
      }
    },
    image_optimize: {
      "id_profile": "image_optimize_jpeg",
      "output_type": "image",
      "input_type": "image",
      "image_config": {
        "max_width": 1200,
        "max_height": 800,
        "quality": 85,
        "format": "jpeg",
        "progressive": true
      }
    }
  };

    // Handle profiles loaded from ProfileManager
    const handleProfilesLoad = (profilesJson) => {
        setProfilesJson(profilesJson);
        setMessage({type: 'success', text: 'Profiles loaded from template manager!'});
    };

  const formatJson = (jsonString) => {
    try {
      const parsed = JSON.parse(jsonString);
      return JSON.stringify(parsed, null, 2);
    } catch (error) {
      return jsonString;
    }
  };

  const addProfileTemplate = (templateKey) => {
    try {
      const currentProfiles = JSON.parse(profilesJson);
      const newProfile = { ...profileTemplates[templateKey] };
      // Add timestamp to make ID unique
      newProfile.id_profile = `${newProfile.id_profile}_${Date.now()}`;
      currentProfiles.push(newProfile);
      setProfilesJson(JSON.stringify(currentProfiles, null, 2));
      setMessage({ type: 'success', text: 'Template added to profiles' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Invalid JSON format. Cannot add template.' });
    }
  };

  // Load config templates on component mount
  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const response = await api.get('/config-templates');
        setConfigTemplates(response.data.templates || []);
      } catch (error) {
        console.error('Error loading config templates:', error);
      }
    };
    loadTemplates();
  }, []);

  // Load selected template
  const cleanProfilesForFormat = (profiles) => {
    // Clean up profile data based on output format
    return profiles.map(profile => {
      if (profile.config && profile.config.output_format === 'gif') {
        // Remove unnecessary fields for GIF
        const cleanConfig = {...profile.config};
        delete cleanConfig.quality; // GIF doesn't use quality parameter
        delete cleanConfig.height; // Let GIF maintain aspect ratio  
        delete cleanConfig.jpeg_quality;
        delete cleanConfig.lossless;
        delete cleanConfig.method;
        delete cleanConfig.preset;
        delete cleanConfig.alpha_quality;
        delete cleanConfig.animated;
        delete cleanConfig.pass_count;
        delete cleanConfig.save_frames;
        delete cleanConfig.auto_filter;
        delete cleanConfig.verbose;
        delete cleanConfig.gamma;
        delete cleanConfig.near_lossless;
        delete cleanConfig.target_size;
        delete cleanConfig.optimize;
        delete cleanConfig.progressive;
        delete cleanConfig.two_pass;
        delete cleanConfig.hardware_accel;
        return {...profile, config: cleanConfig};
      }
      return profile;
    });
  };

  const loadTemplate = async (templateId) => {
    if (!templateId) return;
    
    try {
      const response = await api.get(`/config-templates/${templateId}`);
      const template = response.data;
      // Clean profiles based on output format
      const cleanedProfiles = cleanProfilesForFormat(template.config || template.profiles || []);
      setProfilesJson(JSON.stringify(cleanedProfiles, null, 2));
      setMessage({ type: 'success', text: `Loaded template: ${template.name}` });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to load template' });
    }
  };

  // Save current config as template
  const saveAsTemplate = async () => {
    if (!templateName.trim()) {
      setMessage({ type: 'error', text: 'Please enter a template name' });
      return;
    }

    try {
      const profiles = JSON.parse(profilesJson);
      const response = await api.post('/config-templates', {
        name: templateName,
        description: null,
        profiles: profiles,
        s3_output_config: null,
        face_detection_config: null
      });
      
      setConfigTemplates([...configTemplates, response.data]);
      setTemplateName('');
      setShowSaveDialog(false);
      setMessage({ type: 'success', text: 'Template saved successfully' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save template' });
    }
  };

  // Delete template
  const deleteTemplate = async (templateId) => {
    if (!window.confirm('Are you sure you want to delete this template?')) return;
    
    try {
      await api.delete(`/config-templates/${templateId}`);
      setConfigTemplates(configTemplates.filter(t => t.template_id !== templateId));
      if (selectedTemplate === templateId) {
        setSelectedTemplate('');
      }
      setMessage({ type: 'success', text: 'Template deleted successfully' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to delete template' });
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    const mediaFiles = droppedFiles.filter(file => 
      file.type.startsWith('video/') || 
      file.type.startsWith('image/')
    );
    const configFiles = droppedFiles.filter(file => file.name.endsWith('.json'));
    
    if (configFiles.length > 0) {
      handleConfigFileSelect(configFiles[0]);
    }
    
    if (mediaFiles.length > 0) {
      setFiles(prevFiles => [...prevFiles, ...mediaFiles]);
      setMessage({ 
        type: 'success', 
        text: `Added ${mediaFiles.length} file${mediaFiles.length > 1 ? 's' : ''}: ${mediaFiles.map(f => f.name).join(', ')}` 
      });
    } else if (configFiles.length === 0) {
      setMessage({ type: 'error', text: 'Please select media files or JSON config file' });
    }
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (selectedFiles.length > 0) {
      setFiles(prevFiles => [...prevFiles, ...selectedFiles]);
      setMessage({ 
        type: 'success', 
        text: `Added ${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''}: ${selectedFiles.map(f => f.name).join(', ')}` 
      });
    }
  };

  const removeFile = (index) => {
    setFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
  };

  const addUrlInput = () => {
    setMediaUrls(prev => [...prev, '']);
  };

  const removeUrlInput = (index) => {
    setMediaUrls(prev => prev.filter((_, i) => i !== index));
  };

  const updateUrl = (index, value) => {
    setMediaUrls(prev => prev.map((url, i) => i === index ? value : url));
  };

  const handleConfigFileSelect = async (configFile) => {
    try {
      const text = await configFile.text();
      const config = JSON.parse(text);
      
      if (config.profiles) {
        setProfilesJson(JSON.stringify(config.profiles, null, 2));
      }
      if (config.s3_output_config) {
        setS3ConfigJson(JSON.stringify(config.s3_output_config, null, 2));
      }
      
      setMessage({ type: 'success', text: 'Config loaded from file' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Invalid JSON config file' });
    }
  };

  const handleUpload = async () => {
    // Check if we have any media to upload
    const hasFiles = files.length > 0;
    const hasUrls = mediaUrls.some(url => url.trim() !== '');
    
    if (!hasFiles && !hasUrls) {
      setMessage({ type: 'error', text: 'Please select files or enter URLs' });
      return;
    }

    // Validate JSON configs
    try {
      JSON.parse(profilesJson);
      JSON.parse(s3ConfigJson);
      
      // Validate face detection config if enabled
      if (faceDetectionEnabled) {
        const faceConfig = JSON.parse(faceDetectionConfig);
        
        // Basic validation
        if (typeof faceConfig.enabled !== 'boolean') {
          throw new Error('Face detection "enabled" must be a boolean');
        }
        if (faceConfig.enabled && faceConfig.similarity_threshold < 0 || faceConfig.similarity_threshold > 1) {
          throw new Error('Face detection "similarity_threshold" must be between 0 and 1');
        }
        if (faceConfig.enabled && faceConfig.min_faces_in_group < 1) {
          throw new Error('Face detection "min_faces_in_group" must be at least 1');
        }
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Invalid JSON format: ${error.message}` });
      return;
    }

    setUploading(true);
    setMessage(null);

    try {
      // Collect all media to upload
      const mediaToUpload = [];
      
      // Add files
      if (uploadType === 'file' && files.length > 0) {
        files.forEach(file => {
          mediaToUpload.push({ type: 'file', data: file, name: file.name });
        });
      }
      
      // Add URLs
      if (uploadType === 'url') {
        mediaUrls.forEach(url => {
          if (url.trim()) {
            mediaToUpload.push({ type: 'url', data: url.trim(), name: url.trim() });
          }
        });
      }
      
      if (mediaToUpload.length === 0) {
        setMessage({ type: 'error', text: 'No valid media to upload' });
        setUploading(false);
        return;
      }
      
      // Create tasks for each media
      const results = [];
      // Use nginx proxy instead of direct API call
      const apiUrl = '/api';
      
      for (let i = 0; i < mediaToUpload.length; i++) {
        const media = mediaToUpload[i];
        const formData = new FormData();
        
        // Add media source
        if (media.type === 'file') {
          formData.append('video', media.data);
        } else if (media.type === 'url') {
          formData.append('media_url', media.data);
        }
        
        // Add config data
        formData.append('profiles', profilesJson);
        formData.append('s3_output_config', s3ConfigJson);
        
        // Add face detection config if enabled
        if (faceDetectionEnabled) {
          formData.append('face_detection_config', faceDetectionConfig);
        }
        
        // Add optional callback/notification settings
        if (callbackType === 'webhook' && callbackUrl.trim()) {
          formData.append('callback_url', callbackUrl.trim());
          
          // Add callback authentication if configured
          if (callbackAuth.type !== 'none') {
            const authData = {
              type: callbackAuth.type
            };
            
            if (callbackAuth.type === 'bearer' && callbackAuth.token) {
              authData.token = callbackAuth.token;
            } else if (callbackAuth.type === 'basic' && callbackAuth.username && callbackAuth.password) {
              authData.username = callbackAuth.username;
              authData.password = callbackAuth.password;
            } else if (callbackAuth.type === 'header' && Object.keys(callbackAuth.headers).length > 0) {
              authData.headers = callbackAuth.headers;
            }
            
            formData.append('callback_auth', JSON.stringify(authData));
          }
        } else if (callbackType === 'pubsub' && pubsubTopic.trim()) {
          formData.append('pubsub_topic', pubsubTopic.trim());
        }

          try {
            const response = await axios.post(`${apiUrl}/transcode`, formData, {
              headers: {
                'Content-Type': 'multipart/form-data',
              },
            });
            
            results.push({
              success: true,
              taskId: response.data.task_id,
              media: media.name
            });
            
            setMessage({ 
              type: 'success', 
              text: `Progress: ${i + 1}/${mediaToUpload.length} tasks created...` 
            });
            
          } catch (error) {
            console.error('Upload error for', media.name, ':', error);
            let errorMessage = 'Upload failed';
            
            if (error.response) {
              const status = error.response.status;
              const detail = error.response?.data?.detail || error.response?.data?.message;
              
              if (status === 413) {
                errorMessage = 'File too large. Maximum upload size is 1GB.';
              } else if (status === 400) {
                errorMessage = detail || 'Invalid request. Check your inputs.';
              } else if (status === 500) {
                errorMessage = 'Server error. Please try again later.';
              } else {
                errorMessage = detail || `Server error (${status})`;
              }
            } else if (error.request) {
              errorMessage = 'Network error. Check your connection.';
            } else {
              errorMessage = error.message || 'Unexpected error';
            }
            
            results.push({
              success: false,
              error: errorMessage,
              media: media.name
            });
          }
        }
        
        // Show final results
        const successCount = results.filter(r => r.success).length;
        const failedCount = results.filter(r => !r.success).length;
        
        if (successCount > 0) {
          const successTasks = results.filter(r => r.success).map(r => r.taskId);
          const message = `✅ Successfully created ${successCount} task${successCount > 1 ? 's' : ''}!` +
                         (failedCount > 0 ? ` (${failedCount} failed)` : '') +
                         `\nTask IDs: ${successTasks.join(', ')}`;
          
          setMessage({ type: 'success', text: message });
          
          // Reset form
          setFiles([]);
          setMediaUrls(['']);
          setCallbackUrl('');
          setPubsubTopic('');
          
          // Navigate to results page after 3 seconds
          setTimeout(() => {
            navigate('/results');
          }, 3000);
        } else {
          const errorMessages = results.map(r => `${r.media}: ${r.error}`).join('\n');
          setMessage({ 
            type: 'error', 
            text: `❌ All uploads failed:\n${errorMessages}` 
          });
        }

    } catch (error) {
      console.error('Upload error:', error);
      setMessage({ type: 'error', text: `❌ ${error.message || 'Unexpected error'}` });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ 
      maxWidth: '1400px', 
      margin: '0 auto', 
      padding: '20px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    }}>
      {/* Main Content Grid */}
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <div className="upload-grid">
        
        {/* Left Column - Media Input */}
        <div className="upload-card">
          <h3 style={{ 
            margin: '0 0 16px 0', 
            fontSize: '1.1rem', 
            fontWeight: '600',
            color: '#374151',
            borderBottom: '2px solid #f3f4f6',
            paddingBottom: '8px'
          }}>
            📁 Media Input
          </h3>

          {message && (
            <div className={`${message.type === 'error' ? 'error-message' : 'success-message'}`} style={{ marginBottom: '16px' }}>
              {message.text}
            </div>
          )}

          {/* Upload Type Selection */}
      <div className="form-group" style={{ marginBottom: '12px' }}>
        <label style={{ fontSize: '0.85rem', fontWeight: '600', marginBottom: '6px', display: 'block' }}>Upload Method:</label>
        <div style={{ display: 'flex', gap: '12px', marginTop: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
          <label style={{ 
            display: 'flex', 
            alignItems: 'center', 
            cursor: 'pointer',
            padding: '10px 14px',
            background: uploadType === 'file' ? '#e6fffa' : '#f9fafb',
            borderRadius: '6px',
            border: uploadType === 'file' ? '2px solid #10b981' : '2px solid #e2e8f0',
            fontSize: '0.9rem'
          }}>
            <input
              type="radio"
              value="file"
              checked={uploadType === 'file'}
              onChange={(e) => setUploadType(e.target.value)}
              style={{ marginRight: '8px' }}
            />
            📁 Upload File
          </label>
          <label style={{ 
            display: 'flex', 
            alignItems: 'center', 
            cursor: 'pointer',
            padding: '10px 14px',
            background: uploadType === 'url' ? '#e6fffa' : '#f9fafb',
            borderRadius: '6px',
            border: uploadType === 'url' ? '2px solid #10b981' : '2px solid #e2e8f0',
            fontSize: '0.9rem'
          }}>
            <input
              type="radio"
              value="url"
              checked={uploadType === 'url'}
              onChange={(e) => setUploadType(e.target.value)}
              style={{ marginRight: '8px' }}
            />
            🔗 Media URL
          </label>
        </div>
      </div>

      {/* File Upload */}
      {uploadType === 'file' && (
        <div className="form-group">
          <div
            className={`upload-area ${dragOver ? 'dragover' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-input').click()}
            style={{ padding: '24px', textAlign: 'center', cursor: 'pointer' }}
          >
            <div className="upload-icon">📹</div>
            <h3>Drop media files here or click to select</h3>
            <p style={{ color: '#718096', marginTop: '8px' }}>
              {files.length > 0 ? `${files.length} file${files.length > 1 ? 's' : ''} selected` : 'Supports MP4, AVI, MOV, MKV, Images and more'}
            </p>
            <input
              id="file-input"
              type="file"
              accept="video/*,image/*"
              multiple
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
          </div>
          
          {/* Selected Files List */}
          {files.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <h4 style={{ fontSize: '0.9rem', marginBottom: '8px' }}>Selected Files:</h4>
              <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: '4px', padding: '8px' }}>
                {files.map((file, index) => (
                  <div key={index} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center', 
                    padding: '4px 8px',
                    backgroundColor: index % 2 === 0 ? '#f8f9fa' : 'white',
                    borderRadius: '4px',
                    marginBottom: '4px'
                  }}>
                    <span style={{ fontSize: '0.8rem', color: '#374151' }}>{file.name}</span>
                    <button
                      onClick={() => removeFile(index)}
                      style={{
                        background: '#ef4444',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '2px 8px',
                        fontSize: '0.7rem',
                        cursor: 'pointer'
                      }}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* URL Input */}
      {uploadType === 'url' && (
        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <label style={{ fontSize: '0.9rem', fontWeight: '600' }}>Media URLs:</label>
            <button
              onClick={addUrlInput}
              style={{
                background: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
            >
              + Add URL
            </button>
          </div>
          
          {mediaUrls.map((url, index) => (
            <div key={index} style={{ display: 'flex', marginBottom: '8px', gap: '8px' }}>
              <input
                type="url"
                className="form-control"
                placeholder="https://example.com/video.mp4"
                value={url}
                onChange={(e) => updateUrl(index, e.target.value)}
                style={{ flex: 1 }}
              />
              {mediaUrls.length > 1 && (
                <button
                  onClick={() => removeUrlInput(index)}
                  style={{
                    background: '#ef4444',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    fontSize: '0.8rem',
                    cursor: 'pointer'
                  }}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>
      )}

          {/* Start Transcoding Button */}
          <div style={{ textAlign: 'center', marginTop: '20px' }}>
            <button
              className="btn btn-success"
              onClick={handleUpload}
              disabled={uploading || (files.length === 0 && !mediaUrls.some(url => url.trim()))}
              style={{ 
                fontSize: '1rem', 
                padding: '14px 32px',
                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
              }}
            >
              {uploading ? (
                <>
                  <span className="loading-spinner" style={{ 
                    width: '16px', 
                    height: '16px', 
                    marginRight: '8px',
                    verticalAlign: 'middle'
                  }}></span>
                  Processing...
                </>
              ) : (
                '🚀 Start Transcoding'
              )}
            </button>
          </div>
        </div>

        {/* Right Column - Configuration */}
        <div className="upload-card">
          <h3 style={{ 
            margin: '0 0 20px 0', 
            fontSize: '1.1rem', 
            fontWeight: '600',
            color: '#374151',
            borderBottom: '2px solid #f3f4f6',
            paddingBottom: '8px'
          }}>
            ⚙️ Configuration
          </h3>

          {/* Configuration Tabs */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', borderBottom: '2px solid #f3f4f6', marginBottom: '16px' }}>
              {[
                { id: 'profiles', label: '📋 Profiles', icon: '📋' },
                { id: 's3', label: '☁️ S3 Config', icon: '☁️' },
                { id: 'face', label: '🤖 Face Detection', icon: '🤖' },
                { id: 'webhook', label: '🔔 Webhook', icon: '🔔' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    padding: '8px 16px',
                    fontSize: '0.85rem',
                    fontWeight: '600',
                    border: 'none',
                    borderBottom: activeTab === tab.id ? '2px solid #10b981' : '2px solid transparent',
                    background: activeTab === tab.id ? '#f0fdf4' : 'transparent',
                    color: activeTab === tab.id ? '#10b981' : '#6b7280',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    borderRadius: '6px 6px 0 0'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          <>
          {activeTab === 'profiles' && (
          <div>
          {/* Profiles Configuration */}
      <div className="form-group">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <label style={{ fontSize: '0.9rem', fontWeight: '600' }}>
            Profiles Configuration (JSON Array):
          </label>
          <div style={{ display: 'flex', gap: '8px' }}>
              <button
                  type="button"
                  onClick={() => setShowProfileManager(true)}
                  style={{
                      padding: '4px 12px',
                      fontSize: '0.8rem',
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: '600'
                  }}
              >
                  🔧 Profile Manager
              </button>
            <button
              type="button"
              onClick={() => setProfilesJson(formatJson(profilesJson))}
              style={{
                padding: '4px 8px',
                fontSize: '0.7rem',
                background: '#f8f9fa',
                border: '1px solid #e2e8f0',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              🎨 Format
            </button>
            <button
              type="button"
              onClick={() => setProfilesJson('[]')}
              style={{
                padding: '4px 8px',
                fontSize: '0.7rem',
                background: '#fff5f5',
                border: '1px solid #fed7d7',
                borderRadius: '4px',
                cursor: 'pointer',
                color: '#c53030'
              }}
            >
              🗑️ Clear
            </button>
          </div>
        </div>


        {/* Config Template Management */}
        <div style={{ marginBottom: '12px', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '12px', background: '#f9fafb' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: '600', marginBottom: '8px' }}>📋 Config Templates:</div>
          
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <select
              value={selectedTemplate}
              onChange={(e) => {
                setSelectedTemplate(e.target.value);
                loadTemplate(e.target.value);
              }}
              style={{
                padding: '4px 8px',
                fontSize: '0.8rem',
                border: '1px solid #e2e8f0',
                borderRadius: '4px',
                background: 'white',
                minWidth: '150px'
              }}
            >
              <option value="">Select a template...</option>
              {configTemplates.map(template => (
                <option key={template.template_id} value={template.template_id}>
                  {template.name}
                </option>
              ))}
            </select>
            
            <button
              type="button"
              onClick={() => setShowSaveDialog(true)}
              style={{
                padding: '4px 8px',
                fontSize: '0.8rem',
                background: '#e6fffa',
                border: '1px solid #81e6d9',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              💾 Save Current
            </button>
            
            {selectedTemplate && (
              <button
                type="button"
                onClick={() => deleteTemplate(selectedTemplate)}
                style={{
                  padding: '4px 8px',
                  fontSize: '0.8rem',
                  background: '#fed7d7',
                  border: '1px solid #fc8181',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  color: '#c53030'
                }}
              >
                🗑️ Delete
              </button>
            )}
          </div>
          
          {/* Save Dialog */}
          {showSaveDialog && (
            <div style={{ 
              marginTop: '12px', 
              padding: '12px', 
              border: '1px solid #e2e8f0', 
              borderRadius: '6px',
              background: 'white'
            }}>
              <div style={{ fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>Save as Template:</div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input
                  type="text"
                  placeholder="Template name..."
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  style={{
                    padding: '4px 8px',
                    fontSize: '0.8rem',
                    border: '1px solid #e2e8f0',
                    borderRadius: '4px',
                    flex: 1
                  }}
                />
                <button
                  type="button"
                  onClick={saveAsTemplate}
                  style={{
                    padding: '4px 12px',
                    fontSize: '0.8rem',
                    background: '#48bb78',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowSaveDialog(false);
                    setTemplateName('');
                  }}
                  style={{
                    padding: '4px 12px',
                    fontSize: '0.8rem',
                    background: '#9ca3af',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        <div style={{ 
          border: '1px solid #e2e8f0', 
          borderRadius: '8px', 
          overflow: 'hidden',
          minHeight: '350px'
        }}>
          <Editor
            height="350px"
            defaultLanguage="json"
            value={profilesJson}
            onChange={(value) => setProfilesJson(value || '')}
            theme="vs-light"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              roundedSelection: false,
              scrollBeyondLastLine: false,
              automaticLayout: true,
              formatOnPaste: true,
              formatOnType: true,
              tabSize: 2,
              insertSpaces: true,
              wordWrap: 'on',
              folding: true,
              bracketPairColorization: { enabled: true },
              suggest: {
                showKeywords: false,
                showSnippets: false
              }
            }}
          />
        </div>
        <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '4px' }}>
          Array of profile objects with id_profile, output_type, and config settings
        </div>
      </div>
          </div>
        )}

        {activeTab === 's3' && (
          <div>
      {/* S3 Output Configuration */}
      <div className="form-group">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <label style={{ fontSize: '0.9rem', fontWeight: '600' }}>
            S3 Output Configuration (JSON Object):
          </label>
          <button
            type="button"
            onClick={() => setS3ConfigJson(formatJson(s3ConfigJson))}
            style={{
              padding: '4px 8px',
              fontSize: '0.7rem',
              background: '#f8f9fa',
              border: '1px solid #e2e8f0',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            🎨 Format
          </button>
        </div>
        <div style={{ 
          border: '1px solid #e2e8f0', 
          borderRadius: '8px', 
          overflow: 'hidden',
          minHeight: '180px'
        }}>
          <Editor
            height="180px"
            defaultLanguage="json"
            value={s3ConfigJson}
            onChange={(value) => setS3ConfigJson(value || '')}
            theme="vs-light"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              roundedSelection: false,
              scrollBeyondLastLine: false,
              automaticLayout: true,
              formatOnPaste: true,
              formatOnType: true,
              tabSize: 2,
              insertSpaces: true,
              wordWrap: 'on',
              folding: true,
              bracketPairColorization: { enabled: true },
              suggest: {
                showKeywords: false,
                showSnippets: false
              }
            }}
          />
        </div>
        <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '4px' }}>
          S3 output settings with base_path and folder_structure
        </div>
      </div>

      {/* Config File Upload */}
      <div className="form-group">
        <label style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '8px', display: 'block' }}>
          Or load from JSON file:
        </label>
        <input
          type="file"
          accept=".json"
          onChange={(e) => e.target.files[0] && handleConfigFileSelect(e.target.files[0])}
          className="form-control"
          style={{ fontSize: '0.9rem' }}
        />
        <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '4px' }}>
          Upload a JSON file containing profiles and s3_output_config
        </div>
      </div>
          </div>
        )}

        {activeTab === 'face' && (
          <div>
      {/* Face Detection Configuration */}
      <div className="form-group">
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
          <input
            id="face-detection-enabled"
            type="checkbox"
            checked={faceDetectionEnabled}
            onChange={(e) => setFaceDetectionEnabled(e.target.checked)}
            style={{ marginRight: '8px' }}
          />
          <label htmlFor="face-detection-enabled" style={{ fontSize: '0.9rem', fontWeight: '600', margin: 0 }}>
            🤖 Enable Face Detection
          </label>
        </div>
        
        {faceDetectionEnabled && (
          <div style={{ 
            border: '1px solid #e2e8f0', 
            borderRadius: '8px', 
            padding: '12px', 
            background: '#f9fafb',
            marginBottom: '12px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: '600' }}>
                Face Detection Configuration:
              </label>
              <button
                type="button"
                onClick={() => setFaceDetectionConfig(formatJson(faceDetectionConfig))}
                style={{
                  padding: '4px 8px',
                  fontSize: '0.7rem',
                  background: '#f8f9fa',
                  border: '1px solid #e2e8f0',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                🎨 Format
              </button>
            </div>
            
            <div style={{ 
              border: '1px solid #e2e8f0', 
              borderRadius: '8px', 
              overflow: 'hidden',
              minHeight: '200px'
            }}>
              <Editor
                height="200px"
                defaultLanguage="json"
                value={faceDetectionConfig}
                onChange={(value) => setFaceDetectionConfig(value || '')}
                theme="vs-light"
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  formatOnPaste: true,
                  formatOnType: true,
                  tabSize: 2,
                  insertSpaces: true,
                  wordWrap: 'on',
                  folding: true,
                  bracketPairColorization: { enabled: true }
                }}
              />
            </div>
            
            <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '4px' }}>
              Configuration for face detection, clustering, and avatar generation
            </div>
            
            {/* Quick Settings */}
            <div style={{ marginTop: '8px' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: '600', marginBottom: '4px' }}>Quick Settings:</div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => setFaceDetectionConfig(JSON.stringify({
                    "enabled": true,
                    "similarity_threshold": 0.7,
                    "min_faces_in_group": 5,
                    "sample_interval": 3,
                    "face_detector_size": "640x640",
                    "face_detector_score_threshold": 0.6,
                    "save_faces": true,
                    "avatar_size": 112,
                    "avatar_quality": 90
                  }, null, 2))}
                  style={{
                    padding: '3px 8px',
                    fontSize: '0.7rem',
                    background: '#e6fffa',
                    border: '1px solid #81e6d9',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  🎯 High Quality
                </button>
                <button
                  type="button"
                  onClick={() => setFaceDetectionConfig(JSON.stringify({
                    "enabled": true,
                    "similarity_threshold": 0.5,
                    "min_faces_in_group": 2,
                    "sample_interval": 10,
                    "face_detector_size": "320x320",
                    "face_detector_score_threshold": 0.4,
                    "save_faces": true,
                    "avatar_size": 64,
                    "avatar_quality": 75
                  }, null, 2))}
                  style={{
                    padding: '3px 8px',
                    fontSize: '0.7rem',
                    background: '#fff5f5',
                    border: '1px solid #fed7d7',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  ⚡ Fast Mode
                </button>
                <button
                  type="button"
                  onClick={() => setFaceDetectionConfig(JSON.stringify({
                    "enabled": true,
                    "similarity_threshold": 0.6,
                    "min_faces_in_group": 1,
                    "sample_interval": 5,
                    "face_detector_size": "640x640",
                    "face_detector_score_threshold": 0.5,
                    "save_faces": true,
                    "avatar_size": 112,
                    "avatar_quality": 85
                  }, null, 2))}
                  style={{
                    padding: '3px 8px',
                    fontSize: '0.7rem',
                    background: '#f0fff4',
                    border: '1px solid #9ae6b4',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  ⚖️ Balanced
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
          </div>
        )}

        {activeTab === 'webhook' && (
          <div>
            {/* Callback Configuration */}
            <div className="form-group" style={{ 
              border: '1px solid #e2e8f0', 
              borderRadius: '8px', 
              padding: '16px', 
              background: '#f8fafc' 
            }}>
              <label style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '12px', display: 'block' }}>
                🔔 Notification Settings (Optional)
              </label>
              
              {/* Callback Type Selection */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '0.85rem', fontWeight: '600', marginBottom: '8px', display: 'block' }}>
                  Notification Method:
                </label>
                <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
                  <label style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    cursor: 'pointer',
                    padding: '8px 12px',
                    background: callbackType === 'webhook' ? '#e6fffa' : '#f9fafb',
                    borderRadius: '6px',
                    border: callbackType === 'webhook' ? '2px solid #10b981' : '2px solid #e2e8f0',
                    fontSize: '0.85rem'
                  }}>
                    <input
                      type="radio"
                      value="webhook"
                      checked={callbackType === 'webhook'}
                      onChange={(e) => setCallbackType(e.target.value)}
                      style={{ marginRight: '8px' }}
                    />
                    🌐 Webhook URL
                  </label>
                  <label style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    cursor: 'pointer',
                    padding: '8px 12px',
                    background: callbackType === 'pubsub' ? '#e6fffa' : '#f9fafb',
                    borderRadius: '6px',
                    border: callbackType === 'pubsub' ? '2px solid #10b981' : '2px solid #e2e8f0',
                    fontSize: '0.85rem'
                  }}>
                    <input
                      type="radio"
                      value="pubsub"
                      checked={callbackType === 'pubsub'}
                      onChange={(e) => setCallbackType(e.target.value)}
                      style={{ marginRight: '8px' }}
                    />
                    ☁️ PubSub Topic
                  </label>
                </div>
              </div>

              {/* Webhook Configuration */}
              {callbackType === 'webhook' && (
                <div style={{ marginBottom: '12px' }}>
                  <input
                    type="url"
                    className="form-control"
                    placeholder="https://your-webhook.com/callback"
                    value={callbackUrl}
                    onChange={(e) => setCallbackUrl(e.target.value)}
                    style={{ fontSize: '0.9rem', marginBottom: '8px' }}
                  />
                  <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                    Webhook URL to receive task completion notifications with full result data
                  </div>
                </div>
              )}

              {/* PubSub Configuration */}
              {callbackType === 'pubsub' && (
                <div style={{ marginBottom: '12px' }}>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="your-pubsub-topic-name"
                    value={pubsubTopic}
                    onChange={(e) => setPubsubTopic(e.target.value)}
                    style={{ fontSize: '0.9rem', marginBottom: '8px' }}
                  />
                  <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                    PubSub topic name to publish task completion notifications
                  </div>
                </div>
              )}

              {callbackType === 'webhook' && callbackUrl && (
                <div>
                  <label style={{ fontSize: '0.85rem', fontWeight: '600', marginBottom: '8px', display: 'block' }}>
                    Authentication:
                  </label>
                  
                  <div style={{ marginBottom: '12px' }}>
                    <select
                      value={callbackAuth.type}
                      onChange={(e) => setCallbackAuth({...callbackAuth, type: e.target.value})}
                      style={{
                        padding: '8px 12px',
                        fontSize: '0.85rem',
                        border: '1px solid #d1d5db',
                        borderRadius: '6px',
                        background: 'white',
                        width: '200px'
                      }}
                    >
                      <option value="none">No Authentication</option>
                      <option value="bearer">Bearer Token</option>
                      <option value="basic">Basic Auth</option>
                      <option value="header">Custom Headers</option>
                    </select>
                  </div>

                  {callbackAuth.type === 'bearer' && (
                    <div style={{ marginBottom: '8px' }}>
                      <input
                        type="password"
                        placeholder="Bearer token"
                        value={callbackAuth.token}
                        onChange={(e) => setCallbackAuth({...callbackAuth, token: e.target.value})}
                        style={{
                          padding: '8px 12px',
                          fontSize: '0.85rem',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          width: '100%'
                        }}
                      />
                    </div>
                  )}

                  {callbackAuth.type === 'basic' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
                      <input
                        type="text"
                        placeholder="Username"
                        value={callbackAuth.username}
                        onChange={(e) => setCallbackAuth({...callbackAuth, username: e.target.value})}
                        style={{
                          padding: '8px 12px',
                          fontSize: '0.85rem',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px'
                        }}
                      />
                      <input
                        type="password"
                        placeholder="Password"
                        value={callbackAuth.password}
                        onChange={(e) => setCallbackAuth({...callbackAuth, password: e.target.value})}
                        style={{
                          padding: '8px 12px',
                          fontSize: '0.85rem',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px'
                        }}
                      />
                    </div>
                  )}

                  {callbackAuth.type === 'header' && (
                    <div style={{ marginBottom: '8px' }}>
                      <textarea
                        placeholder='{"Authorization": "Api-Key your-key", "X-Custom-Header": "value"}'
                        value={JSON.stringify(callbackAuth.headers, null, 2)}
                        onChange={(e) => {
                          try {
                            const headers = JSON.parse(e.target.value);
                            setCallbackAuth({...callbackAuth, headers});
                          } catch {
                            // Invalid JSON, don't update
                          }
                        }}
                        style={{
                          padding: '8px 12px',
                          fontSize: '0.8rem',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          width: '100%',
                          height: '80px',
                          fontFamily: 'monospace',
                          resize: 'vertical'
                        }}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
        </>
        </div>
      </div>
      </div>

        {/* Profile Manager Modal */}
        {showProfileManager && (
            <ProfileTemplateManager
                showAsModal={true}
                onClose={() => setShowProfileManager(false)}
                onProfilesLoad={handleProfilesLoad}
            />
        )}
    </div>
  );
};

export default Upload;