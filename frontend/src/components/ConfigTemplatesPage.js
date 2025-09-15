import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import Editor from '@monaco-editor/react';

const ConfigTemplatesPage = () => {
  const [templates, setTemplates] = useState([]);
  const [sampleProfiles, setSampleProfiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('api'); // 'api' or 'samples'
  
  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  
  // Template data
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateName, setTemplateName] = useState('');
  const [templateProfiles, setTemplateProfiles] = useState(JSON.stringify([
    {
      "id_profile": "example_profile",
      "input_type": "video",
      "config": {
        "output_format": "mp4",
        "width": 720,
        "codec": "h264",
        "crf": 23,
        "audio_codec": "aac"
      }
    }
  ], null, 2));

  // Load templates and sample profiles on component mount
  useEffect(() => {
    loadTemplates();
    loadSampleProfiles();
  }, []);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const response = await api.get('/config-templates');
      // API returns templates with full data, no need for detail calls
      setTemplates(response.data.templates || []);
      setMessage({ type: 'success', text: `Loaded ${response.data.templates?.length || 0} API templates` });
    } catch (error) {
      console.error('Error loading templates:', error);
      setMessage({ type: 'error', text: 'Failed to load config templates' });
    } finally {
      setLoading(false);
    }
  };

  const loadSampleProfiles = async () => {
    try {
      // Sample profile files with example data
      const sampleFiles = [
        {
          filename: 'faces_swap_cleaned.json',
          name: 'FACES SWAP CLEANED',
          description: 'Face swap processing profiles with video/image variants',
          profiles: [
            { id_profile: "profile_bk", input_type: "video", config: { output_format: "gif", width: 120 }},
            { id_profile: "profile_1", input_type: "video", config: { output_format: "webp", width: 120 }},
            { id_profile: "profile_2", input_type: "video", config: { output_format: "webp", width: 160 }},
            { id_profile: "profile_3", input_type: "video", config: { output_format: "webp", width: 240 }}
          ]
        },
        {
          filename: 'icon.json',
          name: 'ICON PROFILES',
          description: 'Icon generation in multiple sizes (16px to 512px)',
          profiles: [
            { id_profile: "icon_16", input_type: "image", config: { output_format: "jpg", width: 16, height: 16 }},
            { id_profile: "icon_32", input_type: "image", config: { output_format: "jpg", width: 32, height: 32 }},
            { id_profile: "icon_64", input_type: "image", config: { output_format: "jpg", width: 64, height: 64 }}
          ]
        },
        {
          filename: 'popup_home.json', 
          name: 'POPUP HOME',
          description: 'Home popup content profiles with backup formats',
          profiles: [
            { id_profile: "profile_1", input_type: "video", config: { output_format: "webp", width: 360 }},
            { id_profile: "profile_bk", input_type: "video", config: { output_format: "gif", width: 360 }}
          ]
        },
        {
          filename: 'promoted_banner.json',
          name: 'PROMOTED BANNER', 
          description: 'Promotional banner profiles for marketing content',
          profiles: [
            { id_profile: "banner_small", input_type: "video", config: { output_format: "webp", width: 320 }},
            { id_profile: "banner_small_bk", input_type: "video", config: { output_format: "gif", width: 320 }}
          ]
        },
        {
          filename: 'promoted_baner.json',
          name: 'PROMOTED BANER (ALT)',
          description: 'Alternative promotional banner configurations', 
          profiles: [
            { id_profile: "profile_1", input_type: "video", config: { output_format: "webp", width: 360 }},
            { id_profile: "profile_bk", input_type: "video", config: { output_format: "gif", width: 360 }}
          ]
        },
        {
          filename: 'thumbnail.json',
          name: 'THUMBNAIL PROFILES',
          description: 'Video thumbnail generation with various qualities',
          profiles: [
            { id_profile: "profile_1", input_type: "video", config: { output_format: "webp", width: 120 }},
            { id_profile: "profile_bk", input_type: "video", config: { output_format: "gif", width: 120 }},
            { id_profile: "promoted_banner_bk", input_type: "video", config: { output_format: "gif", width: 320 }}
          ]
        }
      ];
      
      const samples = sampleFiles.map(file => ({
        template_id: `sample_${file.filename.replace('.json', '')}`,
        name: file.name,
        filename: file.filename,
        type: 'sample',
        created_at: '2024-01-01T00:00:00Z',
        profiles: file.profiles,
        description: file.description
      }));
      
      setSampleProfiles(samples);
    } catch (error) {
      console.error('Error loading sample profiles:', error);
    }
  };

  const handleCreateTemplate = async () => {
    if (!templateName.trim()) {
      setMessage({ type: 'error', text: 'Template name is required' });
      return;
    }

    try {
      const profiles = JSON.parse(templateProfiles);
      const response = await api.post('/config-templates', {
        name: templateName.trim(),
        description: null,
        profiles: profiles,
        s3_output_config: null,
        face_detection_config: null
      });

      setTemplates([...templates, response.data]);
      setShowCreateModal(false);
      setTemplateName('');
      setTemplateProfiles(JSON.stringify([
        {
          "id_profile": "example_web_video",
          "input_type": "video",
          "config": {
            "output_format": "mp4",
            "width": 1280,
            "height": 720,
            "codec": "h264",
            "crf": 23,
            "mp4_preset": "fast",
            "profile": "main",
            "pixel_format": "yuv420p",
            "audio_codec": "aac",
            "audio_bitrate": "128k",
            "verbose": false
          }
        }
      ], null, 2));
      setMessage({ type: 'success', text: `Template "${response.data.name}" created successfully` });
    } catch (error) {
      console.error('Error creating template:', error);
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to create template. Please check your JSON format.' 
      });
    }
  };

  const handleEditTemplate = async () => {
    if (!templateName.trim()) {
      setMessage({ type: 'error', text: 'Template name is required' });
      return;
    }

    try {
      const profiles = JSON.parse(templateProfiles);
      const response = await api.put(`/config-templates/${selectedTemplate.template_id}`, {
        name: templateName.trim(),
        description: selectedTemplate.description,
        profiles: profiles,
        s3_output_config: selectedTemplate.s3_output_config,
        face_detection_config: selectedTemplate.face_detection_config
      });

      setTemplates(templates.map(t => 
        t.template_id === selectedTemplate.template_id ? response.data : t
      ));
      setShowEditModal(false);
      setSelectedTemplate(null);
      setMessage({ type: 'success', text: `Template "${response.data.name}" updated successfully` });
    } catch (error) {
      console.error('Error updating template:', error);
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to update template. Please check your JSON format.' 
      });
    }
  };

  const handleDeleteTemplate = async () => {
    try {
      await api.delete(`/config-templates/${selectedTemplate.template_id}`);
      setTemplates(templates.filter(t => t.template_id !== selectedTemplate.template_id));
      setShowDeleteModal(false);
      setSelectedTemplate(null);
      setMessage({ type: 'success', text: `Template "${selectedTemplate.name}" deleted successfully` });
    } catch (error) {
      console.error('Error deleting template:', error);
      setMessage({ type: 'error', text: 'Failed to delete template' });
    }
  };

  const openCreateModal = () => {
    setTemplateName('');
    setTemplateProfiles(JSON.stringify([
      {
        "id_profile": "example_web_video",
        "input_type": "video",
        "config": {
          "output_format": "mp4",
          "width": 1280,
          "height": 720,
          "codec": "h264",
          "crf": 23,
          "mp4_preset": "fast",
          "profile": "main",
          "pixel_format": "yuv420p",
          "audio_codec": "aac",
          "audio_bitrate": "128k",
          "verbose": false
        }
      }
    ], null, 2));
    setShowCreateModal(true);
  };

  const openEditModal = (template) => {
    setSelectedTemplate(template);
    setTemplateName(template.name);
    setTemplateProfiles(JSON.stringify(template.config, null, 2));
    setShowEditModal(true);
  };

  const openViewModal = (template) => {
    setSelectedTemplate(template);
    setShowViewModal(true);
  };

  const openDeleteModal = (template) => {
    setSelectedTemplate(template);
    setShowDeleteModal(true);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      setMessage({ type: 'success', text: 'Template JSON copied to clipboard!' });
    }).catch(() => {
      setMessage({ type: 'error', text: 'Failed to copy to clipboard' });
    });
  };

  const useSampleProfile = (sample) => {
    // When user wants to use a sample profile as template
    setTemplateName(sample.name);
    setTemplateProfiles(JSON.stringify(sample.profiles || [], null, 2));
    setShowCreateModal(true);
  };

  const formatJson = (jsonString) => {
    try {
      const parsed = JSON.parse(jsonString);
      return JSON.stringify(parsed, null, 2);
    } catch (error) {
      return jsonString;
    }
  };

  // Filter templates and samples based on search term and active tab
  const filteredTemplates = templates.filter(template => 
    template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    template.template_id.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  const filteredSamples = sampleProfiles.filter(sample =>
    sample.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    sample.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  const currentItems = activeTab === 'api' ? filteredTemplates : filteredSamples;
  const totalItems = activeTab === 'api' ? templates.length : sampleProfiles.length;

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '20px' }}>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h2 style={{ margin: 0, fontSize: '1.8rem', fontWeight: '700', color: '#1f2937' }}>
            📋 Config Templates Manager
          </h2>
          <div style={{ display: 'flex', gap: '12px' }}>
            <Link 
              to="/upload" 
              style={{
                padding: '8px 16px',
                backgroundColor: '#6366f1',
                color: 'white',
                textDecoration: 'none',
                borderRadius: '6px',
                fontSize: '0.9rem',
                fontWeight: '500'
              }}
            >
              📤 Upload Page
            </Link>
            <button
              onClick={openCreateModal}
              style={{
                padding: '8px 16px',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.9rem',
                fontWeight: '500',
                cursor: 'pointer'
              }}
            >
              ➕ New Template
            </button>
          </div>
        </div>
        
        <p style={{ margin: 0, color: '#6b7280', fontSize: '0.95rem' }}>
          Manage transcode profile configuration templates for different media processing scenarios
        </p>
      </div>

      {/* Messages */}
      {message && (
        <div 
          style={{
            padding: '12px 16px',
            marginBottom: '20px',
            borderRadius: '6px',
            backgroundColor: message.type === 'error' ? '#fef2f2' : '#f0fdf4',
            border: message.type === 'error' ? '1px solid #fecaca' : '1px solid #bbf7d0',
            color: message.type === 'error' ? '#dc2626' : '#16a34a'
          }}
          onClick={() => setMessage(null)}
        >
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ 
          display: 'flex', 
          borderBottom: '2px solid #e2e8f0',
          gap: '0'
        }}>
          <button
            onClick={() => setActiveTab('api')}
            style={{
              padding: '12px 24px',
              fontSize: '0.95rem',
              fontWeight: '600',
              backgroundColor: activeTab === 'api' ? '#3b82f6' : 'transparent',
              color: activeTab === 'api' ? 'white' : '#6b7280',
              border: 'none',
              borderRadius: '8px 8px 0 0',
              cursor: 'pointer',
              borderBottom: activeTab === 'api' ? '2px solid #3b82f6' : '2px solid transparent',
              transition: 'all 0.2s ease'
            }}
          >
            🌐 API Templates ({templates.length})
          </button>
          <button
            onClick={() => setActiveTab('samples')}
            style={{
              padding: '12px 24px',
              fontSize: '0.95rem',
              fontWeight: '600',
              backgroundColor: activeTab === 'samples' ? '#10b981' : 'transparent',
              color: activeTab === 'samples' ? 'white' : '#6b7280',
              border: 'none',
              borderRadius: '8px 8px 0 0',
              cursor: 'pointer',
              borderBottom: activeTab === 'samples' ? '2px solid #10b981' : '2px solid transparent',
              transition: 'all 0.2s ease'
            }}
          >
            📁 Sample Profiles ({sampleProfiles.length})
          </button>
        </div>
      </div>

      {/* Search and Stats */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '20px',
        padding: '16px',
        backgroundColor: '#f8fafc',
        borderRadius: '8px',
        border: '1px solid #e2e8f0'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <input
            type="text"
            placeholder="🔍 Search templates..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: '8px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '0.9rem',
              width: '250px'
            }}
          />
          <button
            onClick={loadTemplates}
            disabled={loading}
            style={{
              padding: '8px 12px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '0.9rem',
              cursor: 'pointer',
              opacity: loading ? 0.6 : 1
            }}
          >
            🔄 {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
        
        <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>
          📊 Total: <strong>{currentItems.length}</strong> {activeTab === 'api' ? 'templates' : 'samples'}
          {searchTerm && ` (filtered from ${totalItems})`}
        </div>
      </div>

      {/* Main Content Grid */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
          <div style={{ fontSize: '2rem', marginBottom: '10px' }}>⏳</div>
          Loading {activeTab === 'api' ? 'templates' : 'sample profiles'}...
        </div>
      ) : currentItems.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
          <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📭</div>
          <h3 style={{ margin: '0 0 8px 0' }}>No {activeTab === 'api' ? 'templates' : 'samples'} found</h3>
          <p style={{ margin: 0 }}>
            {searchTerm 
              ? `No ${activeTab === 'api' ? 'templates' : 'samples'} match "${searchTerm}"` 
              : activeTab === 'api' 
                ? 'Create your first config template to get started'
                : 'Sample profiles will be loaded automatically'
            }
          </p>
          {!searchTerm && activeTab === 'api' && (
            <button
              onClick={openCreateModal}
              style={{
                marginTop: '16px',
                padding: '10px 20px',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.9rem',
                cursor: 'pointer'
              }}
            >
              ➕ Create First Template
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '20px' }}>
          {activeTab === 'api' ? (
            // API Templates
            filteredTemplates.map((template) => (
            <div
              key={template.template_id}
              style={{
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '20px',
                backgroundColor: 'white',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                transition: 'transform 0.2s ease, box-shadow 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.1)';
              }}
            >
              {/* Template Header */}
              <div style={{ marginBottom: '12px' }}>
                <h3 style={{ 
                  margin: '0 0 8px 0', 
                  fontSize: '1.1rem', 
                  fontWeight: '600',
                  color: '#1f2937',
                  lineHeight: '1.3'
                }}>
                  {template.name}
                </h3>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', fontFamily: 'monospace' }}>
                  ID: {template.template_id}
                </div>
              </div>

              {/* Template Info */}
              <div style={{ marginBottom: '16px' }}>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  marginBottom: '8px'
                }}>
                  <span style={{ fontSize: '0.85rem', color: '#4b5563' }}>
                    📁 {template.config?.length || 0} profiles
                  </span>
                  <span style={{ 
                    fontSize: '0.75rem', 
                    color: '#6b7280',
                    padding: '2px 6px',
                    backgroundColor: '#f3f4f6',
                    borderRadius: '4px'
                  }}>
                    {new Date(template.created_at).toLocaleDateString()}
                  </span>
                </div>

                {/* Profile Types Preview */}
                <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                  Types: {[...new Set(template.config?.map(p => p.output_type) || [])].join(', ') || 'N/A'}
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  onClick={() => openViewModal(template)}
                  style={{
                    padding: '6px 12px',
                    fontSize: '0.8rem',
                    backgroundColor: '#3b82f6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    flex: 1
                  }}
                >
                  👁️ View
                </button>
                <button
                  onClick={() => openEditModal(template)}
                  style={{
                    padding: '6px 12px',
                    fontSize: '0.8rem',
                    backgroundColor: '#f59e0b',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    flex: 1
                  }}
                >
                  ✏️ Edit
                </button>
                <button
                  onClick={() => copyToClipboard(JSON.stringify(template.config, null, 2))}
                  style={{
                    padding: '6px 12px',
                    fontSize: '0.8rem',
                    backgroundColor: '#8b5cf6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    flex: 1
                  }}
                >
                  📋 Copy
                </button>
                <button
                  onClick={() => openDeleteModal(template)}
                  style={{
                    padding: '6px 12px',
                    fontSize: '0.8rem',
                    backgroundColor: '#ef4444',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    flex: 1
                  }}
                >
                  🗑️ Delete
                </button>
              </div>
            </div>
            ))
          ) : (
            // Sample Profiles
            filteredSamples.map((sample) => (
              <div
                key={sample.template_id}
                style={{
                  border: '1px solid #10b981',
                  borderRadius: '8px',
                  padding: '20px',
                  backgroundColor: '#f0fdf4',
                  boxShadow: '0 1px 3px rgba(16, 185, 129, 0.1)',
                  transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 4px 6px rgba(16, 185, 129, 0.2)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 1px 3px rgba(16, 185, 129, 0.1)';
                }}
              >
                {/* Sample Header */}
                <div style={{ marginBottom: '12px' }}>
                  <h3 style={{ 
                    margin: '0 0 8px 0', 
                    fontSize: '1.1rem', 
                    fontWeight: '600',
                    color: '#065f46',
                    lineHeight: '1.3'
                  }}>
                    📁 {sample.name}
                  </h3>
                  <div style={{ fontSize: '0.75rem', color: '#059669', fontFamily: 'monospace' }}>
                    File: {sample.filename}
                  </div>
                </div>

                {/* Sample Info */}
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ 
                    fontSize: '0.85rem', 
                    color: '#047857',
                    marginBottom: '8px'
                  }}>
                    {sample.description}
                  </div>
                  <span style={{ 
                    fontSize: '0.75rem', 
                    color: '#059669',
                    padding: '2px 8px',
                    backgroundColor: '#d1fae5',
                    borderRadius: '4px'
                  }}>
                    📦 Sample Profile
                  </span>
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => useSampleProfile(sample)}
                    style={{
                      padding: '6px 12px',
                      fontSize: '0.8rem',
                      backgroundColor: '#10b981',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      flex: 1
                    }}
                  >
                    ✨ Use as Template
                  </button>
                  <button
                    onClick={() => openViewModal(sample)}
                    style={{
                      padding: '6px 12px',
                      fontSize: '0.8rem',
                      backgroundColor: '#059669',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      flex: 1
                    }}
                  >
                    👁️ Preview
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
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
            borderRadius: '8px',
            padding: '24px',
            width: '100%',
            maxWidth: '800px',
            maxHeight: '90vh',
            overflow: 'auto'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '1.3rem', fontWeight: '600' }}>
              ➕ Create New Template
            </h3>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '6px', display: 'block' }}>
                Template Name:
              </label>
              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder="Enter template name..."
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '0.9rem'
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <label style={{ fontSize: '0.9rem', fontWeight: '600' }}>
                  Profile Configuration (JSON):
                </label>
                <button
                  onClick={() => setTemplateProfiles(formatJson(templateProfiles))}
                  style={{
                    padding: '4px 8px',
                    fontSize: '0.75rem',
                    backgroundColor: '#f3f4f6',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  🎨 Format JSON
                </button>
              </div>
              <div style={{ 
                border: '1px solid #d1d5db', 
                borderRadius: '6px', 
                overflow: 'hidden',
                height: '300px'
              }}>
                <Editor
                  height="300px"
                  defaultLanguage="json"
                  value={templateProfiles}
                  onChange={(value) => setTemplateProfiles(value || '')}
                  theme="vs-light"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    formatOnPaste: true,
                    formatOnType: true,
                    tabSize: 2
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowCreateModal(false)}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                ❌ Cancel
              </button>
              <button
                onClick={handleCreateTemplate}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  backgroundColor: '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                ✅ Create Template
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedTemplate && (
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
            borderRadius: '8px',
            padding: '24px',
            width: '100%',
            maxWidth: '800px',
            maxHeight: '90vh',
            overflow: 'auto'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '1.3rem', fontWeight: '600' }}>
              ✏️ Edit Template: {selectedTemplate.name}
            </h3>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '6px', display: 'block' }}>
                Template Name:
              </label>
              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '0.9rem'
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <label style={{ fontSize: '0.9rem', fontWeight: '600' }}>
                  Profile Configuration (JSON):
                </label>
                <button
                  onClick={() => setTemplateProfiles(formatJson(templateProfiles))}
                  style={{
                    padding: '4px 8px',
                    fontSize: '0.75rem',
                    backgroundColor: '#f3f4f6',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  🎨 Format JSON
                </button>
              </div>
              <div style={{ 
                border: '1px solid #d1d5db', 
                borderRadius: '6px', 
                overflow: 'hidden',
                height: '300px'
              }}>
                <Editor
                  height="300px"
                  defaultLanguage="json"
                  value={templateProfiles}
                  onChange={(value) => setTemplateProfiles(value || '')}
                  theme="vs-light"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    formatOnPaste: true,
                    formatOnType: true,
                    tabSize: 2
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowEditModal(false)}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                ❌ Cancel
              </button>
              <button
                onClick={handleEditTemplate}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  backgroundColor: '#f59e0b',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                💾 Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Modal */}
      {showViewModal && selectedTemplate && (
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
            borderRadius: '8px',
            padding: '24px',
            width: '100%',
            maxWidth: '800px',
            maxHeight: '90vh',
            overflow: 'auto'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '1.3rem', fontWeight: '600' }}>
              👁️ View Template: {selectedTemplate.name}
            </h3>
            
            {/* Template/Sample Info */}
            <div style={{ marginBottom: '20px', padding: '12px', backgroundColor: selectedTemplate.type === 'sample' ? '#f0fdf4' : '#f8fafc', borderRadius: '6px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.9rem' }}>
                <div><strong>{selectedTemplate.type === 'sample' ? 'File' : 'Template'} ID:</strong> {selectedTemplate.template_id}</div>
                <div><strong>Created:</strong> {new Date(selectedTemplate.created_at).toLocaleString()}</div>
                <div><strong>Type:</strong> {selectedTemplate.type === 'sample' ? '📦 Sample Profile' : '🌐 API Template'}</div>
                <div><strong>Profiles Count:</strong> {selectedTemplate.config?.length || selectedTemplate.profiles?.length || 0}</div>
                {selectedTemplate.filename && (
                  <div style={{ gridColumn: 'span 2' }}><strong>Filename:</strong> {selectedTemplate.filename}</div>
                )}
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '8px', display: 'block' }}>
                Profile Configuration (Read-Only):
              </label>
              <div style={{ 
                border: '1px solid #d1d5db', 
                borderRadius: '6px', 
                overflow: 'hidden',
                height: '400px'
              }}>
                <Editor
                  height="400px"
                  defaultLanguage="json"
                  value={JSON.stringify(selectedTemplate.config || selectedTemplate.profiles || [], null, 2)}
                  theme="vs-light"
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    fontSize: 13,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    folding: true,
                    bracketPairColorization: { enabled: true }
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => copyToClipboard(JSON.stringify(selectedTemplate.config || selectedTemplate.profiles || [], null, 2))}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  backgroundColor: '#8b5cf6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                📋 Copy JSON
              </button>
              <button
                onClick={() => setShowViewModal(false)}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                ✅ Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {showDeleteModal && selectedTemplate && (
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
            borderRadius: '8px',
            padding: '24px',
            width: '100%',
            maxWidth: '500px'
          }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.2rem', fontWeight: '600', color: '#dc2626' }}>
              🗑️ Delete Template
            </h3>
            
            <p style={{ marginBottom: '20px', color: '#4b5563' }}>
              Are you sure you want to delete the template <strong>"{selectedTemplate.name}"</strong>?
            </p>
            
            <div style={{ 
              padding: '12px', 
              backgroundColor: '#fef2f2', 
              border: '1px solid #fecaca', 
              borderRadius: '6px',
              marginBottom: '20px'
            }}>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#dc2626' }}>
                ⚠️ This action cannot be undone. The template and all its configuration will be permanently deleted.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowDeleteModal(false)}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                ❌ Cancel
              </button>
              <button
                onClick={handleDeleteTemplate}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  backgroundColor: '#dc2626',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                🗑️ Delete Template
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConfigTemplatesPage;