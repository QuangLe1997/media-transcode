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
        document.getElementById('timestamp-container').innerHTML = '';

        // Load video profiles
        if (config.video_settings && config.video_settings.transcode_profiles) {
            config.video_settings.transcode_profiles.forEach(profile => {
                addVideoProfileWithData(profile);
            });
        } else {
            // Add one empty profile if none exist
            addVideoProfile();
        }

        // Load preview settings
        if (config.video_settings && config.video_settings.preview_settings) {
            const previewSettings = config.video_settings.preview_settings;
            document.getElementById('preview-duration').value = previewSettings.duration_seconds || 30;

            // Checkboxes for profiles will be handled by updatePreviewProfiles()
        }

        // Load thumbnail settings
        if (config.video_settings && config.video_settings.thumbnail_settings) {
            const thumbnailSettings = config.video_settings.thumbnail_settings;

            // Load timestamps
            document.getElementById('timestamp-container').innerHTML = '';
            if (thumbnailSettings.timestamps && thumbnailSettings.timestamps.length > 0) {
                thumbnailSettings.timestamps.forEach(timestamp => {
                    addTimestampWithValue(timestamp);
                });
            } else {
                addTimestamp();
            }

            // Load format and quality
            document.getElementById('thumbnail-format').value = thumbnailSettings.format || 'jpg';
            document.getElementById('thumbnail-quality').value = thumbnailSettings.quality || 90;

            // Load thumbnail sizes
            if (thumbnailSettings.sizes && thumbnailSettings.sizes.length > 0) {
                thumbnailSettings.sizes.forEach(size => {
                    addThumbnailSizeWithData(size);
                });
            } else {
                addThumbnailSize();
            }
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
            // Update preview profile checkboxes based on saved config
            if (config.video_settings && config.video_settings.preview_settings && config.video_settings.preview_settings.use_profiles) {
                const selectedProfiles = config.video_settings.preview_settings.use_profiles;
                document.querySelectorAll('.preview-profile-checkbox').forEach(checkbox => {
                    checkbox.checked = selectedProfiles.includes(checkbox.dataset.profileName);
                });
            }
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

    container.appendChild(profileItem);
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