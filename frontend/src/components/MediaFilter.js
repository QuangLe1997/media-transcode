import React, { useState, useMemo } from 'react';

const MediaFilter = ({ outputs, onFilterChange }) => {
  const [activeFilters, setActiveFilters] = useState({
    device: [],     // high, medium, low
    content: [],    // main, thumbs 
    media: [],      // video, image, gif
    size: []        // s, m, l
  });

  // Analyze profile patterns to extract categories
  const profileAnalysis = useMemo(() => {
    if (!outputs) return { categories: {}, stats: {} };

    const categories = {
      device: new Set(),
      content: new Set(), 
      media: new Set(),
      size: new Set()
    };

    const stats = {
      device: {},
      content: {},
      media: {},
      size: {},
      total: 0
    };

    Object.keys(outputs).forEach(profileId => {
      stats.total++;
      
      // Analyze profile ID patterns
      // Examples: high_main_video, low_thumbs_video_s, medium_video_thumbs_image_m
      
      // Device quality (high, medium, low)
      if (profileId.includes('high_')) {
        categories.device.add('high');
        stats.device.high = (stats.device.high || 0) + 1;
      } else if (profileId.includes('medium_')) {
        categories.device.add('medium');
        stats.device.medium = (stats.device.medium || 0) + 1;
      } else if (profileId.includes('low_')) {
        categories.device.add('low');
        stats.device.low = (stats.device.low || 0) + 1;
      }
      
      // Content type (main, thumbs, video_thumbs)
      if (profileId.includes('main_')) {
        categories.content.add('main');
        stats.content.main = (stats.content.main || 0) + 1;
      } else if (profileId.includes('video_thumbs_')) {
        categories.content.add('video_thumbs');
        stats.content.video_thumbs = (stats.content.video_thumbs || 0) + 1;
      } else if (profileId.includes('thumbs_')) {
        categories.content.add('thumbs');
        stats.content.thumbs = (stats.content.thumbs || 0) + 1;
      }
      
      // Media type (video, image, gif)
      if (profileId.includes('video')) {
        categories.media.add('video');
        stats.media.video = (stats.media.video || 0) + 1;
      } else if (profileId.includes('image')) {
        categories.media.add('image');
        stats.media.image = (stats.media.image || 0) + 1;
      } else if (profileId.includes('gif')) {
        categories.media.add('gif');
        stats.media.gif = (stats.media.gif || 0) + 1;
      }
      
      // Size (s, m, l) - usually at the end
      if (profileId.endsWith('_s')) {
        categories.size.add('s');
        stats.size.s = (stats.size.s || 0) + 1;
      } else if (profileId.endsWith('_m')) {
        categories.size.add('m');
        stats.size.m = (stats.size.m || 0) + 1;
      } else if (profileId.endsWith('_l')) {
        categories.size.add('l');
        stats.size.l = (stats.size.l || 0) + 1;
      }
    });

    return {
      categories: {
        device: Array.from(categories.device).sort(),
        content: Array.from(categories.content).sort(),
        media: Array.from(categories.media).sort(),
        size: Array.from(categories.size).sort()
      },
      stats
    };
  }, [outputs]);

  // Filter outputs based on active filters
  const filteredOutputs = useMemo(() => {
    if (!outputs) return {};
    
    // If no filters are active, return all outputs
    const hasActiveFilters = Object.values(activeFilters).some(filters => filters.length > 0);
    if (!hasActiveFilters) return outputs;

    const filtered = {};
    
    Object.entries(outputs).forEach(([profileId, urlItems]) => {
      let matchesFilter = true;
      
      // Check device filter
      if (activeFilters.device.length > 0) {
        const matchesDevice = activeFilters.device.some(device => 
          profileId.includes(`${device}_`)
        );
        if (!matchesDevice) matchesFilter = false;
      }
      
      // Check content filter
      if (activeFilters.content.length > 0) {
        const matchesContent = activeFilters.content.some(content => {
          if (content === 'video_thumbs') {
            return profileId.includes('video_thumbs_');
          } else {
            return profileId.includes(`${content}_`);
          }
        });
        if (!matchesContent) matchesFilter = false;
      }
      
      // Check media filter
      if (activeFilters.media.length > 0) {
        const matchesMedia = activeFilters.media.some(media => 
          profileId.includes(media)
        );
        if (!matchesMedia) matchesFilter = false;
      }
      
      // Check size filter
      if (activeFilters.size.length > 0) {
        const matchesSize = activeFilters.size.some(size => 
          profileId.endsWith(`_${size}`)
        );
        if (!matchesSize) matchesFilter = false;
      }
      
      if (matchesFilter) {
        filtered[profileId] = urlItems;
      }
    });
    
    return filtered;
  }, [outputs, activeFilters]);

  // Update filters and notify parent
  const toggleFilter = (category, value) => {
    const newFilters = { ...activeFilters };
    const categoryFilters = [...newFilters[category]];
    
    if (categoryFilters.includes(value)) {
      newFilters[category] = categoryFilters.filter(item => item !== value);
    } else {
      newFilters[category] = [...categoryFilters, value];
    }
    
    setActiveFilters(newFilters);
    // Calculate new filtered outputs immediately
    const hasActiveFilters = Object.values(newFilters).some(filters => filters.length > 0);
    if (!hasActiveFilters) {
      onFilterChange(null); // Return all outputs
      return;
    }

    const filtered = {};
    Object.entries(outputs).forEach(([profileId, urlItems]) => {
      let matchesFilter = true;
      
      // Check device filter
      if (newFilters.device.length > 0) {
        const matchesDevice = newFilters.device.some(device => 
          profileId.includes(`${device}_`)
        );
        if (!matchesDevice) matchesFilter = false;
      }
      
      // Check content filter
      if (newFilters.content.length > 0) {
        const matchesContent = newFilters.content.some(content => {
          if (content === 'video_thumbs') {
            return profileId.includes('video_thumbs_');
          } else {
            return profileId.includes(`${content}_`);
          }
        });
        if (!matchesContent) matchesFilter = false;
      }
      
      // Check media filter
      if (newFilters.media.length > 0) {
        const matchesMedia = newFilters.media.some(media => 
          profileId.includes(media)
        );
        if (!matchesMedia) matchesFilter = false;
      }
      
      // Check size filter
      if (newFilters.size.length > 0) {
        const matchesSize = newFilters.size.some(size => 
          profileId.endsWith(`_${size}`)
        );
        if (!matchesSize) matchesFilter = false;
      }
      
      if (matchesFilter) {
        filtered[profileId] = urlItems;
      }
    });
    
    onFilterChange(filtered);
  };

  // Clear all filters
  const clearAllFilters = () => {
    setActiveFilters({
      device: [],
      content: [],
      media: [],
      size: []
    });
    onFilterChange(outputs);
  };

  // Get filter button style
  const getFilterButtonStyle = (category, value, isActive) => ({
    padding: '6px 12px',
    margin: '4px',
    border: isActive ? '2px solid #4299e1' : '1px solid #e2e8f0',
    borderRadius: '20px',
    background: isActive ? '#4299e1' : 'white',
    color: isActive ? 'white' : '#4a5568',
    fontSize: '0.8rem',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    textTransform: 'capitalize'
  });

  // Get category icon
  const getCategoryIcon = (category) => {
    const icons = {
      device: '📱',
      content: '🎬',
      media: '🎨',
      size: '📏'
    };
    return icons[category] || '📂';
  };

  // Get value icon
  const getValueIcon = (category, value) => {
    const icons = {
      device: {
        high: '🔥',
        medium: '⚡',
        low: '💡'
      },
      content: {
        main: '🎬',
        thumbs: '🖼️',
        video_thumbs: '🎞️'
      },
      media: {
        video: '🎥',
        image: '🖼️',
        gif: '🎞️'
      },
      size: {
        s: '📱',
        m: '💻',
        l: '🖥️'
      }
    };
    return icons[category]?.[value] || '📄';
  };

  // Get active filter count
  const activeFilterCount = Object.values(activeFilters).reduce((total, filters) => total + filters.length, 0);
  const filteredCount = Object.keys(filteredOutputs).length;
  const totalCount = Object.keys(outputs || {}).length;

  return (
    <div style={{
      background: 'white',
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      padding: '16px',
      marginBottom: '16px'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '16px'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <h3 style={{
            margin: 0,
            fontSize: '1.1rem',
            color: '#2d3748',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            🔍 Media Filter
          </h3>
          <div style={{
            background: filteredCount === totalCount ? '#e6fffa' : '#fff5f5',
            color: filteredCount === totalCount ? '#2d7a6a' : '#c53030',
            padding: '4px 8px',
            borderRadius: '12px',
            fontSize: '0.75rem',
            fontWeight: '600'
          }}>
            {filteredCount}/{totalCount} files
          </div>
        </div>
        
        {activeFilterCount > 0 && (
          <button
            onClick={clearAllFilters}
            style={{
              background: '#f56565',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 12px',
              fontSize: '0.8rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => {
              e.target.style.background = '#e53e3e';
            }}
            onMouseLeave={(e) => {
              e.target.style.background = '#f56565';
            }}
          >
            🗑️ Clear All ({activeFilterCount})
          </button>
        )}
      </div>

      {/* Filter Categories */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '16px'
      }}>
        {Object.entries(profileAnalysis.categories).map(([category, values]) => {
          if (values.length === 0) return null;
          
          return (
            <div key={category} style={{
              background: '#f8f9fa',
              border: '1px solid #e9ecef',
              borderRadius: '6px',
              padding: '12px'
            }}>
              <div style={{
                fontSize: '0.9rem',
                fontWeight: '600',
                color: '#495057',
                marginBottom: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                textTransform: 'capitalize'
              }}>
                {getCategoryIcon(category)} {category}
              </div>
              
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '4px'
              }}>
                {values.map(value => {
                  const isActive = activeFilters[category].includes(value);
                  const count = profileAnalysis.stats[category][value] || 0;
                  
                  return (
                    <button
                      key={value}
                      onClick={() => toggleFilter(category, value)}
                      style={getFilterButtonStyle(category, value, isActive)}
                      onMouseEnter={(e) => {
                        if (!isActive) {
                          e.target.style.background = '#f7fafc';
                          e.target.style.borderColor = '#cbd5e0';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) {
                          e.target.style.background = 'white';
                          e.target.style.borderColor = '#e2e8f0';
                        }
                      }}
                    >
                      {getValueIcon(category, value)}
                      <span>{value}</span>
                      <span style={{
                        background: isActive ? 'rgba(255,255,255,0.2)' : '#e2e8f0',
                        color: isActive ? 'white' : '#4a5568',
                        padding: '2px 6px',
                        borderRadius: '10px',
                        fontSize: '0.7rem',
                        fontWeight: '600',
                        minWidth: '18px',
                        textAlign: 'center'
                      }}>
                        {count}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Filter Presets */}
      <div style={{
        marginTop: '16px',
        paddingTop: '12px',
        borderTop: '1px solid #e2e8f0'
      }}>
        <div style={{
          fontSize: '0.85rem',
          fontWeight: '600',
          color: '#495057',
          marginBottom: '8px'
        }}>
          🚀 Quick Filters:
        </div>
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px'
        }}>
          <button
            onClick={() => {
              const newFilters = {
                device: [],
                content: ['main'],
                media: ['video'],
                size: []
              };
              setActiveFilters(newFilters);
              // Apply filter immediately
              const filtered = {};
              Object.entries(outputs).forEach(([profileId, urlItems]) => {
                if (profileId.includes('main_') && profileId.includes('video')) {
                  filtered[profileId] = urlItems;
                }
              });
              onFilterChange(filtered);
            }}
            style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            🎬 Main Videos
          </button>
          
          <button
            onClick={() => {
              const newFilters = {
                device: [],
                content: ['thumbs'],
                media: [],
                size: []
              };
              setActiveFilters(newFilters);
              const filtered = {};
              Object.entries(outputs).forEach(([profileId, urlItems]) => {
                if (profileId.includes('thumbs_') && !profileId.includes('video_thumbs_')) {
                  filtered[profileId] = urlItems;
                }
              });
              onFilterChange(filtered);
            }}
            style={{
              background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            🖼️ Thumbnails
          </button>
          
          <button
            onClick={() => {
              const newFilters = {
                device: [],
                content: ['video_thumbs'],
                media: [],
                size: []
              };
              setActiveFilters(newFilters);
              const filtered = {};
              Object.entries(outputs).forEach(([profileId, urlItems]) => {
                if (profileId.includes('video_thumbs_')) {
                  filtered[profileId] = urlItems;
                }
              });
              onFilterChange(filtered);
            }}
            style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            🎞️ Video Thumbs
          </button>
          
          <button
            onClick={() => {
              const newFilters = {
                device: ['high'],
                content: [],
                media: [],
                size: []
              };
              setActiveFilters(newFilters);
              const filtered = {};
              Object.entries(outputs).forEach(([profileId, urlItems]) => {
                if (profileId.includes('high_')) {
                  filtered[profileId] = urlItems;
                }
              });
              onFilterChange(filtered);
            }}
            style={{
              background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            🔥 High Quality
          </button>
          
          <button
            onClick={() => {
              const newFilters = {
                device: [],
                content: [],
                media: ['gif'],
                size: []
              };
              setActiveFilters(newFilters);
              const filtered = {};
              Object.entries(outputs).forEach(([profileId, urlItems]) => {
                if (profileId.includes('gif')) {
                  filtered[profileId] = urlItems;
                }
              });
              onFilterChange(filtered);
            }}
            style={{
              background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            🎞️ GIF Files
          </button>
          
          <button
            onClick={() => {
              const newFilters = {
                device: [],
                content: [],
                media: [],
                size: ['s']
              };
              setActiveFilters(newFilters);
              const filtered = {};
              Object.entries(outputs).forEach(([profileId, urlItems]) => {
                if (profileId.endsWith('_s')) {
                  filtered[profileId] = urlItems;
                }
              });
              onFilterChange(filtered);
            }}
            style={{
              background: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
              color: '#2d3748',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            📱 Small Size
          </button>
        </div>
      </div>
    </div>
  );
};

export default MediaFilter;