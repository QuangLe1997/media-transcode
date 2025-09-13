import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../api';

const Results = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [dateFilter, setDateFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  
  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(20);
  
  // Selection states
  const [selectedTasks, setSelectedTasks] = useState([]);
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showClearAllModal, setShowClearAllModal] = useState(false);
  const [deleteOptions, setDeleteOptions] = useState({
    deleteMedia: true,
    deleteFaces: true
  });

  useEffect(() => {
    loadTasks();
    setCurrentPage(1); // Reset pagination when filters change
  }, [filter, dateFilter, startDate, endDate]);

  useEffect(() => {
    let interval;
    if (autoRefresh) {
      interval = setInterval(() => {
        loadTasks();
      }, 5000); // Refresh every 5 seconds
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, filter]);

  const loadTasks = async () => {
    try {
      const status = filter === 'all' ? null : filter;
      const data = await apiService.getTasks(status, 500); // Increase limit for better filtering
      setTasks(data.tasks || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load tasks:', err);
      let errorMessage = 'Failed to load tasks';
      
      if (err.response) {
        const status = err.response.status;
        const detail = err.response?.data?.detail || err.response?.data?.message;
        
        if (status === 404) {
          errorMessage = '📭 No tasks found or API endpoint not available.';
        } else if (status === 500) {
          errorMessage = '🔧 Server error while loading tasks. Please try again.';
        } else if (status === 403) {
          errorMessage = '🔒 Access denied. Please check your permissions.';
        } else {
          errorMessage = `❌ Failed to load tasks: ${detail || `Server error (${status})`}`;
        }
      } else if (err.request) {
        errorMessage = '🌐 Network error. Please check your connection and try again.';
      } else {
        errorMessage = `❌ ${err.message || 'Unexpected error occurred'}`;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const deleteTask = async (taskId) => {
    if (!window.confirm('Are you sure you want to delete this task? This will permanently delete all files and cannot be undone.')) return;
    
    try {
      const response = await apiService.deleteTask(taskId);
      alert(`Task deleted: ${response.deleted_files.length} files removed from S3`);
      setTasks(prev => prev.filter(task => task.task_id !== taskId));
    } catch (err) {
      console.error('Failed to delete task:', err);
      let errorMessage = 'Failed to delete task';
      
      if (err.response) {
        const status = err.response.status;
        const detail = err.response?.data?.detail || err.response?.data?.message;
        
        if (status === 404) {
          errorMessage = 'Task not found or already deleted.';
        } else if (status === 403) {
          errorMessage = 'Access denied. You do not have permission to delete this task.';
        } else {
          errorMessage = detail || `Server error (${status})`;
        }
      } else if (err.request) {
        errorMessage = 'Network error. Please check your connection.';
      } else {
        errorMessage = err.message || 'Unexpected error occurred';
      }
      
      alert('❌ ' + errorMessage);
    }
  };

  const handleSelectTask = (taskId) => {
    setSelectedTasks(prev => {
      if (prev.includes(taskId)) {
        return prev.filter(id => id !== taskId);
      }
      return [...prev, taskId];
    });
  };

  const handleSelectAll = () => {
    const currentPageTasks = getPaginatedTasks();
    if (selectedTasks.length === currentPageTasks.length) {
      // Deselect all on current page
      const currentIds = currentPageTasks.map(t => t.task_id);
      setSelectedTasks(prev => prev.filter(id => !currentIds.includes(id)));
    } else {
      // Select all on current page
      const newSelections = currentPageTasks.map(t => t.task_id);
      setSelectedTasks(prev => [...new Set([...prev, ...newSelections])]);
    }
  };

  const handleBulkDelete = async () => {
    setShowDeleteModal(false);
    
    if (selectedTasks.length === 0) {
      alert('No tasks selected');
      return;
    }

    const confirmMsg = `Are you sure you want to delete ${selectedTasks.length} task(s)?` +
      (deleteOptions.deleteMedia ? '\n- Media files will be deleted from S3' : '') +
      (deleteOptions.deleteFaces ? '\n- Face detection results will be deleted from S3' : '') +
      '\n\nThis action cannot be undone.';
      
    if (!window.confirm(confirmMsg)) return;

    let successCount = 0;
    let failedCount = 0;
    const errors = [];

    for (const taskId of selectedTasks) {
      try {
        await apiService.deleteTask(taskId, deleteOptions.deleteMedia, deleteOptions.deleteFaces);
        successCount++;
      } catch (err) {
        failedCount++;
        errors.push(`${taskId}: ${err.message || 'Failed'}`);
      }
    }

    // Update task list
    setTasks(prev => prev.filter(task => !selectedTasks.includes(task.task_id)));
    setSelectedTasks([]);
    setIsSelectionMode(false);

    // Show results
    let message = `Deleted ${successCount} task(s) successfully.`;
    if (failedCount > 0) {
      message += `\n\n${failedCount} task(s) failed to delete:\n${errors.join('\n')}`;
    }
    alert(message);
  };

  const handleClearAll = async () => {
    setShowClearAllModal(false);
    
    if (tasks.length === 0) {
      alert('No tasks to delete');
      return;
    }

    const confirmMsg = `Are you sure you want to delete ALL ${tasks.length} task(s)?` +
      (deleteOptions.deleteMedia ? '\n- All media files will be deleted from S3' : '') +
      (deleteOptions.deleteFaces ? '\n- All face detection results will be deleted from S3' : '') +
      '\n\n⚠️ This will delete EVERYTHING and cannot be undone!';
      
    if (!window.confirm(confirmMsg)) return;

    let successCount = 0;
    let failedCount = 0;
    const errors = [];

    for (const task of tasks) {
      try {
        await apiService.deleteTask(task.task_id, deleteOptions.deleteMedia, deleteOptions.deleteFaces);
        successCount++;
      } catch (err) {
        failedCount++;
        errors.push(`${task.task_id}: ${err.message || 'Failed'}`);
      }
    }

    // Clear task list
    setTasks([]);
    setSelectedTasks([]);
    setIsSelectionMode(false);

    // Show results
    let message = `Deleted ${successCount} task(s) successfully.`;
    if (failedCount > 0) {
      message += `\n\n${failedCount} task(s) failed to delete:\n${errors.join('\n')}`;
    }
    alert(message);
  };

  const retryTask = async (taskId) => {
    if (!window.confirm('Are you sure you want to retry this task? This will delete all existing outputs and restart processing.')) return;
    
    try {
      const response = await apiService.retryTask(taskId);
      alert(`Task retry initiated: ${response.published_profiles}/${response.total_profiles} profiles queued`);
      // Refresh the task list to show updated status
      loadTasks();
    } catch (err) {
      console.error('Failed to retry task:', err);
      let errorMessage = 'Failed to retry task';
      
      if (err.response) {
        const status = err.response.status;
        const detail = err.response?.data?.detail || err.response?.data?.message;
        
        if (status === 404) {
          errorMessage = 'Task not found.';
        } else if (status === 403) {
          errorMessage = 'Access denied. You do not have permission to retry this task.';
        } else {
          errorMessage = detail || `Server error (${status})`;
        }
      } else if (err.request) {
        errorMessage = 'Network error. Please check your connection.';
      } else {
        errorMessage = err.message || 'Unexpected error occurred';
      }
      
      alert('❌ ' + errorMessage);
    }
  };

  const downloadFile = (url, filename) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'download';
    a.click();
  };

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

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const TaskCard = ({ task, onRetry, onDelete, isSelected, onSelect, isSelectionMode }) => {
    const completedProfiles = task.completed_profiles || 0;
    const failedProfiles = task.failed_profiles || 0;
    const expectedProfiles = task.expected_profiles || 0;
    const progressPercentage = task.completion_percentage || 0;

    // Get media for preview - priority: main profile output > first output > source
    const getPreviewMedia = () => {
      if (task.outputs && Object.keys(task.outputs).length > 0) {
        // Try to find main profile first - match actual profile patterns
        const profileKeys = Object.keys(task.outputs);
        
        // Look for main profiles (not thumbs)
        const mainProfile = profileKeys.find(key => 
          key.includes('main') && 
          !key.includes('thumbs') && 
          !key.includes('thumb')
        );
        
        if (mainProfile) {
          const output = task.outputs[mainProfile][0];
          return typeof output === 'object' ? output.url : output;
        }
        
        // If no main profile, get first available output
        const firstProfile = Object.keys(task.outputs)[0];
        const firstOutput = task.outputs[firstProfile][0];
        return typeof firstOutput === 'object' ? firstOutput.url : firstOutput;
      }
      
      // If no outputs, use source URL
      return task.source_url;
    };

    const previewMedia = getPreviewMedia();

    return (
      <div className={`task-card ${task.status} ${isSelected ? 'selected' : ''}`}>
        {/* Selection Checkbox */}
        {isSelectionMode && (
          <div style={{
            position: 'absolute',
            top: '10px',
            left: '10px',
            zIndex: 10,
            background: 'rgba(255, 255, 255, 0.9)',
            borderRadius: '4px',
            padding: '2px'
          }}>
            <input
              type="checkbox"
              checked={isSelected}
              onChange={() => onSelect(task.task_id)}
              style={{ width: '18px', height: '18px', cursor: 'pointer' }}
            />
          </div>
        )}
        
        {/* Media Preview */}
        <div className="media-preview" style={{ position: 'relative' }}>
          {previewMedia ? (
            <>
              {getFileType(previewMedia) === 'video' ? (
                <video 
                  src={previewMedia} 
                  muted 
                  preload="metadata"
                  style={{ 
                    cursor: 'pointer', 
                    borderRadius: '12px 12px 0 0',
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover'
                  }}
                  onMouseOver={(e) => {
                    e.target.currentTime = 1;
                    e.target.play();
                  }}
                  onMouseOut={(e) => {
                    e.target.pause();
                    e.target.currentTime = 0;
                  }}
                  onClick={() => navigate(`/task/${task.task_id}`)}
                />
              ) : getFileType(previewMedia) === 'image' ? (
                <img 
                  src={previewMedia} 
                  alt="Preview"
                  style={{ 
                    cursor: 'pointer',
                    borderRadius: '12px 12px 0 0',
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover'
                  }}
                  onClick={() => navigate(`/task/${task.task_id}`)}
                />
              ) : (
                <div 
                  className="media-placeholder" 
                  onClick={() => navigate(`/task/${task.task_id}`)}
                  style={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    borderRadius: '12px 12px 0 0',
                    cursor: 'pointer'
                  }}
                >
                  <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📄</div>
                  <div style={{ fontSize: '0.9rem' }}>Media File</div>
                </div>
              )}
              
              {/* Status overlay */}
              <div style={{
                position: 'absolute',
                top: '8px',
                left: '8px',
                background: task.outputs ? 'rgba(72, 187, 120, 0.9)' : 'rgba(237, 137, 54, 0.9)',
                color: 'white',
                padding: '4px 8px',
                borderRadius: '12px',
                fontSize: '0.7rem',
                fontWeight: '600'
              }}>
                {task.outputs ? '📤 Output' : '📥 Source'}
              </div>
              
              <div className="media-type-badge">
                {getFileType(previewMedia).toUpperCase()}
              </div>
            </>
          ) : task.status === 'processing' ? (
            <div className="media-placeholder" style={{ height: '100%' }}>
              <div className="loading-spinner" style={{ width: '32px', height: '32px' }}></div>
              <div style={{ marginTop: '8px', color: 'white' }}>Processing...</div>
            </div>
          ) : (
            <div className="media-placeholder" style={{ height: '100%' }}>
              <div className="media-placeholder-icon">
                {task.status === 'failed' ? '❌' : '📭'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'white' }}>{task.status === 'failed' ? 'Failed' : 'No Output'}</div>
            </div>
          )}
          
          {task.outputs_count > 0 && (
            <div style={{
              position: 'absolute',
              bottom: '4px',
              right: '4px',
              background: 'rgba(102, 126, 234, 0.9)',
              color: 'white',
              padding: '2px 6px',
              borderRadius: '3px',
              fontSize: '0.6rem',
              fontWeight: '600'
            }}>
              {task.outputs_count} files
            </div>
          )}
        </div>

        {/* Card Content */}
        <div style={{ padding: '16px' }}>
          <div className="task-header" style={{ marginBottom: '12px' }}>
            <h3 style={{ fontSize: '0.95rem', margin: 0, fontWeight: '600', color: '#2d3748', lineHeight: '1.3' }}>
              {getFileName(task.source_url)}
            </h3>
            <span className={`task-status ${task.status}`} style={{ fontSize: '0.7rem' }}>
              {task.status}
            </span>
          </div>

          <div style={{ fontSize: '0.75rem', color: '#718096', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span>📅</span>
            <span>{formatDate(task.created_at)}</span>
          </div>

          {expectedProfiles > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '6px'
              }}>
                <span style={{ fontSize: '0.8rem', color: '#4a5568' }}>
                  {completedProfiles}/{expectedProfiles} profiles
                </span>
                <span style={{ fontSize: '0.8rem', fontWeight: '600', color: '#667eea' }}>
                  {progressPercentage}%
                </span>
              </div>
              <div className="progress-bar" style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px' }}>
                <div 
                  className="progress-fill" 
                  style={{ width: `${progressPercentage}%`, borderRadius: '3px' }}
                ></div>
              </div>
              {failedProfiles > 0 && (
                <div style={{ fontSize: '0.7rem', color: '#f56565', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span>⚠️</span>
                  <span>{failedProfiles} failed</span>
                </div>
              )}
            </div>
          )}

          {/* Face Detection Status */}
          {task.face_detection_status && (
            <div style={{ 
              marginBottom: '12px', 
              padding: '8px 12px',
              background: task.face_detection_status === 'completed' ? '#f0fff4' : 
                         task.face_detection_status === 'failed' ? '#fff5f5' : 
                         task.face_detection_status === 'processing' ? '#fffbf0' : '#f8f9fa',
              border: `1px solid ${
                task.face_detection_status === 'completed' ? '#c6f6d5' : 
                task.face_detection_status === 'failed' ? '#fed7d7' : 
                task.face_detection_status === 'processing' ? '#fed7aa' : '#e2e8f0'
              }`,
              borderRadius: '6px',
              fontSize: '0.75rem'
            }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '6px',
                color: task.face_detection_status === 'completed' ? '#276749' : 
                       task.face_detection_status === 'failed' ? '#c53030' : 
                       task.face_detection_status === 'processing' ? '#b7791f' : '#4a5568'
              }}>
                <span>
                  {task.face_detection_status === 'completed' ? '🤖✅' : 
                   task.face_detection_status === 'failed' ? '🤖❌' : 
                   task.face_detection_status === 'processing' ? '🤖⚙️' : '🤖⏳'}
                </span>
                <span style={{ fontWeight: '600' }}>
                  Face Detection: {task.face_detection_status}
                </span>
                {task.face_detection_status === 'completed' && 
                 task.face_detection_results && 
                 task.face_detection_results.faces && (
                  <span style={{ 
                    marginLeft: '4px', 
                    color: '#276749',
                    fontWeight: '500'
                  }}>
                    ({task.face_detection_results.faces.length} faces)
                  </span>
                )}
              </div>
            </div>
          )}

          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            borderTop: '1px solid #e2e8f0',
            paddingTop: '12px'
          }}>
            <div style={{ fontSize: '0.8rem', color: '#718096', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span>📊</span>
              <span>{task.profiles_count || 0} profiles</span>
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                className="btn btn-sm"
                onClick={() => navigate(`/task/${task.task_id}`)}
                style={{ 
                  fontSize: '0.7rem', 
                  padding: '6px 8px',
                  background: 'linear-gradient(45deg, #667eea, #764ba2)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                title="View Details"
              >
                👁️
              </button>
              <button
                onClick={() => onRetry(task.task_id)}
                style={{
                  fontSize: '0.7rem',
                  padding: '6px 8px',
                  background: 'linear-gradient(45deg, #f59e0b, #d97706)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                title="Retry Task"
              >
                🔄
              </button>
              <button
                onClick={() => onDelete(task.task_id)}
                style={{ 
                  fontSize: '0.7rem', 
                  padding: '6px 8px',
                  background: 'linear-gradient(45deg, #f56565, #e53e3e)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                title="Delete Task"
              >
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };


  if (loading) {
    return (
      <div className="card">
        <div className="loading">
          <div className="loading-spinner"></div>
          <h3>Loading tasks...</h3>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="error-message">
          <strong>Error:</strong> {error}
          <button 
            className="btn" 
            onClick={() => { setError(null); loadTasks(); }}
            style={{ marginLeft: '15px' }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Get paginated tasks
  const getPaginatedTasks = () => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredTasks.slice(startIndex, endIndex);
  };

  // Filter and sort tasks
  const filteredTasks = tasks.filter(task => {
    // Status filter
    if (filter !== 'all' && task.status !== filter) return false;
    
    // Date filter
    const taskDate = new Date(task.created_at);
    const now = new Date();
    
    if (dateFilter === 'today') {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (taskDate < today) return false;
    } else if (dateFilter === 'week') {
      const weekAgo = new Date(now - 7 * 24 * 60 * 60 * 1000);
      if (taskDate < weekAgo) return false;
    } else if (dateFilter === 'month') {
      const monthAgo = new Date(now - 30 * 24 * 60 * 60 * 1000);
      if (taskDate < monthAgo) return false;
    } else if (dateFilter === 'custom') {
      if (startDate && taskDate < new Date(startDate)) return false;
      if (endDate && taskDate > new Date(endDate + 'T23:59:59')) return false;
    }
    
    // Search filter
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      const sourceUrl = task.source_url?.toLowerCase() || '';
      const taskId = task.task_id?.toLowerCase() || '';
      const errorMessage = task.error_message?.toLowerCase() || '';
      
      if (!sourceUrl.includes(searchLower) && 
          !taskId.includes(searchLower) && 
          !errorMessage.includes(searchLower)) {
        return false;
      }
    }
    
    return true;
  }).sort((a, b) => {
    let aValue = a[sortBy];
    let bValue = b[sortBy];
    
    // Handle date sorting
    if (sortBy === 'created_at' || sortBy === 'updated_at') {
      aValue = new Date(aValue);
      bValue = new Date(bValue);
    }
    
    // Handle numeric sorting
    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return sortOrder === 'asc' ? aValue - bValue : bValue - aValue;
    }
    
    // Handle string sorting
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return sortOrder === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
    }
    
    // Handle date sorting
    if (aValue instanceof Date && bValue instanceof Date) {
      return sortOrder === 'asc' ? aValue - bValue : bValue - aValue;
    }
    
    return 0;
  });

  return (
    <div className="card">
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '16px',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <h2 style={{ margin: 0, color: '#2d3748', fontSize: '1.4rem' }}>📊 Transcode Results</h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <select
            className="form-control"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ width: 'auto', fontSize: '0.9rem', padding: '6px 8px' }}
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
          
          <label style={{ 
            display: 'flex', 
            alignItems: 'center', 
            cursor: 'pointer',
            fontSize: '0.8rem',
            whiteSpace: 'nowrap'
          }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              style={{ marginRight: '6px' }}
            />
            Auto Refresh
          </label>

          <button 
            className="btn" 
            onClick={loadTasks}
            style={{ fontSize: '0.9rem', padding: '6px 12px' }}
          >
            🔄 Refresh
          </button>

          <button
            className={`btn ${isSelectionMode ? 'btn-secondary' : ''}`}
            onClick={() => {
              setIsSelectionMode(!isSelectionMode);
              setSelectedTasks([]);
            }}
            style={{ fontSize: '0.9rem', padding: '6px 12px', marginLeft: '8px' }}
          >
            {isSelectionMode ? '✖️ Cancel' : '☑️ Select'}
          </button>

          {isSelectionMode && (
            <>
              <button
                className="btn"
                onClick={handleSelectAll}
                style={{ fontSize: '0.9rem', padding: '6px 12px' }}
              >
                {selectedTasks.length === getPaginatedTasks().length ? '⬜ Deselect All' : '☑️ Select All'}
              </button>

              {selectedTasks.length > 0 && (
                <button
                  className="btn btn-danger"
                  onClick={() => setShowDeleteModal(true)}
                  style={{ fontSize: '0.9rem', padding: '6px 12px' }}
                >
                  🗑️ Delete ({selectedTasks.length})
                </button>
              )}
            </>
          )}

          {tasks.length > 0 && (
            <button
              className="btn btn-danger"
              onClick={() => setShowClearAllModal(true)}
              style={{ fontSize: '0.9rem', padding: '6px 12px', marginLeft: 'auto' }}
            >
              🗑️ Clear All
            </button>
          )}
        </div>
      </div>

      {/* Advanced Filters */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
        gap: '12px', 
        marginBottom: '16px',
        padding: '12px',
        backgroundColor: '#f8f9fa',
        borderRadius: '6px'
      }}>
        {/* Date Filter */}
        <div>
          <label style={{ display: 'block', marginBottom: '4px', fontWeight: '600', fontSize: '0.8rem' }}>Date Range:</label>
          <select
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="form-control"
            style={{ width: '100%', padding: '6px 8px', fontSize: '0.9rem' }}
          >
            <option value="">All Time</option>
            <option value="today">Today</option>
            <option value="week">Last Week</option>
            <option value="month">Last Month</option>
            <option value="custom">Custom Range</option>
          </select>
        </div>

        {/* Custom Date Range */}
        {dateFilter === 'custom' && (
          <>
            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontWeight: '600', fontSize: '0.8rem' }}>Start Date:</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="form-control"
                style={{ width: '100%', padding: '6px 8px', fontSize: '0.9rem' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontWeight: '600', fontSize: '0.8rem' }}>End Date:</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="form-control"
                style={{ width: '100%', padding: '6px 8px', fontSize: '0.9rem' }}
              />
            </div>
          </>
        )}

        {/* Search */}
        <div>
          <label style={{ display: 'block', marginBottom: '4px', fontWeight: '600', fontSize: '0.8rem' }}>Search:</label>
          <input
            type="text"
            placeholder="Search by task ID, URL, or error..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-control"
            style={{ width: '100%', padding: '6px 8px', fontSize: '0.9rem' }}
          />
        </div>

        {/* Sort By */}
        <div>
          <label style={{ display: 'block', marginBottom: '4px', fontWeight: '600', fontSize: '0.8rem' }}>Sort By:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="form-control"
            style={{ width: '100%', padding: '6px 8px', fontSize: '0.9rem' }}
          >
            <option value="created_at">Created Date</option>
            <option value="updated_at">Updated Date</option>
            <option value="status">Status</option>
            <option value="completion_percentage">Progress</option>
          </select>
        </div>

        {/* Sort Order */}
        <div>
          <label style={{ display: 'block', marginBottom: '4px', fontWeight: '600', fontSize: '0.8rem' }}>Order:</label>
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
            className="form-control"
            style={{ width: '100%', padding: '6px 8px', fontSize: '0.9rem' }}
          >
            <option value="desc">Newest First</option>
            <option value="asc">Oldest First</option>
          </select>
        </div>
      </div>

      {/* Results Summary */}
      <div style={{ 
        marginBottom: '16px', 
        padding: '8px 12px', 
        backgroundColor: '#e9ecef', 
        borderRadius: '4px', 
        fontSize: '0.9rem',
        color: '#495057'
      }}>
        Showing {filteredTasks.length} of {tasks.length} tasks
      </div>

      {/* Quick Stats */}
      {tasks.length > 0 && (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', 
          gap: '8px', 
          marginBottom: '16px' 
        }}>
          {['completed', 'processing', 'failed', 'pending'].map(status => {
            const count = tasks.filter(t => t.status === status).length;
            const colors = {
              completed: '#48bb78',
              processing: '#4299e1', 
              failed: '#f56565',
              pending: '#ed8936'
            };
            return (
              <div key={status} style={{
                background: 'white',
                padding: '8px',
                borderRadius: '4px',
                textAlign: 'center',
                borderLeft: `3px solid ${colors[status]}`,
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
              }}>
                <div style={{ fontSize: '1.2rem', fontWeight: '700', color: colors[status] }}>
                  {count}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#666', textTransform: 'capitalize' }}>
                  {status}
                </div>
              </div>
            );
          })}
          
          {/* Face Detection Stats */}
          <div style={{
            background: 'white',
            padding: '8px',
            borderRadius: '4px',
            textAlign: 'center',
            borderLeft: '3px solid #8b5cf6',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
          }}>
            <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#8b5cf6' }}>
              {tasks.filter(t => t.face_detection_status === 'completed').length}
            </div>
            <div style={{ fontSize: '0.7rem', color: '#666' }}>
              🤖 Face Detection
            </div>
          </div>
        </div>
      )}

      {/* Selection Summary */}
      {isSelectionMode && selectedTasks.length > 0 && (
        <div style={{
          backgroundColor: '#e3f2fd',
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span style={{ fontWeight: '500', color: '#1565c0' }}>
            {selectedTasks.length} task(s) selected
          </span>
          <span style={{ fontSize: '0.9rem', color: '#666' }}>
            Showing {getPaginatedTasks().length} of {filteredTasks.length} tasks
          </span>
        </div>
      )}

      {filteredTasks.length === 0 ? (
        <div className="loading">
          <div style={{ fontSize: '3rem', marginBottom: '20px' }}>📁</div>
          <h3>No tasks found</h3>
          <p>{tasks.length === 0 ? 'Upload some files to get started!' : 'Try adjusting your filters'}</p>
        </div>
      ) : (
        <>
          <div className="tasks-grid">
            {getPaginatedTasks().map(task => (
              <TaskCard 
                key={task.task_id} 
                task={task} 
                onRetry={retryTask}
                onDelete={deleteTask}
                isSelected={selectedTasks.includes(task.task_id)}
                onSelect={handleSelectTask}
                isSelectionMode={isSelectionMode}
              />
            ))}
          </div>

          {/* Pagination Controls */}
          {filteredTasks.length > itemsPerPage && (
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '12px',
              marginTop: '24px',
              padding: '16px',
              backgroundColor: '#f8f9fa',
              borderRadius: '8px'
            }}>
              <button
                className="btn"
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                style={{ fontSize: '0.9rem', padding: '6px 12px' }}
              >
                ← Previous
              </button>

              <span style={{ fontSize: '0.9rem', color: '#4a5568' }}>
                Page {currentPage} of {Math.ceil(filteredTasks.length / itemsPerPage)}
              </span>

              <select
                className="form-control"
                value={itemsPerPage}
                onChange={(e) => {
                  setItemsPerPage(Number(e.target.value));
                  setCurrentPage(1);
                }}
                style={{ width: 'auto', fontSize: '0.9rem', padding: '6px 8px' }}
              >
                <option value={10}>10 per page</option>
                <option value={20}>20 per page</option>
                <option value={50}>50 per page</option>
                <option value={100}>100 per page</option>
              </select>

              <button
                className="btn"
                onClick={() => setCurrentPage(prev => Math.min(Math.ceil(filteredTasks.length / itemsPerPage), prev + 1))}
                disabled={currentPage === Math.ceil(filteredTasks.length / itemsPerPage)}
                style={{ fontSize: '0.9rem', padding: '6px 12px' }}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}

      {/* Delete Modal */}
      {showDeleteModal && (
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
        }} onClick={() => setShowDeleteModal(false)}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '450px',
            width: '90%',
            maxHeight: '80vh',
            overflowY: 'auto',
            boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)'
          }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginTop: 0, marginBottom: '16px' }}>Delete Options</h3>
            <p style={{ marginBottom: '16px', color: '#666' }}>
              You are about to delete {selectedTasks.length} task(s).
            </p>
            
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={deleteOptions.deleteMedia}
                  onChange={(e) => setDeleteOptions(prev => ({
                    ...prev,
                    deleteMedia: e.target.checked
                  }))}
                  style={{ marginRight: '8px' }}
                />
                Delete media files from S3
              </label>
              
              <label style={{ display: 'block', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={deleteOptions.deleteFaces}
                  onChange={(e) => setDeleteOptions(prev => ({
                    ...prev,
                    deleteFaces: e.target.checked
                  }))}
                  style={{ marginRight: '8px' }}
                />
                Delete face detection results from S3
              </label>
            </div>
            
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowDeleteModal(false)}
                style={{ fontSize: '0.9rem', padding: '8px 16px' }}
              >
                Cancel
              </button>
              <button
                className="btn btn-danger"
                onClick={handleBulkDelete}
                style={{ fontSize: '0.9rem', padding: '8px 16px' }}
              >
                Delete {selectedTasks.length} Task(s)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Clear All Modal */}
      {showClearAllModal && (
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
        }} onClick={() => setShowClearAllModal(false)}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '450px',
            width: '90%',
            maxHeight: '80vh',
            overflowY: 'auto',
            boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)',
            animation: 'modalSlideIn 0.2s ease-out'
          }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginTop: 0, marginBottom: '16px', color: '#dc2626' }}>
              ⚠️ Clear All Tasks
            </h3>
            <p style={{ marginBottom: '16px', color: '#666' }}>
              <strong>Warning:</strong> You are about to delete ALL {tasks.length} task(s) in the system.
            </p>
            <p style={{ marginBottom: '16px', color: '#dc2626', fontWeight: 'bold' }}>
              This action will permanently delete everything and cannot be undone!
            </p>
            
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={deleteOptions.deleteMedia}
                  onChange={(e) => setDeleteOptions(prev => ({
                    ...prev,
                    deleteMedia: e.target.checked
                  }))}
                  style={{ marginRight: '8px' }}
                />
                Delete all media files from S3
              </label>
              
              <label style={{ display: 'block', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={deleteOptions.deleteFaces}
                  onChange={(e) => setDeleteOptions(prev => ({
                    ...prev,
                    deleteFaces: e.target.checked
                  }))}
                  style={{ marginRight: '8px' }}
                />
                Delete all face detection results from S3
              </label>
            </div>
            
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowClearAllModal(false)}
                style={{ fontSize: '0.9rem', padding: '8px 16px' }}
              >
                Cancel
              </button>
              <button
                className="btn btn-danger"
                onClick={handleClearAll}
                style={{ fontSize: '0.9rem', padding: '8px 16px' }}
              >
                Clear All Tasks
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default Results;