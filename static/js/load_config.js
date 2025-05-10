/**
 * Load configuration in edit mode
 */
function loadConfigForEdit(configId) {
    const token = localStorage.getItem('token');

    fetch(`/api/configs/${configId}`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to load configuration');
        }
        return response.json();
    })
    .then(data => {
        // Parse configuration JSON if it's a string
        let config;
        if (typeof data.config_json === 'string') {
            config = JSON.parse(data.config_json);
        } else {
            config = data.config_json;
        }

        // Fill in basic information
        document.getElementById('config-name').value = data.name || '';
        document.getElementById('config-description').value = data.description || '';
        document.getElementById('config-default').checked = data.is_default || false;

        // Clear existing profiles
        document.getElementById('video-profiles-container').innerHTML = '';
        document.getElementById('thumbnail-sizes-container').innerHTML = '';
        document.getElementById('image-profiles-container').innerHTML = '';
        document.getElementById('image-thumbnail-profiles-container').innerHTML = '';

        // Clear existing preview profiles if exists
        if (document.getElementById('preview-profiles-container')) {
            document.getElementById('preview-profiles-container').innerHTML = '';
        }

        // Add Face Detection UI if not exists
        addFaceDetectionSection();

        // Load video profiles
        if (config.video_settings && config.video_settings.transcode_profiles) {
            config.video_settings.transcode_profiles.forEach(profile => {
                addVideoProfileWithData(profile);
            });
        } else {
            // Add one empty profile if none exist
            addVideoProfile();
        }

        // Load preview settings (now GIF-based)
        if (config.video_settings && config.video_settings.preview_settings) {
            const previewSettings = config.video_settings.preview_settings;

            // If old format, convert to new format
            if (previewSettings.duration_seconds && previewSettings.use_profiles) {
                // Old format - migrate to new format
                // Set up a default GIF profile for compatibility
                document.getElementById('preview-profiles-container').innerHTML = '';
                addGifPreviewProfile();

                // Set a default profile
                const previewProfile = document.querySelector('.gif-preview-profile');
                if (previewProfile) {
                    previewProfile.querySelector('.preview-name').value = 'small_gif';
                    previewProfile.querySelector('.preview-width').value = 320;
                    previewProfile.querySelector('.preview-height').value = 180;
                    previewProfile.querySelector('.preview-start').value = 0;
                    previewProfile.querySelector('.preview-end').value = previewSettings.duration_seconds || 30;
                    previewProfile.querySelector('.preview-fps').value = 10;
                    previewProfile.querySelector('.preview-quality').value = 80;
                }
            } else if (previewSettings.profiles && previewSettings.profiles.length > 0) {
                // New format - load GIF profiles
                document.getElementById('preview-profiles-container').innerHTML = '';
                previewSettings.profiles.forEach(profile => {
                    addGifPreviewProfileWithData(profile);
                });
            } else {
                // Add default profile
                addGifPreviewProfile();
            }
        } else {
            // Add default profile
            addGifPreviewProfile();
        }

        // Load thumbnail settings
        if (config.video_settings && config.video_settings.thumbnail_settings) {
            const thumbnailSettings = config.video_settings.thumbnail_settings;

            // Update for the new thumbnail format (single timestamp)
            updateThumbnailSection();

            // Set the timestamp value
            if (thumbnailSettings.timestamp !== undefined) {
                document.getElementById('thumbnail-timestamp').value = thumbnailSettings.timestamp;
            } else if (thumbnailSettings.timestamps && thumbnailSettings.timestamps.length > 0) {
                // Convert from old format
                // Try to parse the first timestamp to seconds if it's in HH:MM:SS format
                const firstTimestamp = thumbnailSettings.timestamps[0];
                let timestampValue = 5; // Default

                if (typeof firstTimestamp === 'string' && firstTimestamp.includes(':')) {
                    // Convert HH:MM:SS to seconds
                    const parts = firstTimestamp.split(':');
                    if (parts.length === 3) {
                        timestampValue = parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseFloat(parts[2]);
                    }
                } else if (!isNaN(parseFloat(firstTimestamp))) {
                    timestampValue = parseFloat(firstTimestamp);
                }

                document.getElementById('thumbnail-timestamp').value = timestampValue;
            }

            // Load format and quality
            document.getElementById('thumbnail-format').value = thumbnailSettings.format || 'jpg';
            document.getElementById('thumbnail-quality').value = thumbnailSettings.quality || 90;

            // Load thumbnail profiles
            document.getElementById('thumbnail-sizes-container').innerHTML = '';
            if (thumbnailSettings.profiles && thumbnailSettings.profiles.length > 0) {
                // New format
                thumbnailSettings.profiles.forEach(profile => {
                    addThumbnailSizeWithData(profile);
                });
            } else if (thumbnailSettings.sizes && thumbnailSettings.sizes.length > 0) {
                // Old format
                thumbnailSettings.sizes.forEach(size => {
                    addThumbnailSizeWithData(size);
                });
            } else {
                addThumbnailSize();
            }
        } else {
            updateThumbnailSection();
            addThumbnailSize();
        }

        // Load image profiles
        if (config.image_settings && config.image_settings.transcode_profiles) {
            config.image_settings.transcode_profiles.forEach(profile => {
                addImageProfileWithData(profile);
            });
        } else {
            // Add one empty profile if none exist
            addImageProfile();
        }

        // Load image thumbnail profiles
        if (config.image_settings && config.image_settings.thumbnail_profiles) {
            config.image_settings.thumbnail_profiles.forEach(profile => {
                addImageThumbnailProfileWithData(profile);
            });
        } else {
            // Add one empty profile if none exist
            addImageThumbnailProfile();
        }

        // Load face detection settings
        if (config.face_detection) {
            const faceDetection = config.face_detection;
            const enabled = faceDetection.enabled;

            document.getElementById('face-detection-enabled').checked = enabled;
            document.getElementById('face-detection-config').style.display = enabled ? 'block' : 'none';

            if (faceDetection.config) {
                const faceConfig = faceDetection.config;

                // Set values for all face detection configuration fields
                if (faceConfig.similarity_threshold !== undefined) {
                    document.getElementById('similarity-threshold').value = faceConfig.similarity_threshold;
                }

                if (faceConfig.min_faces_in_group !== undefined) {
                    document.getElementById('min-faces-in-group').value = faceConfig.min_faces_in_group;
                }

                if (faceConfig.sample_interval !== undefined) {
                    document.getElementById('sample-interval').value = faceConfig.sample_interval;
                }

                if (faceConfig.face_detector_size !== undefined) {
                    document.getElementById('face-detector-size').value = faceConfig.face_detector_size;
                }

                if (faceConfig.face_detector_score_threshold !== undefined) {
                    document.getElementById('face-detector-score').value = faceConfig.face_detector_score_threshold;
                }

                if (faceConfig.min_appearance_ratio !== undefined) {
                    document.getElementById('min-appearance-ratio').value = faceConfig.min_appearance_ratio;
                }

                if (faceConfig.min_frontality !== undefined) {
                    document.getElementById('min-frontality').value = faceConfig.min_frontality;
                }

                if (faceConfig.max_workers !== undefined) {
                    document.getElementById('max-workers').value = faceConfig.max_workers;
                }

                if (faceConfig.avatar_size !== undefined) {
                    document.getElementById('avatar-size').value = faceConfig.avatar_size;
                }

                if (faceConfig.avatar_padding !== undefined) {
                    document.getElementById('avatar-padding').value = faceConfig.avatar_padding;
                }

                if (faceConfig.avatar_quality !== undefined) {
                    document.getElementById('avatar-quality').value = faceConfig.avatar_quality;
                }

                // Handle ignore_frames (convert array to comma-separated string)
                if (faceConfig.ignore_frames && Array.isArray(faceConfig.ignore_frames)) {
                    document.getElementById('ignore-frames').value = faceConfig.ignore_frames.join(', ');
                }

                // Handle ignore_ranges (convert array of arrays to comma-separated string)
                if (faceConfig.ignore_ranges && Array.isArray(faceConfig.ignore_ranges)) {
                    const rangesStr = faceConfig.ignore_ranges.map(range => {
                        if (Array.isArray(range) && range.length >= 2) {
                            return `${range[0]}-${range[1]}`;
                        }
                        return '';
                    }).filter(s => s).join(', ');

                    document.getElementById('ignore-ranges').value = rangesStr;
                }
            }
        }

        // Load output settings
        if (config.output_settings) {
            const outputSettings = config.output_settings;
            document.getElementById('s3-bucket').value = outputSettings.s3_bucket || '';
            document.getElementById('folder-structure').value = outputSettings.folder_structure || '{user_id}/{job_id}/{type}/{profile_name}/';
            document.getElementById('generate-unique-filenames').checked = outputSettings.generate_unique_filenames !== false;
            document.getElementById('preserve-original-filename').checked = outputSettings.preserve_original_filename !== false;
            document.getElementById('use-temp-storage').checked = outputSettings.use_temporary_local_storage !== false;
            document.getElementById('temp-storage-path').value = outputSettings.local_storage_path || '/tmp/transcode-jobs/';
            document.getElementById('delete-after-upload').checked = outputSettings.delete_local_after_upload !== false;
        }

        // Update preview profiles and JSON preview
        updatePreviewProfiles();
        setTimeout(() => {
            // Update JSON preview
            updateJsonPreview();
        }, 100);
    })
    .catch(error => {
        console.error('Error loading configuration:', error);
        alert('Failed to load configuration. Please try again.');
    });
}

/**
 * Add a video profile with preset data
 */
function addVideoProfileWithData(profileData) {
    const container = document.getElementById('video-profiles-container');
    const template = document.getElementById('video-profile-template');
    const profileItem = template.content.cloneNode(true);

    profileItem.querySelector('.profile-name').value = profileData.name || '';
    profileItem.querySelector('.profile-width').value = profileData.width || 1280;
    profileItem.querySelector('.profile-height').value = profileData.height || 720;

    if (profileData.codec) {
        const codecSelect = profileItem.querySelector('.profile-codec');
        if (Array.from(codecSelect.options).some(option => option.value === profileData.codec)) {
            codecSelect.value = profileData.codec;
        }
    }

    if (profileData.preset) {
        const presetSelect = profileItem.querySelector('.profile-preset');
        if (Array.from(presetSelect.options).some(option => option.value === profileData.preset)) {
            presetSelect.value = profileData.preset;
        }
    }

    profileItem.querySelector('.profile-crf').value = profileData.crf || 23;

    if (profileData.format) {
        const formatSelect = profileItem.querySelector('.profile-format');
        if (Array.from(formatSelect.options).some(option => option.value === profileData.format)) {
            formatSelect.value = profileData.format;
        }
    }

    if (profileData.audio_codec) {
        const audioCodecSelect = profileItem.querySelector('.profile-audio-codec');
        if (Array.from(audioCodecSelect.options).some(option => option.value === profileData.audio_codec)) {
            audioCodecSelect.value = profileData.audio_codec;
        }
    }

    profileItem.querySelector('.profile-audio-bitrate').value = profileData.audio_bitrate || '128k';
    profileItem.querySelector('.profile-use-gpu').checked = profileData.use_gpu !== false;

    // Check if this profile has start/end times (trim settings)
    if (profileData.start !== undefined || profileData.end !== undefined) {
        // We need to add the start/end time inputs
        const rowDiv = document.createElement('div');
        rowDiv.className = 'row mb-3 trim-times';
        rowDiv.innerHTML = `
            <div class="col-md-3">
                <label class="form-label">Start Time (sec)</label>
                <input type="number" class="form-control profile-start-time" min="0" step="0.1" value="${profileData.start || ''}">
            </div>
            <div class="col-md-3">
                <label class="form-label">End Time (sec)</label>
                <input type="number" class="form-control profile-end-time" min="0" step="0.1" value="${profileData.end || ''}">
            </div>
            <div class="col-md-6">
                <div class="form-text mt-4">
                    Optional: Specify range to trim video (leave empty for full video)
                </div>
            </div>
        `;

        // Insert after the first row
        const firstRow = profileItem.querySelector('.row');
        firstRow.parentNode.insertBefore(rowDiv, firstRow.nextSibling);
    }

    container.appendChild(profileItem);
}

/**
 * Add a GIF preview profile with preset data
 */
function addGifPreviewProfileWithData(profileData) {
    const container = document.getElementById('preview-profiles-container');

    // Clear any existing message
    if (container.querySelector('.text-muted')) {
        container.innerHTML = '';
    }

    const html = `
        <div class="profile-item gif-preview-profile">
            <i class="fas fa-times remove-profile"></i>
            <div class="row mb-3">
                <div class="col-md-4">
                    <label class="form-label">Profile Name</label>
                    <input type="text" class="form-control preview-name" placeholder="small_gif" value="${profileData.name || 'small_gif'}">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Width</label>
                    <input type="number" class="form-control preview-width" value="${profileData.width || 320}">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Height</label>
                    <input type="number" class="form-control preview-height" value="${profileData.height || 180}">
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-3">
                    <label class="form-label">Start Time (sec)</label>
                    <input type="number" class="form-control preview-start" value="${profileData.start !== undefined ? profileData.start : 0}" min="0" step="0.1">
                </div>
                <div class="col-md-3">
                    <label class="form-label">End Time (sec)</label>
                    <input type="number" class="form-control preview-end" value="${profileData.end !== undefined ? profileData.end : 5}" min="0" step="0.1">
                </div>
                <div class="col-md-3">
                    <label class="form-label">FPS</label>
                    <input type="number" class="form-control preview-fps" value="${profileData.fps || 10}" min="1" max="30">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Quality (1-100)</label>
                    <input type="number" class="form-control preview-quality" value="${profileData.quality || 80}" min="1" max="100">
                </div>
            </div>
        </div>
    `;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    container.appendChild(tempDiv.firstElementChild);
}

/**
 * Add a timestamp with preset value
 */
function addTimestampWithValue(value) {
    const container = document.getElementById('timestamp-container');
    const html = `
        <div class="col-md-3 mb-2">
            <div class="input-group">
                <input type="text" class="form-control timestamp-input" value="${value}" pattern="[0-9]{2}:[0-9]{2}:[0-9]{2}">
                <button class="btn btn-outline-danger remove-timestamp" type="button">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    `;
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    container.appendChild(tempDiv.firstElementChild);
}

/**
 * Add a thumbnail size with preset data
 */
function addThumbnailSizeWithData(sizeData) {
    const container = document.getElementById('thumbnail-sizes-container');
    const template = document.getElementById('thumbnail-size-template');
    const sizeItem = template.content.cloneNode(true);

    sizeItem.querySelector('.thumbnail-size-name').value = sizeData.name || '';
    sizeItem.querySelector('.thumbnail-size-width').value = sizeData.width || 320;
    sizeItem.querySelector('.thumbnail-size-height').value = sizeData.height || 180;

    container.appendChild(sizeItem);
}


/**
 * Add an image thumbnail profile with preset data
 */
function addImageThumbnailProfileWithData(profileData) {
    const container = document.getElementById('image-thumbnail-profiles-container');
    const template = document.getElementById('image-thumbnail-template');
    const profileItem = template.content.cloneNode(true);

    profileItem.querySelector('.profile-name').value = profileData.name || '';
    profileItem.querySelector('.profile-width').value = profileData.width || 320;
    profileItem.querySelector('.profile-height').value = profileData.height || 240;

    if (profileData.format) {
        const formatSelect = profileItem.querySelector('.profile-format');
        if (Array.from(formatSelect.options).some(option => option.value === profileData.format)) {
            formatSelect.value = profileData.format;
        }
    }

    profileItem.querySelector('.profile-quality').value = profileData.quality || 85;
    profileItem.querySelector('.profile-maintain-aspect').checked = profileData.maintain_aspect_ratio !== false;

    container.appendChild(profileItem);
}

/**
 * Add face detection section to the UI
 */
function addFaceDetectionSection() {
    // Check if the face detection section already exists
    if (document.getElementById('face-detection-section')) {
        return;
    }

    const videoTab = document.getElementById('video');

    // Create face detection section
    const faceDetectionSection = document.createElement('div');
    faceDetectionSection.id = 'face-detection-section';
    faceDetectionSection.className = 'form-section';
    faceDetectionSection.innerHTML = `
        <h5>Face Detection Settings</h5>
        <p class="text-muted">Settings for detecting and extracting faces from videos and images</p>
        
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" id="face-detection-enabled">
                    <label class="form-check-label" for="face-detection-enabled">Enable Face Detection</label>
                </div>
            </div>
        </div>
        
        <div id="face-detection-config" style="display: none;">
            <div class="row mb-3">
                <div class="col-md-4">
                    <label class="form-label">Similarity Threshold (0-1)</label>
                    <input type="number" class="form-control" id="similarity-threshold" value="0.6" min="0" max="1" step="0.05">
                    <div class="form-text">Lower values create more face groups</div>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Min Faces in Group</label>
                    <input type="number" class="form-control" id="min-faces-in-group" value="3" min="1" max="100">
                    <div class="form-text">Minimum faces required for a group</div>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Sample Interval</label>
                    <input type="number" class="form-control" id="sample-interval" value="5" min="1" max="30">
                    <div class="form-text">Process every N-th frame</div>
                </div>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label">Face Detector Size</label>
                    <select class="form-select" id="face-detector-size">
                        <option value="320x320">320x320 (Faster)</option>
                        <option value="640x640" selected>640x640 (Balanced)</option>
                        <option value="1280x1280">1280x1280 (More accurate)</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Score Threshold (0-1)</label>
                    <input type="number" class="form-control" id="face-detector-score" value="0.6" min="0" max="1" step="0.05">
                    <div class="form-text">Minimum confidence score for detection</div>
                </div>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-4">
                    <label class="form-label">Min Appearance Ratio (0-1)</label>
                    <input type="number" class="form-control" id="min-appearance-ratio" value="0.15" min="0" max="1" step="0.05">
                    <div class="form-text">Minimum ratio of frames a face must appear in</div>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Min Frontality (0-1)</label>
                    <input type="number" class="form-control" id="min-frontality" value="0.2" min="0" max="1" step="0.05">
                    <div class="form-text">Minimum frontality score for faces</div>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Max Workers</label>
                    <input type="number" class="form-control" id="max-workers" value="4" min="1" max="16">
                    <div class="form-text">Maximum parallel processing threads</div>
                </div>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-4">
                    <label class="form-label">Avatar Size (px)</label>
                    <input type="number" class="form-control" id="avatar-size" value="256" min="64" max="1024">
                    <div class="form-text">Size of face avatar images</div>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Avatar Padding (0-1)</label>
                    <input type="number" class="form-control" id="avatar-padding" value="0.1" min="0" max="1" step="0.05">
                    <div class="form-text">Amount of padding around faces</div>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Avatar Quality (1-100)</label>
                    <input type="number" class="form-control" id="avatar-quality" value="90" min="1" max="100">
                    <div class="form-text">JPEG quality for avatars</div>
                </div>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-12">
                    <label class="form-label">Ignore Frames (comma-separated list)</label>
                    <input type="text" class="form-control" id="ignore-frames" placeholder="0, 1, 2">
                    <div class="form-text">Specific frame numbers to ignore</div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-12">
                    <label class="form-label">Ignore Ranges (format: start-end, comma-separated)</label>
                    <input type="text" class="form-control" id="ignore-ranges" placeholder="500-600, 1200-1300">
                    <div class="form-text">Ranges of frame numbers to ignore</div>
                </div>
            </div>
        </div>
    `;

    // Add to video tab before the last section
    const sections = videoTab.querySelectorAll('.form-section');
    if (sections.length > 0) {
        const lastSection = sections[sections.length - 1];
        videoTab.insertBefore(faceDetectionSection, lastSection.nextSibling);
    } else {
        videoTab.appendChild(faceDetectionSection);
    }

    // Add event listener for enable/disable toggle
    document.getElementById('face-detection-enabled').addEventListener('change', function (e) {
        document.getElementById('face-detection-config').style.display = e.target.checked ? 'block' : 'none';
    });
}

/**
 * Modified thumbnail settings UI to handle one timestamp
 */
function updateThumbnailSection() {
    const timestampContainer = document.getElementById('timestamp-container');
    const addTimestampBtn = document.getElementById('add-timestamp');

    // Replace multiple timestamps with a single timestamp input
    timestampContainer.innerHTML = `
        <div class="col-md-4 mb-2">
            <label class="form-label">Thumbnail Timestamp (seconds)</label>
            <input type="number" class="form-control" id="thumbnail-timestamp" value="5" min="0" step="0.1">
            <div class="form-text">Time in seconds to extract thumbnail</div>
        </div>
    `;

    // Hide the add button if it exists
    if (addTimestampBtn) {
        addTimestampBtn.style.display = 'none';
    }
}

/**
 * Add a GIF preview profile
 */
function addGifPreviewProfile() {
    const container = document.getElementById('preview-profiles-container');

    // Clear any existing message
    if (container.querySelector('.text-muted')) {
        container.innerHTML = '';
    }

    const html = `
        <div class="profile-item gif-preview-profile">
            <i class="fas fa-times remove-profile"></i>
            <div class="row mb-3">
                <div class="col-md-4">
                    <label class="form-label">Profile Name</label>
                    <input type="text" class="form-control preview-name" placeholder="small_gif" value="small_gif">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Width</label>
                    <input type="number" class="form-control preview-width" value="320">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Height</label>
                    <input type="number" class="form-control preview-height" value="180">
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-3">
                    <label class="form-label">Start Time (sec)</label>
                    <input type="number" class="form-control preview-start" value="0" min="0" step="0.1">
                </div>
                <div class="col-md-3">
                    <label class="form-label">End Time (sec)</label>
                    <input type="number" class="form-control preview-end" value="5" min="0" step="0.1">
                </div>
                <div class="col-md-3">
                    <label class="form-label">FPS</label>
                    <input type="number" class="form-control preview-fps" value="10" min="1" max="30">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Quality (1-100)</label>
                    <input type="number" class="form-control preview-quality" value="80" min="1" max="100">
                </div>
            </div>
        </div>
    `;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    container.appendChild(tempDiv.firstElementChild);
}

/**
 * Add an image profile with preset data
 */
function addImageProfileWithData(profileData) {
    const container = document.getElementById('image-profiles-container');
    const template = document.getElementById('image-profile-template');
    const profileItem = template.content.cloneNode(true);

    profileItem.querySelector('.profile-name').value = profileData.name || '';

    if (profileData.format) {
        const formatSelect = profileItem.querySelector('.profile-format');
        if (Array.from(formatSelect.options).some(option => option.value === profileData.format)) {
            formatSelect.value = profileData.format;
        }
    }

    profileItem.querySelector('.profile-quality').value = profileData.quality || 90;
    profileItem.querySelector('.profile-resize').checked = profileData.resize === true;

    container.appendChild(profileItem);
}

