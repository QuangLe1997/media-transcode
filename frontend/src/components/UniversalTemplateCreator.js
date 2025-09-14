import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import api from '../api';

const UniversalTemplateCreator = ({ onClose, onTemplateCreated }) => {
  const [templateName, setTemplateName] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');
  const [templateVersion, setTemplateVersion] = useState('2.0');
  const [profiles, setProfiles] = useState([]);
  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const addProfile = () => {
    const newProfile = {
      id: Date.now(),
      id_profile: '',
      input_type: '',
      output_filename: '',
      config: JSON.stringify({
        output_format: 'webp',
        width: 720,
        quality: 85,
        animated: true,
        lossless: false
      }, null, 2)
    };
    setProfiles([...profiles, newProfile]);
  };

  const removeProfile = (profileId) => {
    setProfiles(profiles.filter(p => p.id !== profileId));
  };

  const updateProfile = (profileId, field, value) => {
    setProfiles(profiles.map(p => 
      p.id === profileId ? { ...p, [field]: value } : p
    ));
  };

  const getTemplateData = () => {
    if (!templateName.trim()) {
      throw new Error('Template name is required');
    }

    const profilesData = profiles.map(p => {
      if (!p.id_profile.trim()) {
        throw new Error('Profile ID is required for all profiles');
      }

      let config;
      try {
        config = JSON.parse(p.config);
      } catch (e) {
        throw new Error(`Invalid JSON in profile "${p.id_profile}": ${e.message}`);
      }

      const profileData = {
        id_profile: p.id_profile.trim(),
        config: config
      };

      if (p.input_type) profileData.input_type = p.input_type;
      if (p.output_filename) profileData.output_filename = p.output_filename.trim();

      return profileData;
    });

    if (profilesData.length === 0) {
      throw new Error('At least one profile is required');
    }

    return {
      name: templateName.trim(),
      description: templateDescription.trim() || undefined,
      profiles: profilesData
    };
  };

  const validateTemplate = async () => {
    try {
      setIsValidating(true);
      setValidationResult(null);
      
      const templateData = getTemplateData();
      
      // For validation, we'll use the /transcode endpoint with dummy data
      const formData = new FormData();
      formData.append('profiles', JSON.stringify(templateData.profiles));
      formData.append('s3_output_config', JSON.stringify({
        enabled: false,
        bucket: 'test',
        base_folder: 'test'
      }));
      formData.append('media_url', 'https://example.com/test.mp4');
      
      const response = await fetch('/api/transcode', {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        setValidationResult({
          type: 'success',
          message: `✅ Template is valid! All ${templateData.profiles.length} profiles passed validation.`
        });
      } else {
        const error = await response.json();
        setValidationResult({
          type: 'error',
          message: `❌ Validation failed: ${error.detail || 'Unknown error'}`
        });
      }
    } catch (error) {
      setValidationResult({
        type: 'error',
        message: `❌ Validation error: ${error.message}`
      });
    } finally {
      setIsValidating(false);
    }
  };

  const saveTemplate = async () => {
    try {
      setIsSaving(true);
      setValidationResult(null);

      const templateData = getTemplateData();
      
      // Convert v2 format to v1 legacy format for API compatibility
      const legacyProfiles = templateData.profiles.map(profile => {
        // Determine output_type based on config.output_format
        let output_type = 'video'; // default
        const outputFormat = profile.config.output_format;
        
        if (outputFormat === 'webp') {
          output_type = 'webp';
        } else if (outputFormat === 'jpg' || outputFormat === 'jpeg') {
          output_type = 'image';
        } else if (outputFormat === 'mp4') {
          output_type = 'video';
        }

        // Create legacy profile structure
        const legacyProfile = {
          id_profile: profile.id_profile,
          output_type: output_type,
          input_type: profile.input_type || null
        };

        // Map config to appropriate legacy config structure
        if (output_type === 'webp') {
          legacyProfile.webp_config = {
            width: profile.config.width || null,
            height: profile.config.height || null,
            quality: profile.config.quality || 85,
            fps: profile.config.fps || null,
            duration: profile.config.duration || null,
            start_time: profile.config.start_time || 0,
            speed: profile.config.speed || 1,
            lossless: profile.config.lossless || false,
            animated: profile.config.animated !== false,
            loop: profile.config.loop || 0,
            preset: profile.config.preset || 'default'
          };
        } else if (output_type === 'image') {
          legacyProfile.image_config = {
            quality: profile.config.jpeg_quality || profile.config.quality || 90,
            optimize: profile.config.optimize !== false,
            progressive: profile.config.progressive || false
          };
        } else if (output_type === 'video') {
          legacyProfile.video_config = {
            codec: profile.config.codec || 'h264',
            crf: profile.config.crf || 23,
            preset: profile.config.mp4_preset || 'medium',
            profile: profile.config.profile || 'high',
            level: profile.config.level || '4.1',
            pixel_format: profile.config.pixel_format || 'yuv420p',
            audio_codec: profile.config.audio_codec || 'aac',
            audio_bitrate: profile.config.audio_bitrate || '128k',
            audio_sample_rate: profile.config.audio_sample_rate || 44100,
            two_pass: profile.config.two_pass || false,
            hardware_accel: profile.config.hardware_accel || false
          };
        }

        return legacyProfile;
      });

      // Create template using legacy API
      const response = await api.post('/config-templates', {
        name: `${templateData.name}_v2_universal`,
        config: legacyProfiles
      });

      // Also save to localStorage for v2 format reference
      const existingTemplates = JSON.parse(localStorage.getItem('universal-templates') || '[]');
      const newTemplate = {
        id: response.data.template_id,
        api_id: response.data.template_id,
        ...templateData,
        created_at: response.data.created_at,
        format_version: 'v2'
      };
      
      existingTemplates.push(newTemplate);
      localStorage.setItem('universal-templates', JSON.stringify(existingTemplates));
      
      setValidationResult({
        type: 'success',
        message: `✅ Template "${templateData.name}" created successfully!\n\nAPI ID: ${response.data.template_id}\nFormat: Universal v2\n\nYou can now use this template in transcode operations.`
      });

      if (onTemplateCreated) {
        onTemplateCreated(newTemplate);
      }

      // Close after 3 seconds
      setTimeout(() => {
        onClose();
      }, 3000);

    } catch (error) {
      let errorMessage = `❌ Save error: ${error.message}`;
      
      if (error.response?.data?.detail) {
        errorMessage = `❌ API Error: ${error.response.data.detail}`;
      }
      
      setValidationResult({
        type: 'error',
        message: errorMessage
      });
    } finally {
      setIsSaving(false);
    }
  };

  const getConfigExample = (outputFormat) => {
    const examples = {
      webp: {
        output_format: 'webp',
        width: 720,
        quality: 85,
        fps: 12.0,
        duration: 3.0,
        animated: true,
        lossless: false,
        preset: 'picture'
      },
      mp4: {
        output_format: 'mp4',
        codec: 'h264',
        crf: 23,
        mp4_preset: 'medium',
        profile: 'high',
        level: '4.1',
        audio_codec: 'aac',
        audio_bitrate: '128k',
        two_pass: false
      },
      jpg: {
        output_format: 'jpg',
        jpeg_quality: 90,
        optimize: true,
        progressive: false
      },
      jpeg: {
        output_format: 'jpeg',
        jpeg_quality: 95,
        optimize: false,
        progressive: false
      }
    };
    return examples[outputFormat] || examples.webp;
  };

  const insertConfigExample = (profileId, format) => {
    const example = getConfigExample(format);
    updateProfile(profileId, 'config', JSON.stringify(example, null, 2));
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '24px',
        width: '95vw',
        maxWidth: '1200px',
        maxHeight: '90vh',
        overflow: 'hidden',
        position: 'relative'
      }}>
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '12px',
            right: '12px',
            background: '#f3f4f6',
            border: 'none',
            borderRadius: '50%',
            width: '32px',
            height: '32px',
            cursor: 'pointer',
            fontSize: '18px',
            color: '#6b7280'
          }}
        >
          ×
        </button>

        <div style={{ height: '85vh', overflow: 'auto', paddingRight: '12px' }}>
          <h2 style={{ marginTop: 0, marginBottom: '24px', color: '#374151' }}>
            🎨 Create Universal Template (v2)
          </h2>

          {/* Template Basic Info */}
          <div style={{
            marginBottom: '24px',
            padding: '20px',
            background: '#f8f9fa',
            borderRadius: '8px',
            border: '1px solid #e9ecef'
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '16px', color: '#495057' }}>
              📋 Template Information
            </h3>
            
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: '16px',
              marginBottom: '16px'
            }}>
              <div>
                <label style={{
                  display: 'block',
                  marginBottom: '6px',
                  fontWeight: '600',
                  color: '#495057',
                  fontSize: '0.9rem'
                }}>
                  Template Name *
                </label>
                <input
                  type="text"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  placeholder="e.g., faceswap_template"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    border: '1px solid #ced4da',
                    borderRadius: '4px',
                    fontSize: '0.9rem'
                  }}
                />
              </div>
              <div>
                <label style={{
                  display: 'block',
                  marginBottom: '6px',
                  fontWeight: '600',
                  color: '#495057',
                  fontSize: '0.9rem'
                }}>
                  Version
                </label>
                <input
                  type="text"
                  value={templateVersion}
                  onChange={(e) => setTemplateVersion(e.target.value)}
                  placeholder="e.g., 2.0"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    border: '1px solid #ced4da',
                    borderRadius: '4px',
                    fontSize: '0.9rem'
                  }}
                />
              </div>
              <div>
                <button
                  onClick={addProfile}
                  style={{
                    marginTop: '28px',
                    width: '100%',
                    padding: '10px',
                    background: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.9rem',
                    fontWeight: '600'
                  }}
                >
                  ➕ Add Profile
                </button>
              </div>
            </div>
            
            <div>
              <label style={{
                display: 'block',
                marginBottom: '6px',
                fontWeight: '600',
                color: '#495057',
                fontSize: '0.9rem'
              }}>
                Description
              </label>
              <textarea
                value={templateDescription}
                onChange={(e) => setTemplateDescription(e.target.value)}
                placeholder="Describe what this template is for..."
                rows="2"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '0.9rem',
                  resize: 'vertical'
                }}
              />
            </div>
          </div>

          {/* Profiles */}
          <div>
            <h3 style={{ marginBottom: '16px', color: '#495057' }}>
              🎯 Profiles ({profiles.length})
            </h3>
            
            {profiles.length === 0 ? (
              <div style={{
                padding: '40px',
                textAlign: 'center',
                color: '#6c757d',
                background: '#f8f9fa',
                borderRadius: '8px',
                border: '2px dashed #dee2e6'
              }}>
                No profiles added yet. Click "Add Profile" to start building your template.
              </div>
            ) : (
              profiles.map((profile, index) => (
                <div
                  key={profile.id}
                  style={{
                    marginBottom: '24px',
                    padding: '20px',
                    background: '#ffffff',
                    border: '1px solid #dee2e6',
                    borderRadius: '8px',
                    position: 'relative'
                  }}
                >
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '16px'
                  }}>
                    <h4 style={{ margin: 0, color: '#495057' }}>
                      🎯 Profile {index + 1}
                    </h4>
                    <button
                      onClick={() => removeProfile(profile.id)}
                      style={{
                        background: '#dc3545',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '6px 12px',
                        cursor: 'pointer',
                        fontSize: '0.8rem'
                      }}
                    >
                      🗑️ Remove
                    </button>
                  </div>

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr',
                    gap: '16px',
                    marginBottom: '16px'
                  }}>
                    <div>
                      <label style={{
                        display: 'block',
                        marginBottom: '6px',
                        fontWeight: '600',
                        color: '#495057',
                        fontSize: '0.9rem'
                      }}>
                        Profile ID *
                      </label>
                      <input
                        type="text"
                        value={profile.id_profile}
                        onChange={(e) => updateProfile(profile.id, 'id_profile', e.target.value)}
                        placeholder="e.g., webp_preview_high"
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          border: '1px solid #ced4da',
                          borderRadius: '4px',
                          fontSize: '0.9rem'
                        }}
                      />
                    </div>
                    <div>
                      <label style={{
                        display: 'block',
                        marginBottom: '6px',
                        fontWeight: '600',
                        color: '#495057',
                        fontSize: '0.9rem'
                      }}>
                        Input Type
                      </label>
                      <select
                        value={profile.input_type}
                        onChange={(e) => updateProfile(profile.id, 'input_type', e.target.value)}
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          border: '1px solid #ced4da',
                          borderRadius: '4px',
                          fontSize: '0.9rem'
                        }}
                      >
                        <option value="">Any</option>
                        <option value="video">Video</option>
                        <option value="image">Image</option>
                      </select>
                    </div>
                    <div>
                      <label style={{
                        display: 'block',
                        marginBottom: '6px',
                        fontWeight: '600',
                        color: '#495057',
                        fontSize: '0.9rem'
                      }}>
                        Output Filename
                      </label>
                      <input
                        type="text"
                        value={profile.output_filename}
                        onChange={(e) => updateProfile(profile.id, 'output_filename', e.target.value)}
                        placeholder="e.g., preview_hd"
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          border: '1px solid #ced4da',
                          borderRadius: '4px',
                          fontSize: '0.9rem'
                        }}
                      />
                    </div>
                  </div>

                  <div>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '8px'
                    }}>
                      <label style={{
                        fontWeight: '600',
                        color: '#495057',
                        fontSize: '0.9rem'
                      }}>
                        Configuration (JSON)
                      </label>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <select
                          onChange={(e) => insertConfigExample(profile.id, e.target.value)}
                          defaultValue=""
                          style={{
                            padding: '4px 8px',
                            fontSize: '0.8rem',
                            border: '1px solid #dee2e6',
                            borderRadius: '4px'
                          }}
                        >
                          <option value="">📝 Insert Example</option>
                          <option value="webp">WebP Example</option>
                          <option value="mp4">MP4 Example</option>
                          <option value="jpg">JPG Example</option>
                          <option value="jpeg">JPEG Example</option>
                        </select>
                      </div>
                    </div>
                    
                    <div style={{
                      border: '1px solid #dee2e6',
                      borderRadius: '4px',
                      overflow: 'hidden'
                    }}>
                      <Editor
                        height="200px"
                        defaultLanguage="json"
                        value={profile.config}
                        onChange={(value) => updateProfile(profile.id, 'config', value || '')}
                        theme="vs-light"
                        options={{
                          minimap: { enabled: false },
                          fontSize: 13,
                          lineNumbers: 'on',
                          scrollBeyondLastLine: false,
                          automaticLayout: true,
                          wordWrap: 'on',
                          folding: true,
                          bracketPairColorization: { enabled: true }
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Validation Result */}
          {validationResult && (
            <div style={{
              padding: '12px 16px',
              borderRadius: '6px',
              marginBottom: '20px',
              backgroundColor: validationResult.type === 'error' ? '#f8d7da' : '#d1fae5',
              color: validationResult.type === 'error' ? '#721c24' : '#065f46',
              border: `1px solid ${validationResult.type === 'error' ? '#f5c6cb' : '#a7f3d0'}`,
              whiteSpace: 'pre-wrap'
            }}>
              {validationResult.message}
            </div>
          )}

          {/* Actions */}
          <div style={{
            display: 'flex',
            gap: '12px',
            justifyContent: 'flex-end',
            paddingTop: '20px',
            borderTop: '1px solid #dee2e6'
          }}>
            <button
              onClick={validateTemplate}
              disabled={isValidating || profiles.length === 0}
              style={{
                padding: '10px 20px',
                background: isValidating ? '#6c757d' : '#ffc107',
                color: isValidating ? 'white' : '#000',
                border: 'none',
                borderRadius: '4px',
                cursor: isValidating || profiles.length === 0 ? 'not-allowed' : 'pointer',
                fontSize: '0.9rem',
                fontWeight: '600'
              }}
            >
              {isValidating ? '🔄 Validating...' : '🔍 Validate'}
            </button>
            <button
              onClick={saveTemplate}
              disabled={isSaving || profiles.length === 0}
              style={{
                padding: '10px 20px',
                background: isSaving ? '#6c757d' : '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: isSaving || profiles.length === 0 ? 'not-allowed' : 'pointer',
                fontSize: '0.9rem',
                fontWeight: '600'
              }}
            >
              {isSaving ? '💾 Saving...' : '💾 Save Template'}
            </button>
            <button
              onClick={onClose}
              style={{
                padding: '10px 20px',
                background: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.9rem'
              }}
            >
              ❌ Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UniversalTemplateCreator;