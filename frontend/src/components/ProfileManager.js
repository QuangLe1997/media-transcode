import React, { useState, useEffect } from 'react';
import api from '../api';
import Editor from '@monaco-editor/react';

const ProfileManager = ({ onProfilesLoad, showAsModal = false, onClose = null }) => {
  const [profiles, setProfiles] = useState({});
  const [features, setFeatures] = useState([]);
  const [selectedFeature, setSelectedFeature] = useState('');
  const [deviceTier, setDeviceTier] = useState('both');
  const [featureProfiles, setFeatureProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState('');
  const [profileDetail, setProfileDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  // Load all profiles on component mount
  useEffect(() => {
    const loadProfiles = async () => {
      setLoading(true);
      try {
        const response = await api.get('/profiles');
        setProfiles(response.data.profiles);
        setFeatures(response.data.features);
        setMessage({ 
          type: 'success', 
          text: `Loaded ${response.data.total_profiles} profiles across ${response.data.features.length} features` 
        });
      } catch (error) {
        console.error('Error loading profiles:', error);
        setMessage({ type: 'error', text: 'Failed to load profiles' });
      } finally {
        setLoading(false);
      }
    };
    loadProfiles();
  }, []);

  // Load feature profiles when feature changes
  useEffect(() => {
    if (selectedFeature) {
      loadFeatureProfiles();
    }
  }, [selectedFeature, deviceTier]);

  const loadFeatureProfiles = async () => {
    if (!selectedFeature) return;
    
    setLoading(true);
    try {
      const response = await api.get(`/profiles/${selectedFeature}?device_tier=${deviceTier}`);
      setFeatureProfiles(response.data.profiles);
      setSelectedProfile('');
      setProfileDetail(null);
    } catch (error) {
      console.error('Error loading feature profiles:', error);
      setMessage({ type: 'error', text: 'Failed to load feature profiles' });
    } finally {
      setLoading(false);
    }
  };

  // Load single profile detail
  const loadProfileDetail = async (profileId) => {
    if (!profileId) return;
    
    try {
      const response = await api.get(`/profiles/single/${profileId}`);
      setProfileDetail(response.data.profile);
      setSelectedProfile(profileId);
    } catch (error) {
      console.error('Error loading profile detail:', error);
      setMessage({ type: 'error', text: 'Failed to load profile detail' });
    }
  };

  // Generate profiles for selected feature
  const generateProfiles = () => {
    if (featureProfiles.length === 0) {
      setMessage({ type: 'error', text: 'No profiles available for selected feature' });
      return;
    }

    const profilesJson = JSON.stringify(featureProfiles, null, 2);
    
    if (onProfilesLoad) {
      onProfilesLoad(profilesJson);
    }
    
    setMessage({ 
      type: 'success', 
      text: `Generated ${featureProfiles.length} profiles for ${selectedFeature} (${deviceTier})` 
    });

    if (showAsModal && onClose) {
      onClose();
    }
  };

  // Get feature display info
  const getFeatureInfo = (feature) => {
    const featureMap = {
      'ai_face_swap_video': {
        name: '🎭 AI Face Swap - Video',
        desc: 'Video templates for face swap (preview, detail, AI processing)',
        icon: '🎬'
      },
      'ai_face_swap_image': {
        name: '🎭 AI Face Swap - Image', 
        desc: 'Image templates for face swap (thumbnails, detail, AI processing)',
        icon: '🖼️'
      },
      'popup_home_video': {
        name: '🏠 Home Popup - Video',
        desc: 'Full-screen popup videos (80% screen height)',
        icon: '📺'
      },
      'popup_home_image': {
        name: '🏠 Home Popup - Image',
        desc: 'Full-screen popup images (80% screen height)',
        icon: '🖼️'
      },
      'banner_promoted_video': {
        name: '📢 Banner Promoted - Video',
        desc: 'Promotional banner videos (1/3 screen height)',
        icon: '🎞️'
      },
      'banner_promoted_image': {
        name: '📢 Banner Promoted - Image',
        desc: 'Promotional banner images (1/3 screen height)',
        icon: '🎨'
      }
    };
    return featureMap[feature] || { name: feature, desc: 'Unknown feature', icon: '❓' };
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
    position: 'relative'
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
          maxWidth: showAsModal ? '800px' : '1200px', 
          margin: '0 auto', 
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
        }}>
          <h2 style={{ 
            marginBottom: '24px', 
            color: '#374151',
            borderBottom: '2px solid #f3f4f6',
            paddingBottom: '12px'
          }}>
            🔧 Profile Template Manager
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

          {loading && (
            <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280' }}>
              <div style={{ 
                display: 'inline-block', 
                width: '20px', 
                height: '20px', 
                border: '2px solid #e5e7eb',
                borderTop: '2px solid #3b82f6',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                marginRight: '8px'
              }}></div>
              Loading...
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {/* Left Column - Feature Selection */}
            <div>
              <h3 style={{ marginBottom: '16px', color: '#374151' }}>📋 Select Feature & Device Tier</h3>
              
              {/* Feature Selection */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '8px', display: 'block' }}>
                  Feature Type:
                </label>
                <select
                  value={selectedFeature}
                  onChange={(e) => setSelectedFeature(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    fontSize: '0.9rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    backgroundColor: 'white'
                  }}
                >
                  <option value="">Select a feature...</option>
                  {features.map(feature => {
                    const info = getFeatureInfo(feature);
                    return (
                      <option key={feature} value={feature}>
                        {info.icon} {info.name}
                      </option>
                    );
                  })}
                </select>
                
                {selectedFeature && (
                  <div style={{ 
                    marginTop: '8px', 
                    padding: '8px 12px',
                    backgroundColor: '#f9fafb',
                    borderRadius: '6px',
                    border: '1px solid #e5e7eb',
                    fontSize: '0.8rem',
                    color: '#6b7280'
                  }}>
                    {getFeatureInfo(selectedFeature).desc}
                  </div>
                )}
              </div>

              {/* Device Tier Selection */}
              {selectedFeature && (
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '8px', display: 'block' }}>
                    Device Tier:
                  </label>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {[
                      { value: 'both', label: '🔄 Both Tiers', desc: 'All profiles' },
                      { value: 'high', label: '📱 High-End', desc: 'Flagship devices' },
                      { value: 'low', label: '📞 Low-End', desc: 'Budget devices' }
                    ].map(tier => (
                      <button
                        key={tier.value}
                        onClick={() => setDeviceTier(tier.value)}
                        style={{
                          padding: '8px 12px',
                          fontSize: '0.8rem',
                          border: `2px solid ${deviceTier === tier.value ? '#10b981' : '#e5e7eb'}`,
                          borderRadius: '6px',
                          backgroundColor: deviceTier === tier.value ? '#ecfdf5' : 'white',
                          color: deviceTier === tier.value ? '#065f46' : '#6b7280',
                          cursor: 'pointer',
                          fontWeight: deviceTier === tier.value ? '600' : '400'
                        }}
                        title={tier.desc}
                      >
                        {tier.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Profiles List */}
              {featureProfiles.length > 0 && (
                <div>
                  <h4 style={{ marginBottom: '12px', color: '#374151' }}>
                    📄 Available Profiles ({featureProfiles.length})
                  </h4>
                  <div style={{ 
                    maxHeight: '300px', 
                    overflowY: 'auto',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px'
                  }}>
                    {featureProfiles.map((profile, index) => (
                      <button
                        key={profile.id_profile}
                        onClick={() => loadProfileDetail(profile.id_profile)}
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          fontSize: '0.8rem',
                          textAlign: 'left',
                          border: 'none',
                          borderBottom: index < featureProfiles.length - 1 ? '1px solid #f3f4f6' : 'none',
                          backgroundColor: selectedProfile === profile.id_profile ? '#f0fdf4' : 'white',
                          color: selectedProfile === profile.id_profile ? '#065f46' : '#374151',
                          cursor: 'pointer',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseOver={(e) => {
                          if (selectedProfile !== profile.id_profile) {
                            e.target.style.backgroundColor = '#f9fafb';
                          }
                        }}
                        onMouseOut={(e) => {
                          if (selectedProfile !== profile.id_profile) {
                            e.target.style.backgroundColor = 'white';
                          }
                        }}
                      >
                        <div style={{ fontWeight: '600' }}>{profile.id_profile}</div>
                        <div style={{ fontSize: '0.7rem', color: '#6b7280' }}>
                          {profile.output_type} • {profile.input_type || 'any input'}
                        </div>
                      </button>
                    ))}
                  </div>
                  
                  {/* Generate Button */}
                  <button
                    onClick={generateProfiles}
                    style={{
                      width: '100%',
                      marginTop: '16px',
                      padding: '12px 16px',
                      fontSize: '0.9rem',
                      fontWeight: '600',
                      backgroundColor: '#10b981',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      transition: 'background-color 0.2s'
                    }}
                    onMouseOver={(e) => e.target.style.backgroundColor = '#059669'}
                    onMouseOut={(e) => e.target.style.backgroundColor = '#10b981'}
                  >
                    🚀 Use These Profiles ({featureProfiles.length})
                  </button>
                </div>
              )}
            </div>

            {/* Right Column - Profile Detail */}
            <div>
              <h3 style={{ marginBottom: '16px', color: '#374151' }}>🔍 Profile Detail</h3>
              
              {profileDetail ? (
                <div>
                  <div style={{ 
                    marginBottom: '12px',
                    padding: '12px',
                    backgroundColor: '#f8fafc',
                    borderRadius: '6px',
                    border: '1px solid #e2e8f0'
                  }}>
                    <h4 style={{ margin: '0 0 8px 0', color: '#374151' }}>
                      {profileDetail.id_profile}
                    </h4>
                    <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                      <span style={{ 
                        display: 'inline-block',
                        padding: '2px 6px',
                        backgroundColor: '#ddd6fe',
                        borderRadius: '4px',
                        marginRight: '8px'
                      }}>
                        {profileDetail.output_type}
                      </span>
                      {profileDetail.input_type && (
                        <span style={{ 
                          display: 'inline-block',
                          padding: '2px 6px',
                          backgroundColor: '#fef3c7',
                          borderRadius: '4px'
                        }}>
                          input: {profileDetail.input_type}
                        </span>
                      )}
                    </div>
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
                      value={JSON.stringify(profileDetail, null, 2)}
                      theme="vs-light"
                      options={{
                        readOnly: true,
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
              ) : (
                <div style={{ 
                  textAlign: 'center', 
                  padding: '40px',
                  color: '#9ca3af',
                  backgroundColor: '#f9fafb',
                  borderRadius: '6px',
                  border: '1px dashed #d1d5db'
                }}>
                  Select a profile from the left to view details
                </div>
              )}
            </div>
          </div>
        </div>
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

export default ProfileManager;