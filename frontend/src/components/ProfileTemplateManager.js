import React, { useState, useEffect } from 'react';
import api from '../api';
import Editor from '@monaco-editor/react';
import UniversalTemplateCreator from './UniversalTemplateCreator';

const ProfileTemplateManager = ({ onProfilesLoad, showAsModal = false, onClose = null }) => {
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  
  // Template editing state
  const [editMode, setEditMode] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [templateName, setTemplateName] = useState('');
  const [templateProfiles, setTemplateProfiles] = useState('[]');
  
  // Create new template state
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showUniversalCreator, setShowUniversalCreator] = useState(false);
  const [universalTemplates, setUniversalTemplates] = useState([]);
  const [newTemplateName, setNewTemplateName] = useState('');
  const [newTemplateProfiles, setNewTemplateProfiles] = useState(JSON.stringify([
    {
      "id_profile": "example_profile",
      "output_type": "video",
      "input_type": "video",
      "video_config": {
        "codec": "libx264",
        "max_width": 1280,
        "max_height": 720,
        "crf": 23,
        "preset": "medium"
      }
    }
  ], null, 2));

  // Load templates on mount
  useEffect(() => {
    loadTemplates();
    loadUniversalTemplates();
  }, []);

  const loadUniversalTemplates = () => {
    try {
      const saved = localStorage.getItem('universal-templates');
      if (saved) {
        setUniversalTemplates(JSON.parse(saved));
      }
    } catch (error) {
      console.error('Failed to load universal templates:', error);
    }
  };

  const handleUniversalTemplateCreated = (newTemplate) => {
    setUniversalTemplates([...universalTemplates, newTemplate]);
    // Also reload legacy templates in case it was saved to API
    loadTemplates();
  };

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const response = await api.get('/config-templates');
      setTemplates(response.data.templates || []);
    } catch (error) {
      console.error('Error loading templates:', error);
      setMessage({ type: 'error', text: 'Failed to load templates' });
    } finally {
      setLoading(false);
    }
  };

  const loadTemplateDetail = async (templateId) => {
    try {
      const response = await api.get(`/config-templates/${templateId}`);
      setSelectedTemplate(response.data);
      setTemplateProfiles(JSON.stringify(response.data.config, null, 2));
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to load template detail' });
    }
  };

  const createTemplate = async () => {
    if (!newTemplateName.trim()) {
      setMessage({ type: 'error', text: 'Please enter a template name' });
      return;
    }

    try {
      const profiles = JSON.parse(newTemplateProfiles);
      const response = await api.post('/config-templates', {
        name: newTemplateName,
        description: null,
        profiles: profiles,
        s3_output_config: null,
        face_detection_config: null
      });
      
      setTemplates([...templates, response.data]);
      setNewTemplateName('');
      setShowCreateDialog(false);
      setMessage({ type: 'success', text: 'Template created successfully!' });
      
      // Auto-select the new template
      loadTemplateDetail(response.data.template_id);
    } catch (error) {
      if (error.message.includes('JSON')) {
        setMessage({ type: 'error', text: 'Invalid JSON format' });
      } else {
        setMessage({ type: 'error', text: 'Failed to create template' });
      }
    }
  };

  const updateTemplate = async () => {
    if (!editingTemplate || !templateName.trim()) {
      setMessage({ type: 'error', text: 'Template name is required' });
      return;
    }

    try {
      const profiles = JSON.parse(templateProfiles);
      const response = await api.put(`/config-templates/${editingTemplate.template_id}`, {
        name: templateName,
        description: editingTemplate.description,
        profiles: profiles,
        s3_output_config: editingTemplate.s3_output_config,
        face_detection_config: editingTemplate.face_detection_config
      });
      
      // Update templates list
      setTemplates(templates.map(t => 
        t.template_id === editingTemplate.template_id ? response.data : t
      ));
      
      setSelectedTemplate(response.data);
      setEditMode(false);
      setEditingTemplate(null);
      setMessage({ type: 'success', text: 'Template updated successfully!' });
    } catch (error) {
      if (error.message.includes('JSON')) {
        setMessage({ type: 'error', text: 'Invalid JSON format' });
      } else {
        setMessage({ type: 'error', text: 'Failed to update template' });
      }
    }
  };

  const deleteTemplate = async (templateId) => {
    if (!window.confirm('Are you sure you want to delete this template?')) {
      return;
    }

    try {
      await api.delete(`/config-templates/${templateId}`);
      setTemplates(templates.filter(t => t.template_id !== templateId));
      
      if (selectedTemplate?.template_id === templateId) {
        setSelectedTemplate(null);
        setTemplateProfiles('[]');
      }
      
      setMessage({ type: 'success', text: 'Template deleted successfully' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to delete template' });
    }
  };

  const startEdit = () => {
    if (!selectedTemplate) return;
    
    setEditMode(true);
    setEditingTemplate(selectedTemplate);
    setTemplateName(selectedTemplate.name);
    setTemplateProfiles(JSON.stringify(selectedTemplate.config, null, 2));
  };

  const cancelEdit = () => {
    setEditMode(false);
    setEditingTemplate(null);
    setTemplateName('');
    if (selectedTemplate) {
      setTemplateProfiles(JSON.stringify(selectedTemplate.config, null, 2));
    }
  };

  const useProfiles = () => {
    if (!selectedTemplate) {
      setMessage({ type: 'error', text: 'No template selected' });
      return;
    }

    const profilesJson = JSON.stringify(selectedTemplate.config, null, 2);
    
    if (onProfilesLoad) {
      onProfilesLoad(profilesJson);
    }
    
    setMessage({ 
      type: 'success', 
      text: `Loaded ${selectedTemplate.config.length} profiles from "${selectedTemplate.name}"` 
    });

    if (showAsModal && onClose) {
      onClose();
    }
  };

  const formatJson = (jsonString) => {
    try {
      const parsed = JSON.parse(jsonString);
      return JSON.stringify(parsed, null, 2);
    } catch (error) {
      return jsonString;
    }
  };

  const containerStyle = showAsModal ? {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000
  } : {};

  const contentStyle = showAsModal ? {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '24px',
    maxWidth: '90vw',
    maxHeight: '90vh',
    overflow: 'auto',
    position: 'relative',
    width: '1000px'
  } : {};

  return (
    <div style={containerStyle}>
      <div style={contentStyle}>
        {showAsModal && (
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
              fontSize: '18px'
            }}
          >
            ×
          </button>
        )}

        <div style={{ 
          maxWidth: showAsModal ? '100%' : '1200px', 
          margin: '0 auto', 
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
        }}>
          <h2 style={{ 
            marginBottom: '24px', 
            color: '#374151',
            borderBottom: '2px solid #f3f4f6',
            paddingBottom: '12px'
          }}>
            📋 Profile Template Manager
          </h2>

          {message && (
            <div 
              style={{
                padding: '12px 16px',
                borderRadius: '6px',
                marginBottom: '20px',
                backgroundColor: message.type === 'error' ? '#fee2e2' : '#d1fae5',
                color: message.type === 'error' ? '#dc2626' : '#065f46',
                border: `1px solid ${message.type === 'error' ? '#fecaca' : '#a7f3d0'}`
              }}
            >
              {message.text}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '350px 1fr', gap: '24px' }}>
            {/* Left Column - Templates List */}
            <div>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '16px'
              }}>
                <h3 style={{ margin: 0, color: '#374151' }}>📁 Templates</h3>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => setShowUniversalCreator(true)}
                    style={{
                      padding: '6px 12px',
                      fontSize: '0.8rem',
                      backgroundColor: '#007bff',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontWeight: '600'
                    }}
                  >
                    🎨 New Universal
                  </button>
                  <button
                    onClick={() => setShowCreateDialog(true)}
                    style={{
                      padding: '6px 12px',
                      fontSize: '0.8rem',
                      backgroundColor: '#10b981',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontWeight: '600'
                    }}
                  >
                    + Legacy Template
                  </button>
                </div>
              </div>

              {loading ? (
                <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280' }}>
                  Loading templates...
                </div>
              ) : (
                <div style={{ 
                  maxHeight: '500px', 
                  overflowY: 'auto',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px'
                }}>
                  {templates.length === 0 ? (
                    <div style={{ 
                      padding: '20px', 
                      textAlign: 'center', 
                      color: '#9ca3af' 
                    }}>
                      No templates found. Create one!
                    </div>
                  ) : (
                    <>
                      {/* Universal Templates (v2) */}
                      {universalTemplates.map((template, index) => (
                        <button
                          key={`universal-${template.id}`}
                          onClick={() => {
                            // Convert universal template to legacy format for display
                            const legacyFormat = {
                              template_id: template.id,
                              name: `${template.name} (v2)`,
                              config: template.profiles,
                              created_at: template.created_at,
                              updated_at: template.created_at,
                              format_version: 'v2'
                            };
                            setSelectedTemplate(legacyFormat);
                            setTemplateProfiles(JSON.stringify(template.profiles, null, 2));
                          }}
                          style={{
                            width: '100%',
                            padding: '12px',
                            fontSize: '0.85rem',
                            textAlign: 'left',
                            border: 'none',
                            borderBottom: '1px solid #f3f4f6',
                            backgroundColor: selectedTemplate?.template_id === template.id ? '#eff6ff' : '#f8fafc',
                            color: selectedTemplate?.template_id === template.id ? '#1e40af' : '#475569',
                            cursor: 'pointer',
                            transition: 'background-color 0.2s'
                          }}
                          onMouseOver={(e) => {
                            if (selectedTemplate?.template_id !== template.id) {
                              e.target.style.backgroundColor = '#f1f5f9';
                            }
                          }}
                          onMouseOut={(e) => {
                            if (selectedTemplate?.template_id !== template.id) {
                              e.target.style.backgroundColor = '#f8fafc';
                            }
                          }}
                        >
                          <div style={{ fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontSize: '0.7rem', background: '#007bff', color: 'white', padding: '2px 6px', borderRadius: '3px' }}>v2</span>
                            {template.name}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
                            {template.profiles?.length || 0} profiles • Universal format
                          </div>
                        </button>
                      ))}
                      
                      {/* Legacy Templates (v1) */}
                      {templates.map((template, index) => (
                        <button
                          key={template.template_id}
                          onClick={() => loadTemplateDetail(template.template_id)}
                          style={{
                            width: '100%',
                            padding: '12px',
                            fontSize: '0.85rem',
                            textAlign: 'left',
                            border: 'none',
                            borderBottom: index < templates.length - 1 ? '1px solid #f3f4f6' : 'none',
                            backgroundColor: selectedTemplate?.template_id === template.template_id ? '#f0fdf4' : 'white',
                            color: selectedTemplate?.template_id === template.template_id ? '#065f46' : '#374151',
                            cursor: 'pointer',
                            transition: 'background-color 0.2s'
                          }}
                          onMouseOver={(e) => {
                            if (selectedTemplate?.template_id !== template.template_id) {
                              e.target.style.backgroundColor = '#f9fafb';
                            }
                          }}
                          onMouseOut={(e) => {
                            if (selectedTemplate?.template_id !== template.template_id) {
                              e.target.style.backgroundColor = 'white';
                            }
                          }}
                        >
                          <div style={{ fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontSize: '0.7rem', background: '#10b981', color: 'white', padding: '2px 6px', borderRadius: '3px' }}>v1</span>
                            {template.name}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '4px' }}>
                            {template.config?.length || 0} profiles • Legacy format
                          </div>
                        </button>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Right Column - Template Detail */}
            <div>
              {selectedTemplate ? (
                <div>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    marginBottom: '16px'
                  }}>
                    <h3 style={{ margin: 0, color: '#374151' }}>
                      {editMode ? '✏️ Edit Template' : '📄 Template Detail'}
                    </h3>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      {!editMode ? (
                        <>
                          <button
                            onClick={useProfiles}
                            style={{
                              padding: '6px 12px',
                              fontSize: '0.8rem',
                              backgroundColor: '#10b981',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              cursor: 'pointer',
                              fontWeight: '600'
                            }}
                          >
                            🚀 Use Profiles
                          </button>
                          <button
                            onClick={startEdit}
                            style={{
                              padding: '6px 12px',
                              fontSize: '0.8rem',
                              backgroundColor: '#3b82f6',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              cursor: 'pointer'
                            }}
                          >
                            ✏️ Edit
                          </button>
                          <button
                            onClick={() => deleteTemplate(selectedTemplate.template_id)}
                            style={{
                              padding: '6px 12px',
                              fontSize: '0.8rem',
                              backgroundColor: '#ef4444',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              cursor: 'pointer'
                            }}
                          >
                            🗑️ Delete
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={updateTemplate}
                            style={{
                              padding: '6px 12px',
                              fontSize: '0.8rem',
                              backgroundColor: '#10b981',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              cursor: 'pointer',
                              fontWeight: '600'
                            }}
                          >
                            💾 Save
                          </button>
                          <button
                            onClick={cancelEdit}
                            style={{
                              padding: '6px 12px',
                              fontSize: '0.8rem',
                              backgroundColor: '#6b7280',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              cursor: 'pointer'
                            }}
                          >
                            Cancel
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {editMode && (
                    <div style={{ marginBottom: '12px' }}>
                      <label style={{ fontSize: '0.85rem', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                        Template Name:
                      </label>
                      <input
                        type="text"
                        value={templateName}
                        onChange={(e) => setTemplateName(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          fontSize: '0.9rem',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px'
                        }}
                      />
                    </div>
                  )}

                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      marginBottom: '8px'
                    }}>
                      <label style={{ fontSize: '0.85rem', fontWeight: '600' }}>
                        Profiles Configuration:
                      </label>
                      {editMode && (
                        <button
                          onClick={() => setTemplateProfiles(formatJson(templateProfiles))}
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
                      )}
                    </div>
                    
                    <div style={{ 
                      border: '1px solid #e5e7eb', 
                      borderRadius: '6px', 
                      overflow: 'hidden',
                      minHeight: '400px'
                    }}>
                      <Editor
                        height="400px"
                        defaultLanguage="json"
                        value={templateProfiles}
                        onChange={(value) => editMode && setTemplateProfiles(value || '')}
                        theme="vs-light"
                        options={{
                          readOnly: !editMode,
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

                  {!editMode && selectedTemplate && (
                    <div style={{ 
                      marginTop: '12px',
                      padding: '12px',
                      backgroundColor: '#f9fafb',
                      borderRadius: '6px',
                      border: '1px solid #e5e7eb',
                      fontSize: '0.8rem',
                      color: '#6b7280'
                    }}>
                      <div><strong>Template ID:</strong> {selectedTemplate.template_id}</div>
                      <div><strong>Created:</strong> {new Date(selectedTemplate.created_at).toLocaleString()}</div>
                      <div><strong>Updated:</strong> {new Date(selectedTemplate.updated_at).toLocaleString()}</div>
                      <div><strong>Profiles:</strong> {selectedTemplate.config.length}</div>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ 
                  textAlign: 'center', 
                  padding: '80px 40px',
                  color: '#9ca3af',
                  backgroundColor: '#f9fafb',
                  borderRadius: '6px',
                  border: '1px dashed #d1d5db'
                }}>
                  Select a template from the list to view details
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Create Template Dialog */}
        {showCreateDialog && (
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
            zIndex: 1001
          }}>
            <div style={{
              backgroundColor: 'white',
              borderRadius: '12px',
              padding: '24px',
              width: '800px',
              maxHeight: '80vh',
              overflow: 'auto'
            }}>
              <h3 style={{ marginBottom: '16px', color: '#374151' }}>
                ➕ Create New Template
              </h3>

              <div style={{ marginBottom: '12px' }}>
                <label style={{ fontSize: '0.85rem', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                  Template Name:
                </label>
                <input
                  type="text"
                  value={newTemplateName}
                  onChange={(e) => setNewTemplateName(e.target.value)}
                  placeholder="e.g., Mobile Video Profiles"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    fontSize: '0.9rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px'
                  }}
                />
              </div>

              <div style={{ marginBottom: '12px' }}>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  marginBottom: '8px'
                }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '600' }}>
                    Profiles Configuration:
                  </label>
                  <button
                    onClick={() => setNewTemplateProfiles(formatJson(newTemplateProfiles))}
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
                  border: '1px solid #e5e7eb', 
                  borderRadius: '6px', 
                  overflow: 'hidden',
                  minHeight: '300px'
                }}>
                  <Editor
                    height="300px"
                    defaultLanguage="json"
                    value={newTemplateProfiles}
                    onChange={(value) => setNewTemplateProfiles(value || '')}
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

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button
                  onClick={createTemplate}
                  style={{
                    padding: '8px 16px',
                    fontSize: '0.9rem',
                    backgroundColor: '#10b981',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontWeight: '600'
                  }}
                >
                  Create Template
                </button>
                <button
                  onClick={() => {
                    setShowCreateDialog(false);
                    setNewTemplateName('');
                  }}
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
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Universal Template Creator */}
        {showUniversalCreator && (
          <UniversalTemplateCreator
            onClose={() => setShowUniversalCreator(false)}
            onTemplateCreated={handleUniversalTemplateCreated}
          />
        )}
      </div>
      
      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default ProfileTemplateManager;