import React from 'react';

const ConfirmModal = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title, 
  message, 
  confirmText = 'Confirm', 
  cancelText = 'Cancel',
  type = 'default', // 'default', 'danger', 'warning'
  showDeleteFilesOption = false,
  deleteFiles = false,
  onDeleteFilesChange = null
}) => {
  if (!isOpen) return null;

  const getTypeStyles = () => {
    switch (type) {
      case 'danger':
        return {
          confirmButton: {
            background: '#dc2626',
            hoverBackground: '#b91c1c'
          },
          titleColor: '#dc2626',
          icon: '⚠️'
        };
      case 'warning':
        return {
          confirmButton: {
            background: '#f59e0b',
            hoverBackground: '#d97706'
          },
          titleColor: '#f59e0b',
          icon: '⚠️'
        };
      default:
        return {
          confirmButton: {
            background: '#3b82f6',
            hoverBackground: '#2563eb'
          },
          titleColor: '#3b82f6',
          icon: '❓'
        };
    }
  };

  const styles = getTypeStyles();

  return (
    <>
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '20px'
      }} onClick={onClose}>
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '24px',
          maxWidth: '480px',
          width: '90%',
          maxHeight: '80vh',
          overflowY: 'auto',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
          animation: 'modalSlideIn 0.2s ease-out'
        }} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          marginBottom: '20px'
        }}>
          <span style={{ fontSize: '2rem' }}>{styles.icon}</span>
          <h2 style={{
            margin: 0,
            fontSize: '1.25rem',
            fontWeight: '600',
            color: styles.titleColor
          }}>
            {title}
          </h2>
        </div>

        {/* Message */}
        <div style={{
          fontSize: '1rem',
          color: '#374151',
          lineHeight: '1.6',
          marginBottom: showDeleteFilesOption ? '24px' : '32px'
        }}>
          {message}
        </div>

        {/* Delete Files Option */}
        {showDeleteFilesOption && (
          <div style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '24px'
          }}>
            <label style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              cursor: 'pointer',
              fontSize: '0.95rem'
            }}>
              <input
                type="checkbox"
                checked={deleteFiles}
                onChange={(e) => onDeleteFilesChange && onDeleteFilesChange(e.target.checked)}
                style={{
                  width: '18px',
                  height: '18px',
                  marginTop: '2px',
                  cursor: 'pointer'
                }}
              />
              <div>
                <div style={{
                  fontWeight: '500',
                  color: '#374151',
                  marginBottom: '4px'
                }}>
                  🗑️ Also delete S3 files
                </div>
                <div style={{
                  fontSize: '0.85rem',
                  color: '#6b7280',
                  lineHeight: '1.4'
                }}>
                  {type === 'danger' 
                    ? 'This will permanently delete all source and output files from S3 storage. This action cannot be undone.'
                    : 'This will delete existing output files from S3 storage before retrying. Source files will not be deleted.'
                  }
                </div>
              </div>
            </label>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{
          display: 'flex',
          gap: '12px',
          justifyContent: 'flex-end'
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '10px 20px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              background: 'white',
              color: '#374151',
              fontSize: '0.9rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => {
              e.target.style.background = '#f9fafb';
              e.target.style.borderColor = '#9ca3af';
            }}
            onMouseLeave={(e) => {
              e.target.style.background = 'white';
              e.target.style.borderColor = '#d1d5db';
            }}
          >
            {cancelText}
          </button>
          <button
            onClick={() => onConfirm(deleteFiles)}
            style={{
              padding: '10px 20px',
              border: 'none',
              borderRadius: '6px',
              background: styles.confirmButton.background,
              color: 'white',
              fontSize: '0.9rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => {
              e.target.style.background = styles.confirmButton.hoverBackground;
              e.target.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              e.target.style.background = styles.confirmButton.background;
              e.target.style.transform = 'translateY(0)';
            }}
          >
            {confirmText}
          </button>
        </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes modalSlideIn {
          from {
            opacity: 0;
            transform: scale(0.9);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
      `}</style>
    </>
  );
};

export default ConfirmModal;