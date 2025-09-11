/**
 * Configuration Builder JavaScript
 * A comprehensive tool for building media transcoding configurations
 */

class ConfigurationBuilder {
    constructor() {
        this.config = {};
        this.baseConfig = {};
        this.currentSection = 0;
        this.sections = [
            'basic-info', 'video-settings', 'image-settings', 'face-detection',
            'output-settings'
        ];
        this.validation = {
            errors: [],
            warnings: [],
            isValid: false
        };
        this.isDirty = false;
        this.currentMode = 'form';
        this.jsonEditor = null;
        
        this.init();
    }

    async init() {
        try {
            await this.loadBaseConfig();
            
            // Check if we're editing an existing config
            if (window.CONFIG_ID) {
                await this.loadExistingConfig(window.CONFIG_ID);
            } else {
                this.initializeConfig();
            }
            
            this.setupEventListeners();
            this.initializeNavigation();
            this.loadSection('basic-info');
            this.updateProgress();
            
            console.log('Configuration Builder initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Configuration Builder:', error);
            this.showNotification('Failed to initialize the application', 'error');
        }
    }

    async loadBaseConfig() {
        try {
            const response = await fetch('/config_samples/base_config.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.baseConfig = await response.json();
        } catch (error) {
            console.error('Failed to load base config:', error);
            // Fallback to minimal config
            this.baseConfig = {
                config_name: '',
                description: '',
                video_settings: { _enabled: true, transcode_profiles: [] },
                image_settings: { _enabled: true, transcode_profiles: [] },
                face_detection: { enabled: false },
                output_settings: { storage: {} }
            };
        }
    }

    async loadExistingConfig(configId) {
        try {
            console.log('Loading config with ID:', configId);
            this.showLoading('Loading configuration...');
            
            const token = localStorage.getItem('token') || sessionStorage.getItem('token');
            if (!token) {
                throw new Error('No authentication token found');
            }
            
            const response = await fetch(`/api/configs/${configId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.text();
                console.error('API Error Response:', errorData);
                throw new Error(`Failed to load config: ${response.status} - ${errorData}`);
            }
            
            const configData = await response.json();
            console.log('Received config data:', configData);
            
            // Parse the config JSON
            if (configData.config_json) {
                if (typeof configData.config_json === 'string') {
                    this.config = JSON.parse(configData.config_json);
                } else {
                    this.config = configData.config_json;
                }
            } else {
                console.warn('No config_json found in response, using base config');
                this.initializeConfig();
                this.hideLoading();
                return;
            }
            
            // Update basic info from database fields
            this.config.config_name = configData.name || this.config.config_name;
            this.config.description = configData.description || this.config.description;
            this.config.created_at = configData.created_at || this.config.created_at;
            this.config.updated_at = configData.updated_at || new Date().toISOString();
            
            console.log('Config loaded and processed:', this.config);
            this.hideLoading();
            this.showNotification('Configuration loaded successfully', 'success');
            
            // Populate form with loaded data after a short delay
            setTimeout(() => {
                this.populateFormFromConfig();
            }, 200);
            
        } catch (error) {
            console.error('Failed to load existing config:', error);
            this.hideLoading();
            this.showNotification(`Failed to load configuration: ${error.message}`, 'error');
            this.initializeConfig();
        }
    }

    initializeConfig() {
        this.config = JSON.parse(JSON.stringify(this.baseConfig));
        this.config.created_at = new Date().toISOString();
        this.config.updated_at = new Date().toISOString();
    }

    setupEventListeners() {
        // Mode switching
        document.getElementById('formModeBtn')?.addEventListener('click', () => this.switchMode('form'));
        document.getElementById('jsonModeBtn')?.addEventListener('click', () => this.switchMode('json'));

        // Header actions
        document.getElementById('loadTemplateBtn')?.addEventListener('click', () => this.openTemplateLibrary());
        document.getElementById('validateBtn')?.addEventListener('click', () => this.validateConfiguration());
        document.getElementById('exportBtn')?.addEventListener('click', () => this.exportConfiguration());
        document.getElementById('saveBtn')?.addEventListener('click', () => this.saveConfiguration());

        // Navigation
        document.getElementById('prevSectionBtn')?.addEventListener('click', () => this.previousSection());
        document.getElementById('nextSectionBtn')?.addEventListener('click', () => this.nextSection());

        // Sidebar navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const section = item.dataset.section;
                if (section) {
                    this.loadSection(section);
                }
            });
        });

        // Form change detection
        document.addEventListener('input', (e) => {
            if (e.target.closest('.config-section')) {
                this.markDirty();
                this.updateConfigFromForm();
            }
        });

        document.addEventListener('change', (e) => {
            if (e.target.closest('.config-section')) {
                this.markDirty();
                this.updateConfigFromForm();
            }
        });

        // Window beforeunload
        window.addEventListener('beforeunload', (e) => {
            if (this.isDirty) {
                e.preventDefault();
                e.returnValue = '';
            }
        });

        // Modal events
        document.getElementById('closeTemplateModal')?.addEventListener('click', () => this.closeTemplateLibrary());
        document.getElementById('templateModalOverlay')?.addEventListener('click', () => this.closeTemplateLibrary());
        document.getElementById('closeValidationBtn')?.addEventListener('click', () => this.closeValidationPanel());

        // JSON Editor events
        document.getElementById('formatJsonBtn')?.addEventListener('click', () => this.formatJSON());
        document.getElementById('validateJsonBtn')?.addEventListener('click', () => this.validateJSON());
        document.getElementById('syncFromFormBtn')?.addEventListener('click', () => this.syncFromForm());
    }

    initializeNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach((item, index) => {
            item.dataset.index = index;
        });
    }

    switchMode(mode) {
        const formMode = document.getElementById('formBuilderMode');
        const jsonMode = document.getElementById('jsonEditorMode');
        const formBtn = document.getElementById('formModeBtn');
        const jsonBtn = document.getElementById('jsonModeBtn');

        if (mode === 'json') {
            formMode?.classList.remove('active');
            jsonMode?.classList.add('active');
            formBtn?.classList.remove('active');
            jsonBtn?.classList.add('active');
            this.initJsonEditor();
            this.currentMode = 'json';
        } else {
            formMode?.classList.add('active');
            jsonMode?.classList.remove('active');
            formBtn?.classList.add('active');
            jsonBtn?.classList.remove('active');
            this.currentMode = 'form';
        }
    }

    async initJsonEditor() {
        if (this.jsonEditor) {
            this.updateJsonEditor();
            return;
        }

        try {
            const monaco = await new Promise((resolve) => {
                require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.34.1/min/vs' } });
                require(['vs/editor/editor.main'], resolve);
            });

            this.jsonEditor = monaco.editor.create(document.getElementById('jsonEditor'), {
                value: JSON.stringify(this.config, null, 2),
                language: 'json',
                theme: 'vs',
                fontSize: 13,
                fontFamily: 'Fira Code, Monaco, Cascadia Code, Roboto Mono, monospace',
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                formatOnPaste: true,
                formatOnType: true,
                autoIndent: 'advanced',
                bracketPairColorization: { enabled: true },
                suggest: { snippetsPreventQuickSuggestions: false }
            });

            // Setup JSON schema validation
            monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
                validate: true,
                schemas: [{
                    uri: 'config-schema.json',
                    fileMatch: ['*'],
                    schema: this.getConfigSchema()
                }]
            });

            this.jsonEditor.onDidChangeModelContent(() => {
                this.markDirty();
                this.updateLineCount();
                this.validateJSONContent();
            });

            this.updateLineCount();
        } catch (error) {
            console.error('Failed to initialize Monaco Editor:', error);
            this.showNotification('Failed to load JSON editor', 'error');
        }
    }

    updateJsonEditor() {
        if (this.jsonEditor) {
            const currentValue = this.jsonEditor.getValue();
            const newValue = JSON.stringify(this.config, null, 2);
            if (currentValue !== newValue) {
                this.jsonEditor.setValue(newValue);
            }
        }
    }

    updateLineCount() {
        if (this.jsonEditor) {
            const lineCount = this.jsonEditor.getModel().getLineCount();
            const lineCountElement = document.getElementById('jsonLineCount');
            if (lineCountElement) {
                lineCountElement.textContent = `Lines: ${lineCount}`;
            }
        }
    }

    validateJSONContent() {
        if (!this.jsonEditor) return;

        try {
            const value = this.jsonEditor.getValue();
            JSON.parse(value);
            this.updateJsonStatus('Valid JSON', 'success');
        } catch (error) {
            this.updateJsonStatus(`Invalid JSON: ${error.message}`, 'error');
        }
    }

    updateJsonStatus(message, type) {
        const statusElement = document.getElementById('jsonStatus');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `status-indicator ${type}`;
        }
    }

    loadSection(sectionName) {
        // Hide all sections
        document.querySelectorAll('.config-section').forEach(section => {
            section.classList.remove('active');
        });

        // Show target section
        const targetSection = document.getElementById(`${sectionName}-section`);
        if (targetSection) {
            targetSection.classList.add('active');
        }

        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });

        const activeNavItem = document.querySelector(`[data-section="${sectionName}"]`);
        if (activeNavItem) {
            activeNavItem.classList.add('active');
            this.currentSection = parseInt(activeNavItem.dataset.index) || 0;
        }

        // Update navigation buttons
        this.updateNavigationButtons();

        // Load section content
        this.loadSectionContent(sectionName);

        // Update progress
        this.updateProgress();
    }

    loadSectionContent(sectionName) {
        switch (sectionName) {
            case 'basic-info':
                this.loadBasicInfoSection();
                break;
            case 'video-settings':
                this.loadVideoSettingsSection();
                break;
            case 'image-settings':
                this.loadImageSettingsSection();
                break;
            case 'face-detection':
                this.loadFaceDetectionSection();
                break;
            case 'output-settings':
                this.loadOutputSettingsSection();
                break;
        }
    }

    loadBasicInfoSection() {
        // Load basic information form fields
        this.setFieldValue('configName', this.config.config_name);
        this.setFieldValue('description', this.config.description);
        this.setFieldValue('version', this.config.version || '1.0.0');
        this.setFieldValue('tags', Array.isArray(this.config.tags) ? this.config.tags.join(', ') : '');
        this.setFieldValue('createdAt', this.config.created_at || '');
        this.setFieldValue('updatedAt', this.config.updated_at || '');
        
        // Set timestamps if not already set
        if (!this.config.created_at) {
            this.config.created_at = new Date().toISOString();
            this.setFieldValue('createdAt', this.config.created_at);
        }
        if (!this.config.updated_at) {
            this.config.updated_at = new Date().toISOString();
            this.setFieldValue('updatedAt', this.config.updated_at);
        }
    }

    loadVideoSettingsSection() {
        // Setup video settings toggle
        const videoEnabled = document.getElementById('videoEnabled');
        const videoContainer = document.getElementById('videoSettingsContainer');
        
        if (videoEnabled && videoContainer) {
            videoEnabled.checked = this.config.video_settings?._enabled !== false;
            videoContainer.style.display = videoEnabled.checked ? 'block' : 'none';
            
            videoEnabled.addEventListener('change', () => {
                videoContainer.style.display = videoEnabled.checked ? 'block' : 'none';
                this.config.video_settings._enabled = videoEnabled.checked;
                this.markDirty();
            });
        }

        // Load video profiles
        this.loadVideoProfiles();
        this.loadPreviewProfiles();
        this.loadThumbnailProfiles();

        // Setup add profile buttons
        this.setupAddProfileButtons();
    }

    loadVideoProfiles() {
        const container = document.getElementById('videoProfilesContainer');
        if (!container) return;

        container.innerHTML = '';
        
        const profiles = this.config.video_settings?.transcode_profiles || [];
        profiles.forEach((profile, index) => {
            const profileCard = this.createVideoProfileCard(profile, index);
            container.appendChild(profileCard);
        });

        if (profiles.length === 0) {
            container.innerHTML = '<p class="text-muted">No video profiles configured. Click "Add Profile" to create one.</p>';
        }

        this.updateProfileCount('video-profiles-count', profiles.length);
    }

    loadPreviewProfiles() {
        const container = document.getElementById('previewProfilesContainer');
        if (!container) return;

        container.innerHTML = '';
        
        const profiles = this.config.video_settings?.preview_settings?.profiles || [];
        profiles.forEach((profile, index) => {
            const profileCard = this.createPreviewProfileCard(profile, index);
            container.appendChild(profileCard);
        });

        if (profiles.length === 0) {
            container.innerHTML = '<p class="text-muted">No preview profiles configured. Click "Add Preview Profile" to create one.</p>';
        }
    }

    loadThumbnailProfiles() {
        const container = document.getElementById('thumbnailProfilesContainer');
        if (!container) return;

        container.innerHTML = '';
        
        const profiles = this.config.video_settings?.thumbnail_settings?.profiles || [];
        profiles.forEach((profile, index) => {
            const profileCard = this.createThumbnailProfileCard(profile, index);
            container.appendChild(profileCard);
        });

        if (profiles.length === 0) {
            container.innerHTML = '<p class="text-muted">No thumbnail profiles configured. Click "Add Thumbnail Profile" to create one.</p>';
        }

        // Load thumbnail timestamp
        const timestampField = document.getElementById('thumbnailTimestamp');
        if (timestampField) {
            timestampField.value = this.config.video_settings?.thumbnail_settings?.timestamp || 5;
            timestampField.addEventListener('input', () => {
                if (!this.config.video_settings) this.config.video_settings = {};
                if (!this.config.video_settings.thumbnail_settings) this.config.video_settings.thumbnail_settings = {};
                this.config.video_settings.thumbnail_settings.timestamp = parseFloat(timestampField.value) || 5;
                this.markDirty();
            });
        }
    }

    createVideoProfileCard(profile, index) {
        const card = document.createElement('div');
        card.className = 'profile-card';
        card.innerHTML = `
            <div class="profile-header">
                <div class="profile-title">${profile.name || `Video Profile ${index + 1}`}</div>
                <div class="profile-actions">
                    <button type="button" class="btn btn-sm btn-secondary" onclick="configBuilder.duplicateVideoProfile(${index})">
                        <i class="fas fa-copy"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-warning" onclick="configBuilder.removeVideoProfile(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="profile-fields">
                ${this.generateVideoProfileFields(profile, index)}
            </div>
        `;
        return card;
    }

    createPreviewProfileCard(profile, index) {
        const card = document.createElement('div');
        card.className = 'profile-card';
        card.dataset.profileIndex = index;
        card.innerHTML = `
            <div class="profile-header">
                <div class="profile-title">${profile.name || `Preview Profile ${index + 1}`}</div>
                <div class="profile-actions">
                    <button type="button" class="btn btn-sm btn-secondary" onclick="configBuilder.duplicatePreviewProfile(${index})">
                        <i class="fas fa-copy"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-warning" onclick="configBuilder.removePreviewProfile(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="profile-fields">
                <!-- Basic Settings (2 columns) -->
                <div class="form-grid-2">
                    <div class="form-group">
                        <label>Profile Name</label>
                        <input type="text" data-path="video_settings.preview_settings.profiles.${index}.name" 
                               value="${profile.name || ''}" placeholder="e.g., preview_640">
                    </div>
                    <div class="form-group">
                        <label>Format</label>
                        <select data-path="video_settings.preview_settings.profiles.${index}.format" 
                                onchange="configBuilder.updatePreviewProfileFields(${index}, this.value)">
                            <option value="gif" ${profile.format === 'gif' ? 'selected' : ''}>GIF</option>
                            <option value="mp4" ${profile.format === 'mp4' ? 'selected' : ''}>MP4</option>
                            <option value="webm" ${profile.format === 'webm' ? 'selected' : ''}>WebM</option>
                        </select>
                    </div>
                </div>

                <!-- Timing Settings (2 columns) -->
                <div class="form-grid-2">
                    <div class="form-group">
                        <label>Start Time (seconds)</label>
                        <input type="number" data-path="video_settings.preview_settings.profiles.${index}.start" 
                               value="${profile.start || 0}" min="0" step="0.1">
                    </div>
                    <div class="form-group">
                        <label>End Time (seconds)</label>
                        <input type="number" data-path="video_settings.preview_settings.profiles.${index}.end" 
                               value="${profile.end || 5}" min="0" step="0.1">
                    </div>
                </div>

                <!-- Format-specific Settings -->
                <div id="preview-format-fields-${index}">
                    ${this.generatePreviewFormatFields(profile, index)}
                </div>
            </div>
        `;
        return card;
    }

    generatePreviewFormatFields(profile, index) {
        if (profile.format === 'mp4' || profile.format === 'webm') {
            // Video format fields (similar to transcode profiles but without audio)
            return `
                <!-- Video Dimensions (3 columns) -->
                <div class="form-grid-3">
                    <div class="form-group">
                        <label>Width</label>
                        <input type="number" data-path="video_settings.preview_settings.profiles.${index}.width" 
                               value="${profile.width || 640}" min="64" max="3840">
                    </div>
                    <div class="form-group">
                        <label>Height</label>
                        <input type="number" data-path="video_settings.preview_settings.profiles.${index}.height" 
                               value="${profile.height || 360}" min="64" max="2160">
                    </div>
                    <div class="form-group">
                        <label>Frame Rate (FPS)</label>
                        <input type="number" data-path="video_settings.preview_settings.profiles.${index}.fps" 
                               value="${profile.fps || 30}" min="1" max="60">
                    </div>
                </div>

                <!-- Video Encoding (3 columns) -->
                <div class="form-grid-3">
                    <div class="form-group">
                        <label>Codec</label>
                        <select data-path="video_settings.preview_settings.profiles.${index}.codec">
                            <option value="libx264" ${profile.codec === 'libx264' ? 'selected' : ''}>H.264</option>
                            <option value="libx265" ${profile.codec === 'libx265' ? 'selected' : ''}>H.265</option>
                            <option value="libvpx-vp9" ${profile.codec === 'libvpx-vp9' ? 'selected' : ''}>VP9</option>
                            <option value="h264_nvenc" ${profile.codec === 'h264_nvenc' ? 'selected' : ''}>H.264 NVENC</option>
                            <option value="hevc_nvenc" ${profile.codec === 'hevc_nvenc' ? 'selected' : ''}>H.265 NVENC</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Preset</label>
                        <select data-path="video_settings.preview_settings.profiles.${index}.preset">
                            <option value="ultrafast" ${profile.preset === 'ultrafast' ? 'selected' : ''}>Ultra Fast</option>
                            <option value="fast" ${profile.preset === 'fast' ? 'selected' : ''}>Fast</option>
                            <option value="medium" ${profile.preset === 'medium' ? 'selected' : ''}>Medium</option>
                            <option value="slow" ${profile.preset === 'slow' ? 'selected' : ''}>Slow</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>CRF (Quality)</label>
                        <input type="number" data-path="video_settings.preview_settings.profiles.${index}.crf" 
                               value="${profile.crf || 23}" min="0" max="51" step="1">
                        <small class="form-help">Lower = better</small>
                    </div>
                </div>

                <!-- Video Options (1 column) -->
                <div class="form-grid">
                    <div class="form-group">
                        <label class="toggle-switch">
                            <input type="checkbox" data-path="video_settings.preview_settings.profiles.${index}.use_gpu" 
                                   ${profile.use_gpu !== false ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">Use GPU Acceleration</span>
                        </label>
                    </div>
                </div>
            `;
        } else {
            // GIF format fields
            return `
                <!-- GIF Dimensions (3 columns) -->
                <div class="form-grid-3">
                    <div class="form-group">
                        <label>Width</label>
                        <input type="number" data-path="video_settings.preview_settings.profiles.${index}.width" 
                               value="${profile.width || 640}" min="64" max="1920">
                    </div>
                    <div class="form-group">
                        <label>Height</label>
                        <input type="number" data-path="video_settings.preview_settings.profiles.${index}.height" 
                               value="${profile.height || 360}" min="64" max="1080">
                    </div>
                    <div class="form-group">
                        <label>Frame Rate (FPS)</label>
                        <input type="number" data-path="video_settings.preview_settings.profiles.${index}.fps" 
                               value="${profile.fps || 12}" min="1" max="30">
                    </div>
                </div>

                <!-- GIF Quality (3 columns) -->
                <div class="form-grid-3">
                    <div class="form-group">
                        <label>Quality</label>
                        <input type="number" data-path="video_settings.preview_settings.profiles.${index}.quality" 
                               value="${profile.quality || 80}" min="1" max="100">
                    </div>
                    <div class="form-group">
                        <label>Dither</label>
                        <select data-path="video_settings.preview_settings.profiles.${index}.dither">
                            <option value="none" ${profile.dither === 'none' ? 'selected' : ''}>None</option>
                            <option value="floyd_steinberg" ${profile.dither === 'floyd_steinberg' ? 'selected' : ''}>Floyd-Steinberg</option>
                            <option value="sierra2_4a" ${profile.dither === 'sierra2_4a' ? 'selected' : ''}>Sierra2-4A</option>
                            <option value="bayer" ${profile.dither === 'bayer' ? 'selected' : ''}>Bayer</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Palette Size</label>
                        <input type="number" data-path="video_settings.preview_settings.profiles.${index}.palette_size" 
                               value="${profile.palette_size || 256}" min="2" max="256">
                    </div>
                </div>

                <!-- GIF Options (2 columns) -->
                <div class="form-grid-2">
                    <div class="form-group">
                        <label class="toggle-switch">
                            <input type="checkbox" data-path="video_settings.preview_settings.profiles.${index}.loop" 
                                   ${profile.loop !== false ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">Loop Animation</span>
                        </label>
                    </div>
                    <div class="form-group">
                        <label class="toggle-switch">
                            <input type="checkbox" data-path="video_settings.preview_settings.profiles.${index}.optimize" 
                                   ${profile.optimize !== false ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">Optimize File Size</span>
                        </label>
                    </div>
                </div>
            `;
        }
    }

    updatePreviewProfileFields(index, format) {
        const container = document.getElementById(`preview-format-fields-${index}`);
        if (!container) return;

        // Update the format in config
        if (this.config.video_settings?.preview_settings?.profiles?.[index]) {
            this.config.video_settings.preview_settings.profiles[index].format = format;
            
            // Set default values based on format
            if (format === 'mp4' || format === 'webm') {
                // Video defaults
                this.config.video_settings.preview_settings.profiles[index].codec = this.config.video_settings.preview_settings.profiles[index].codec || 'libx264';
                this.config.video_settings.preview_settings.profiles[index].preset = this.config.video_settings.preview_settings.profiles[index].preset || 'fast';
                this.config.video_settings.preview_settings.profiles[index].crf = this.config.video_settings.preview_settings.profiles[index].crf || 23;
                this.config.video_settings.preview_settings.profiles[index].fps = this.config.video_settings.preview_settings.profiles[index].fps || 30;
            } else {
                // GIF defaults
                this.config.video_settings.preview_settings.profiles[index].fps = this.config.video_settings.preview_settings.profiles[index].fps || 12;
                this.config.video_settings.preview_settings.profiles[index].quality = this.config.video_settings.preview_settings.profiles[index].quality || 80;
                this.config.video_settings.preview_settings.profiles[index].loop = this.config.video_settings.preview_settings.profiles[index].loop !== false;
                this.config.video_settings.preview_settings.profiles[index].optimize = this.config.video_settings.preview_settings.profiles[index].optimize !== false;
            }
            
            // Regenerate fields
            container.innerHTML = this.generatePreviewFormatFields(this.config.video_settings.preview_settings.profiles[index], index);
            this.markDirty();
        }
    }

    createThumbnailProfileCard(profile, index) {
        const card = document.createElement('div');
        card.className = 'profile-card';
        card.innerHTML = `
            <div class="profile-header">
                <div class="profile-title">${profile.name || `Thumbnail Profile ${index + 1}`}</div>
                <div class="profile-actions">
                    <button type="button" class="btn btn-sm btn-secondary" onclick="configBuilder.duplicateThumbnailProfile(${index})">
                        <i class="fas fa-copy"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-warning" onclick="configBuilder.removeThumbnailProfile(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="profile-fields">
                <!-- Profile Name (full width) -->
                <div class="form-grid">
                    <div class="form-group">
                        <label>Profile Name</label>
                        <input type="text" data-path="video_settings.thumbnail_settings.profiles.${index}.name" 
                               value="${profile.name || ''}" placeholder="e.g., medium_thumb">
                    </div>
                </div>

                <!-- Dimensions & Format (3 columns) -->
                <div class="form-grid-3">
                    <div class="form-group">
                        <label>Width</label>
                        <input type="number" data-path="video_settings.thumbnail_settings.profiles.${index}.width" 
                               value="${profile.width || 640}" min="64" max="3840">
                    </div>
                    <div class="form-group">
                        <label>Height</label>
                        <input type="number" data-path="video_settings.thumbnail_settings.profiles.${index}.height" 
                               value="${profile.height || 360}" min="64" max="2160">
                    </div>
                    <div class="form-group">
                        <label>Format</label>
                        <select data-path="video_settings.thumbnail_settings.profiles.${index}.format">
                            <option value="jpg" ${profile.format === 'jpg' ? 'selected' : ''}>JPEG</option>
                            <option value="png" ${profile.format === 'png' ? 'selected' : ''}>PNG</option>
                            <option value="webp" ${profile.format === 'webp' ? 'selected' : ''}>WebP</option>
                        </select>
                    </div>
                </div>

                <!-- Quality & Options (2 columns) -->
                <div class="form-grid-2">
                    <div class="form-group">
                        <label>Quality</label>
                        <input type="number" data-path="video_settings.thumbnail_settings.profiles.${index}.quality" 
                               value="${profile.quality || 90}" min="1" max="100">
                    </div>
                    <div class="form-group">
                        <label class="toggle-switch">
                            <input type="checkbox" data-path="video_settings.thumbnail_settings.profiles.${index}.maintain_aspect_ratio" 
                                   ${profile.maintain_aspect_ratio !== false ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">Maintain Aspect Ratio</span>
                        </label>
                    </div>
                </div>
            </div>
        `;
        return card;
    }

    generateVideoProfileFields(profile, index) {
        return `
            <!-- Profile Name (full width) -->
            <div class="form-grid">
                <div class="form-group">
                    <label>Profile Name</label>
                    <input type="text" data-path="video_settings.transcode_profiles.${index}.name" 
                           value="${profile.name || ''}" placeholder="e.g., 720p_medium">
                </div>
            </div>

            <!-- Dimensions & Format (4 columns) -->
            <div class="form-grid-4">
                <div class="form-group">
                    <label>Width</label>
                    <input type="number" data-path="video_settings.transcode_profiles.${index}.width" 
                           value="${profile.width || 1280}" min="64" max="7680">
                </div>
                <div class="form-group">
                    <label>Height</label>
                    <input type="number" data-path="video_settings.transcode_profiles.${index}.height" 
                           value="${profile.height || 720}" min="64" max="4320">
                </div>
                <div class="form-group">
                    <label>Format</label>
                    <select data-path="video_settings.transcode_profiles.${index}.format">
                        <option value="mp4" ${profile.format === 'mp4' ? 'selected' : ''}>MP4</option>
                        <option value="webm" ${profile.format === 'webm' ? 'selected' : ''}>WebM</option>
                        <option value="mov" ${profile.format === 'mov' ? 'selected' : ''}>MOV</option>
                        <option value="mkv" ${profile.format === 'mkv' ? 'selected' : ''}>MKV</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>FPS</label>
                    <input type="number" data-path="video_settings.transcode_profiles.${index}.fps" 
                           value="${profile.fps || ''}" min="1" max="120" placeholder="Auto">
                </div>
            </div>

            <!-- Video Encoding (4 columns) -->
            <div class="form-grid-4">
                <div class="form-group">
                    <label>Codec</label>
                    <select data-path="video_settings.transcode_profiles.${index}.codec">
                        <option value="libx264" ${profile.codec === 'libx264' ? 'selected' : ''}>H.264</option>
                        <option value="libx265" ${profile.codec === 'libx265' ? 'selected' : ''}>H.265</option>
                        <option value="libvpx-vp9" ${profile.codec === 'libvpx-vp9' ? 'selected' : ''}>VP9</option>
                        <option value="h264_nvenc" ${profile.codec === 'h264_nvenc' ? 'selected' : ''}>H.264 NVENC</option>
                        <option value="hevc_nvenc" ${profile.codec === 'hevc_nvenc' ? 'selected' : ''}>H.265 NVENC</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Preset</label>
                    <select data-path="video_settings.transcode_profiles.${index}.preset">
                        <option value="ultrafast" ${profile.preset === 'ultrafast' ? 'selected' : ''}>Ultra Fast</option>
                        <option value="fast" ${profile.preset === 'fast' ? 'selected' : ''}>Fast</option>
                        <option value="medium" ${profile.preset === 'medium' ? 'selected' : ''}>Medium</option>
                        <option value="slow" ${profile.preset === 'slow' ? 'selected' : ''}>Slow</option>
                        <option value="veryslow" ${profile.preset === 'veryslow' ? 'selected' : ''}>Very Slow</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>CRF (Quality)</label>
                    <input type="number" data-path="video_settings.transcode_profiles.${index}.crf" 
                           value="${profile.crf || 23}" min="0" max="51" step="1">
                </div>
                <div class="form-group">
                    <label>Bitrate</label>
                    <input type="text" data-path="video_settings.transcode_profiles.${index}.bitrate" 
                           value="${profile.bitrate || ''}" placeholder="Auto">
                </div>
            </div>

            <!-- Audio Settings (4 columns) -->
            <div class="form-grid-4">
                <div class="form-group">
                    <label>Audio Codec</label>
                    <select data-path="video_settings.transcode_profiles.${index}.audio_codec">
                        <option value="aac" ${profile.audio_codec === 'aac' ? 'selected' : ''}>AAC</option>
                        <option value="libopus" ${profile.audio_codec === 'libopus' ? 'selected' : ''}>Opus</option>
                        <option value="mp3" ${profile.audio_codec === 'mp3' ? 'selected' : ''}>MP3</option>
                        <option value="copy" ${profile.audio_codec === 'copy' ? 'selected' : ''}>Copy</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Audio Bitrate</label>
                    <select data-path="video_settings.transcode_profiles.${index}.audio_bitrate">
                        <option value="64k" ${profile.audio_bitrate === '64k' ? 'selected' : ''}>64k</option>
                        <option value="96k" ${profile.audio_bitrate === '96k' ? 'selected' : ''}>96k</option>
                        <option value="128k" ${profile.audio_bitrate === '128k' ? 'selected' : ''}>128k</option>
                        <option value="192k" ${profile.audio_bitrate === '192k' ? 'selected' : ''}>192k</option>
                        <option value="256k" ${profile.audio_bitrate === '256k' ? 'selected' : ''}>256k</option>
                        <option value="320k" ${profile.audio_bitrate === '320k' ? 'selected' : ''}>320k</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Audio Channels</label>
                    <select data-path="video_settings.transcode_profiles.${index}.audio_channels">
                        <option value="1" ${profile.audio_channels == 1 ? 'selected' : ''}>Mono</option>
                        <option value="2" ${profile.audio_channels == 2 ? 'selected' : ''}>Stereo</option>
                        <option value="6" ${profile.audio_channels == 6 ? 'selected' : ''}>5.1</option>
                        <option value="8" ${profile.audio_channels == 8 ? 'selected' : ''}>7.1</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="toggle-switch">
                        <input type="checkbox" data-path="video_settings.transcode_profiles.${index}.use_gpu" 
                               ${profile.use_gpu !== false ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                        <span class="toggle-label">Use GPU</span>
                    </label>
                </div>
            </div>
        `;
    }

    setupAddProfileButtons() {
        // Add video profile button
        document.getElementById('addVideoProfileBtn')?.addEventListener('click', () => {
            this.addVideoProfile();
        });

        // Add preview profile button  
        document.getElementById('addPreviewProfileBtn')?.addEventListener('click', () => {
            this.addPreviewProfile();
        });

        // Add thumbnail profile button
        document.getElementById('addThumbnailProfileBtn')?.addEventListener('click', () => {
            this.addThumbnailProfile();
        });
    }

    addVideoProfile() {
        if (!this.config.video_settings) {
            this.config.video_settings = { _enabled: true, transcode_profiles: [] };
        }
        if (!this.config.video_settings.transcode_profiles) {
            this.config.video_settings.transcode_profiles = [];
        }

        const newProfile = {
            _id: this.generateId(),
            name: `profile_${this.config.video_settings.transcode_profiles.length + 1}`,
            enabled: true,
            width: 1280,
            height: 720,
            codec: 'libx264',
            preset: 'medium',
            crf: 23,
            format: 'mp4',
            audio_codec: 'aac',
            audio_bitrate: '128k',
            use_gpu: true
        };

        this.config.video_settings.transcode_profiles.push(newProfile);
        this.loadVideoProfiles();
        this.markDirty();
    }

    removeVideoProfile(index) {
        if (confirm('Are you sure you want to remove this video profile?')) {
            this.config.video_settings.transcode_profiles.splice(index, 1);
            this.loadVideoProfiles();
            this.markDirty();
        }
    }

    duplicateVideoProfile(index) {
        const originalProfile = this.config.video_settings.transcode_profiles[index];
        const duplicatedProfile = JSON.parse(JSON.stringify(originalProfile));
        duplicatedProfile._id = this.generateId();
        duplicatedProfile.name = `${originalProfile.name}_copy`;
        
        this.config.video_settings.transcode_profiles.push(duplicatedProfile);
        this.loadVideoProfiles();
        this.markDirty();
    }

    addPreviewProfile() {
        if (!this.config.video_settings) {
            this.config.video_settings = { _enabled: true };
        }
        if (!this.config.video_settings.preview_settings) {
            this.config.video_settings.preview_settings = { _enabled: true, profiles: [] };
        }
        if (!this.config.video_settings.preview_settings.profiles) {
            this.config.video_settings.preview_settings.profiles = [];
        }

        const newProfile = {
            _id: this.generateId(),
            name: `preview_${this.config.video_settings.preview_settings.profiles.length + 1}`,
            enabled: true,
            start: 0,
            end: 5,
            width: 640,
            height: 360,
            format: 'gif',
            // GIF specific defaults
            fps: 12,
            quality: 80,
            loop: true,
            optimize: true,
            dither: 'sierra2_4a',
            palette_size: 256
        };

        this.config.video_settings.preview_settings.profiles.push(newProfile);
        this.loadPreviewProfiles();
        this.markDirty();
    }

    removePreviewProfile(index) {
        if (confirm('Are you sure you want to remove this preview profile?')) {
            this.config.video_settings.preview_settings.profiles.splice(index, 1);
            this.loadPreviewProfiles();
            this.markDirty();
        }
    }

    duplicatePreviewProfile(index) {
        const originalProfile = this.config.video_settings.preview_settings.profiles[index];
        const duplicatedProfile = JSON.parse(JSON.stringify(originalProfile));
        duplicatedProfile._id = this.generateId();
        duplicatedProfile.name = `${originalProfile.name}_copy`;
        
        this.config.video_settings.preview_settings.profiles.push(duplicatedProfile);
        this.loadPreviewProfiles();
        this.markDirty();
    }

    addThumbnailProfile() {
        if (!this.config.video_settings) {
            this.config.video_settings = { _enabled: true };
        }
        if (!this.config.video_settings.thumbnail_settings) {
            this.config.video_settings.thumbnail_settings = { _enabled: true, profiles: [] };
        }
        if (!this.config.video_settings.thumbnail_settings.profiles) {
            this.config.video_settings.thumbnail_settings.profiles = [];
        }

        const newProfile = {
            _id: this.generateId(),
            name: `thumbnail_${this.config.video_settings.thumbnail_settings.profiles.length + 1}`,
            enabled: true,
            width: 640,
            height: 360,
            format: 'jpg',
            quality: 90,
            maintain_aspect_ratio: true,
            crop_mode: 'center'
        };

        this.config.video_settings.thumbnail_settings.profiles.push(newProfile);
        this.loadThumbnailProfiles();
        this.markDirty();
    }

    removeThumbnailProfile(index) {
        if (confirm('Are you sure you want to remove this thumbnail profile?')) {
            this.config.video_settings.thumbnail_settings.profiles.splice(index, 1);
            this.loadThumbnailProfiles();
            this.markDirty();
        }
    }

    duplicateThumbnailProfile(index) {
        const originalProfile = this.config.video_settings.thumbnail_settings.profiles[index];
        const duplicatedProfile = JSON.parse(JSON.stringify(originalProfile));
        duplicatedProfile._id = this.generateId();
        duplicatedProfile.name = `${originalProfile.name}_copy`;
        
        this.config.video_settings.thumbnail_settings.profiles.push(duplicatedProfile);
        this.loadThumbnailProfiles();
        this.markDirty();
    }

    loadImageSettingsSection() {
        console.log('Loading image settings section');
        this.loadImageProfiles();
        this.loadImageThumbnailProfiles();
        this.setupImageEventListeners();
    }

    loadImageProfiles() {
        const container = document.getElementById('imageProfilesContainer');
        if (!container) return;

        container.innerHTML = '';
        
        const profiles = this.config.image_settings?.transcode_profiles || [];
        profiles.forEach((profile, index) => {
            const profileCard = this.createImageProfileCard(profile, index);
            container.appendChild(profileCard);
        });

        if (profiles.length === 0) {
            container.innerHTML = '<p class="text-muted">No image profiles configured. Click "Add Profile" to create one.</p>';
        }

        this.updateProfileCount('image-profiles-count', profiles.length);
    }

    loadImageThumbnailProfiles() {
        const container = document.getElementById('imageThumbnailContainer');
        if (!container) return;

        container.innerHTML = '';
        
        const profiles = this.config.image_settings?.thumbnail_profiles || [];
        profiles.forEach((profile, index) => {
            const profileCard = this.createImageThumbnailCard(profile, index);
            container.appendChild(profileCard);
        });

        if (profiles.length === 0) {
            container.innerHTML = '<p class="text-muted">No image thumbnail profiles configured. Click "Add Thumbnail Profile" to create one.</p>';
        }
    }

    createImageProfileCard(profile, index) {
        const card = document.createElement('div');
        card.className = 'profile-card';
        card.innerHTML = `
            <div class="profile-header">
                <div class="profile-title">${profile.name || `Image Profile ${index + 1}`}</div>
                <div class="profile-actions">
                    <button type="button" class="btn btn-sm btn-secondary" onclick="configBuilder.duplicateImageProfile(${index})">
                        <i class="fas fa-copy"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-warning" onclick="configBuilder.removeImageProfile(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="profile-fields">
                <!-- Profile Name (full width) -->
                <div class="form-grid">
                    <div class="form-group">
                        <label>Profile Name</label>
                        <input type="text" data-path="image_settings.transcode_profiles.${index}.name" 
                               value="${profile.name || ''}" placeholder="e.g., webp_high_quality">
                    </div>
                </div>

                <!-- Format & Quality (4 columns) -->
                <div class="form-grid-4">
                    <div class="form-group">
                        <label>Format</label>
                        <select data-path="image_settings.transcode_profiles.${index}.format">
                            <option value="webp" ${profile.format === 'webp' ? 'selected' : ''}>WebP</option>
                            <option value="avif" ${profile.format === 'avif' ? 'selected' : ''}>AVIF</option>
                            <option value="jpg" ${profile.format === 'jpg' ? 'selected' : ''}>JPEG</option>
                            <option value="png" ${profile.format === 'png' ? 'selected' : ''}>PNG</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Quality</label>
                        <input type="number" data-path="image_settings.transcode_profiles.${index}.quality" 
                               value="${profile.quality || 85}" min="1" max="100">
                    </div>
                    <div class="form-group">
                        <label>Compression Level</label>
                        <input type="number" data-path="image_settings.transcode_profiles.${index}.compression_level" 
                               value="${profile.compression_level || 6}" min="0" max="9">
                    </div>
                    <div class="form-group">
                        <label class="toggle-switch">
                            <input type="checkbox" data-path="image_settings.transcode_profiles.${index}.resize" 
                                   ${profile.resize ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">Enable Resize</span>
                        </label>
                    </div>
                </div>

                <!-- Dimensions (4 columns) -->
                <div class="form-grid-4">
                    <div class="form-group">
                        <label>Width (optional)</label>
                        <input type="number" data-path="image_settings.transcode_profiles.${index}.width" 
                               value="${profile.width || ''}" min="1" placeholder="Original">
                    </div>
                    <div class="form-group">
                        <label>Height (optional)</label>
                        <input type="number" data-path="image_settings.transcode_profiles.${index}.height" 
                               value="${profile.height || ''}" min="1" placeholder="Original">
                    </div>
                    <div class="form-group">
                        <label>Crop Mode</label>
                        <select data-path="image_settings.transcode_profiles.${index}.crop_mode">
                            <option value="center" ${profile.crop_mode === 'center' ? 'selected' : ''}>Center</option>
                            <option value="top" ${profile.crop_mode === 'top' ? 'selected' : ''}>Top</option>
                            <option value="bottom" ${profile.crop_mode === 'bottom' ? 'selected' : ''}>Bottom</option>
                            <option value="left" ${profile.crop_mode === 'left' ? 'selected' : ''}>Left</option>
                            <option value="right" ${profile.crop_mode === 'right' ? 'selected' : ''}>Right</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Background Fill</label>
                        <input type="text" data-path="image_settings.transcode_profiles.${index}.background_fill" 
                               value="${profile.background_fill || 'white'}" placeholder="white">
                    </div>
                </div>

                <!-- Options (4 columns) -->
                <div class="form-grid-4">
                    <div class="form-group">
                        <label class="toggle-switch">
                            <input type="checkbox" data-path="image_settings.transcode_profiles.${index}.maintain_aspect_ratio" 
                                   ${profile.maintain_aspect_ratio !== false ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">Maintain Aspect</span>
                        </label>
                    </div>
                    <div class="form-group">
                        <label class="toggle-switch">
                            <input type="checkbox" data-path="image_settings.transcode_profiles.${index}.optimize" 
                                   ${profile.optimize !== false ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">Optimize Size</span>
                        </label>
                    </div>
                    <div class="form-group">
                        <label class="toggle-switch">
                            <input type="checkbox" data-path="image_settings.transcode_profiles.${index}.progressive" 
                                   ${profile.progressive ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">Progressive</span>
                        </label>
                    </div>
                    <div class="form-group">
                        <label class="toggle-switch">
                            <input type="checkbox" data-path="image_settings.transcode_profiles.${index}.strip_metadata" 
                                   ${profile.strip_metadata ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">Strip Metadata</span>
                        </label>
                    </div>
                </div>
            </div>
        `;
        return card;
    }

    createImageThumbnailCard(profile, index) {
        const card = document.createElement('div');
        card.className = 'profile-card';
        card.innerHTML = `
            <div class="profile-header">
                <div class="profile-title">${profile.name || `Image Thumbnail ${index + 1}`}</div>
                <div class="profile-actions">
                    <button type="button" class="btn btn-sm btn-secondary" onclick="configBuilder.duplicateImageThumbnailProfile(${index})">
                        <i class="fas fa-copy"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-warning" onclick="configBuilder.removeImageThumbnailProfile(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="profile-fields">
                <!-- Profile Name (full width) -->
                <div class="form-grid">
                    <div class="form-group">
                        <label>Profile Name</label>
                        <input type="text" data-path="image_settings.thumbnail_profiles.${index}.name" 
                               value="${profile.name || ''}" placeholder="e.g., thumb_320">
                    </div>
                </div>

                <!-- Dimensions & Format (4 columns) -->
                <div class="form-grid-4">
                    <div class="form-group">
                        <label>Width</label>
                        <input type="number" data-path="image_settings.thumbnail_profiles.${index}.width" 
                               value="${profile.width || 320}" min="32" max="2048">
                    </div>
                    <div class="form-group">
                        <label>Height</label>
                        <input type="number" data-path="image_settings.thumbnail_profiles.${index}.height" 
                               value="${profile.height || 240}" min="32" max="2048">
                    </div>
                    <div class="form-group">
                        <label>Format</label>
                        <select data-path="image_settings.thumbnail_profiles.${index}.format">
                            <option value="webp" ${profile.format === 'webp' ? 'selected' : ''}>WebP</option>
                            <option value="jpg" ${profile.format === 'jpg' ? 'selected' : ''}>JPEG</option>
                            <option value="png" ${profile.format === 'png' ? 'selected' : ''}>PNG</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Quality</label>
                        <input type="number" data-path="image_settings.thumbnail_profiles.${index}.quality" 
                               value="${profile.quality || 85}" min="1" max="100">
                    </div>
                </div>

                <!-- Options (4 columns) -->
                <div class="form-grid-4">
                    <div class="form-group">
                        <label>Crop Mode</label>
                        <select data-path="image_settings.thumbnail_profiles.${index}.crop_mode">
                            <option value="center" ${profile.crop_mode === 'center' ? 'selected' : ''}>Center</option>
                            <option value="top" ${profile.crop_mode === 'top' ? 'selected' : ''}>Top</option>
                            <option value="bottom" ${profile.crop_mode === 'bottom' ? 'selected' : ''}>Bottom</option>
                            <option value="left" ${profile.crop_mode === 'left' ? 'selected' : ''}>Left</option>
                            <option value="right" ${profile.crop_mode === 'right' ? 'selected' : ''}>Right</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Background Fill</label>
                        <input type="text" data-path="image_settings.thumbnail_profiles.${index}.background_fill" 
                               value="${profile.background_fill || 'white'}" placeholder="white">
                    </div>
                    <div class="form-group">
                        <label class="toggle-switch">
                            <input type="checkbox" data-path="image_settings.thumbnail_profiles.${index}.maintain_aspect_ratio" 
                                   ${profile.maintain_aspect_ratio !== false ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">Maintain Aspect</span>
                        </label>
                    </div>
                    <div class="form-group">
                        <label class="toggle-switch">
                            <input type="checkbox" data-path="image_settings.thumbnail_profiles.${index}.upscale" 
                                   ${profile.upscale ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">Allow Upscale</span>
                        </label>
                    </div>
                </div>
            </div>
        `;
        return card;
    }

    setupImageEventListeners() {
        // Add image profile button
        document.getElementById('addImageProfileBtn')?.addEventListener('click', () => {
            this.addImageProfile();
        });

        // Add image thumbnail button
        document.getElementById('addImageThumbnailBtn')?.addEventListener('click', () => {
            this.addImageThumbnailProfile();
        });

        // Image enabled toggle
        document.getElementById('imageEnabled')?.addEventListener('change', (e) => {
            if (!this.config.image_settings) this.config.image_settings = {};
            this.config.image_settings._enabled = e.target.checked;
            this.toggleImageSettings(e.target.checked);
            this.markDirty();
        });

    }

    toggleImageSettings(enabled) {
        const container = document.getElementById('imageSettingsContainer');
        if (container) {
            container.style.display = enabled ? 'block' : 'none';
        }
    }


    addImageProfile() {
        if (!this.config.image_settings) {
            this.config.image_settings = { _enabled: true, transcode_profiles: [] };
        }
        if (!this.config.image_settings.transcode_profiles) {
            this.config.image_settings.transcode_profiles = [];
        }

        const newProfile = {
            _id: this.generateId(),
            name: `image_profile_${this.config.image_settings.transcode_profiles.length + 1}`,
            enabled: true,
            format: 'webp',
            quality: 85,
            resize: false,
            maintain_aspect_ratio: true,
            optimize: true
        };

        this.config.image_settings.transcode_profiles.push(newProfile);
        this.loadImageProfiles();
        this.markDirty();
    }

    removeImageProfile(index) {
        if (confirm('Are you sure you want to remove this image profile?')) {
            this.config.image_settings.transcode_profiles.splice(index, 1);
            this.loadImageProfiles();
            this.markDirty();
        }
    }

    duplicateImageProfile(index) {
        const originalProfile = this.config.image_settings.transcode_profiles[index];
        const duplicatedProfile = JSON.parse(JSON.stringify(originalProfile));
        duplicatedProfile._id = this.generateId();
        duplicatedProfile.name = `${originalProfile.name}_copy`;
        
        this.config.image_settings.transcode_profiles.push(duplicatedProfile);
        this.loadImageProfiles();
        this.markDirty();
    }

    addImageThumbnailProfile() {
        if (!this.config.image_settings) {
            this.config.image_settings = { _enabled: true };
        }
        if (!this.config.image_settings.thumbnail_profiles) {
            this.config.image_settings.thumbnail_profiles = [];
        }

        const newProfile = {
            _id: this.generateId(),
            name: `thumb_${this.config.image_settings.thumbnail_profiles.length + 1}`,
            enabled: true,
            width: 320,
            height: 240,
            format: 'webp',
            quality: 85,
            maintain_aspect_ratio: true
        };

        this.config.image_settings.thumbnail_profiles.push(newProfile);
        this.loadImageThumbnailProfiles();
        this.markDirty();
    }

    removeImageThumbnailProfile(index) {
        if (confirm('Are you sure you want to remove this image thumbnail profile?')) {
            this.config.image_settings.thumbnail_profiles.splice(index, 1);
            this.loadImageThumbnailProfiles();
            this.markDirty();
        }
    }

    duplicateImageThumbnailProfile(index) {
        const originalProfile = this.config.image_settings.thumbnail_profiles[index];
        const duplicatedProfile = JSON.parse(JSON.stringify(originalProfile));
        duplicatedProfile._id = this.generateId();
        duplicatedProfile.name = `${originalProfile.name}_copy`;
        
        this.config.image_settings.thumbnail_profiles.push(duplicatedProfile);
        this.loadImageThumbnailProfiles();
        this.markDirty();
    }

    loadFaceDetectionSection() {
        console.log('Loading face detection section');
        this.setupFaceDetectionEventListeners();
        this.loadFaceDetectionSettings();
    }

    setupFaceDetectionEventListeners() {
        // Face detection enabled toggle
        document.getElementById('faceDetectionEnabled')?.addEventListener('change', (e) => {
            if (!this.config.face_detection) this.config.face_detection = { enabled: false };
            this.config.face_detection.enabled = e.target.checked;
            this.toggleFaceDetectionSettings(e.target.checked);
            this.markDirty();
        });
    }

    toggleFaceDetectionSettings(enabled) {
        const container = document.getElementById('faceDetectionContainer');
        if (container) {
            container.style.display = enabled ? 'block' : 'none';
        }
        
        if (enabled) {
            this.loadFaceDetectionSettings();
        }
    }

    loadFaceDetectionSettings() {
        const container = document.getElementById('faceDetectionContainer');
        if (!container) return;

        const faceConfig = this.config.face_detection?.config || {};
        
        container.innerHTML = `
            <div class="settings-group">
                <div class="group-header">
                    <h3><i class="fas fa-cog"></i> Detection Settings</h3>
                </div>
                <div class="profiles-container">
                    <div class="form-grid">
                        <div class="form-group">
                            <label>Model Version</label>
                            <select data-path="face_detection.config.model_version">
                                <option value="v1.0" ${faceConfig.model_version === 'v1.0' ? 'selected' : ''}>v1.0</option>
                                <option value="v2.0" ${faceConfig.model_version === 'v2.0' ? 'selected' : ''}>v2.0 (Recommended)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Similarity Threshold</label>
                            <input type="number" data-path="face_detection.config.similarity_threshold" 
                                   value="${faceConfig.similarity_threshold || 0.7}" min="0" max="1" step="0.1">
                            <small class="form-help">Higher values = stricter face matching</small>
                        </div>
                        <div class="form-group">
                            <label>Min Faces in Group</label>
                            <input type="number" data-path="face_detection.config.min_faces_in_group" 
                                   value="${faceConfig.min_faces_in_group || 3}" min="1" max="20">
                        </div>
                        <div class="form-group">
                            <label>Sample Interval (seconds)</label>
                            <input type="number" data-path="face_detection.config.sample_interval" 
                                   value="${faceConfig.sample_interval || 5}" min="0.1" step="0.1">
                        </div>
                        <div class="form-group">
                            <label>Max Faces Per Frame</label>
                            <input type="number" data-path="face_detection.config.max_faces_per_frame" 
                                   value="${faceConfig.max_faces_per_frame || 20}" min="1" max="100">
                        </div>
                        <div class="form-group">
                            <label>Output Path</label>
                            <input type="text" data-path="face_detection.config.output_path" 
                                   value="${faceConfig.output_path || './output/faces'}" placeholder="./output/faces">
                        </div>
                    </div>
                </div>
            </div>

            <div class="settings-group">
                <div class="group-header">
                    <h3><i class="fas fa-chart-bar"></i> Analysis Options</h3>
                </div>
                <div class="profiles-container">
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="toggle-switch">
                                <input type="checkbox" data-path="face_detection.config.generate_face_embeddings" 
                                       ${faceConfig.generate_face_embeddings !== false ? 'checked' : ''}>
                                <span class="toggle-slider"></span>
                                <span class="toggle-label">Generate Face Embeddings</span>
                            </label>
                        </div>
                        <div class="form-group">
                            <label class="toggle-switch">
                                <input type="checkbox" data-path="face_detection.config.save_face_crops" 
                                       ${faceConfig.save_face_crops !== false ? 'checked' : ''}>
                                <span class="toggle-slider"></span>
                                <span class="toggle-label">Save Face Crops</span>
                            </label>
                        </div>
                        <div class="form-group">
                            <label class="toggle-switch">
                                <input type="checkbox" data-path="face_detection.config.detailed_analysis.age_estimation" 
                                       ${faceConfig.detailed_analysis?.age_estimation ? 'checked' : ''}>
                                <span class="toggle-slider"></span>
                                <span class="toggle-label">Age Estimation</span>
                            </label>
                        </div>
                        <div class="form-group">
                            <label class="toggle-switch">
                                <input type="checkbox" data-path="face_detection.config.detailed_analysis.gender_classification" 
                                       ${faceConfig.detailed_analysis?.gender_classification ? 'checked' : ''}>
                                <span class="toggle-slider"></span>
                                <span class="toggle-label">Gender Classification</span>
                            </label>
                        </div>
                        <div class="form-group">
                            <label class="toggle-switch">
                                <input type="checkbox" data-path="face_detection.config.detailed_analysis.emotion_detection" 
                                       ${faceConfig.detailed_analysis?.emotion_detection ? 'checked' : ''}>
                                <span class="toggle-slider"></span>
                                <span class="toggle-label">Emotion Detection</span>
                            </label>
                        </div>
                        <div class="form-group">
                            <label class="toggle-switch">
                                <input type="checkbox" data-path="face_detection.config.detailed_analysis.face_quality_score" 
                                       ${faceConfig.detailed_analysis?.face_quality_score !== false ? 'checked' : ''}>
                                <span class="toggle-slider"></span>
                                <span class="toggle-label">Face Quality Score</span>
                            </label>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    loadOutputSettingsSection() {
        console.log('Loading output settings section');
        this.loadOutputSettings();
    }

    loadOutputSettings() {
        const container = document.querySelector('#output-settings-section .settings-container');
        if (!container) return;

        const outputConfig = this.config.output_settings || {};
        
        container.innerHTML = `
            <div class="settings-group">
                <div class="group-header">
                    <h3><i class="fas fa-cloud"></i> Storage Settings</h3>
                </div>
                <div class="profiles-container">
                    <div class="form-grid">
                        <div class="form-group">
                            <label>S3 Bucket</label>
                            <input type="text" data-path="output_settings.storage.s3_bucket" 
                                   value="${outputConfig.storage?.s3_bucket || ''}" placeholder="my-transcode-bucket">
                        </div>
                        <div class="form-group">
                            <label>S3 Region</label>
                            <select data-path="output_settings.storage.s3_region">
                                <option value="us-east-1" ${outputConfig.storage?.s3_region === 'us-east-1' ? 'selected' : ''}>US East (N. Virginia)</option>
                                <option value="us-west-2" ${outputConfig.storage?.s3_region === 'us-west-2' ? 'selected' : ''}>US West (Oregon)</option>
                                <option value="eu-west-1" ${outputConfig.storage?.s3_region === 'eu-west-1' ? 'selected' : ''}>Europe (Ireland)</option>
                                <option value="ap-southeast-1" ${outputConfig.storage?.s3_region === 'ap-southeast-1' ? 'selected' : ''}>Asia Pacific (Singapore)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Folder Structure</label>
                            <input type="text" data-path="output_settings.storage.folder_structure" 
                                   value="${outputConfig.storage?.folder_structure || '{user_id}/{job_id}/{type}/{profile_name}/'}" 
                                   placeholder="{user_id}/{job_id}/{type}/{profile_name}/">
                            <small class="form-help">Use {user_id}, {job_id}, {type}, {profile_name} placeholders</small>
                        </div>
                        <div class="form-group">
                            <label class="toggle-switch">
                                <input type="checkbox" data-path="output_settings.storage.generate_unique_filenames" 
                                       ${outputConfig.storage?.generate_unique_filenames !== false ? 'checked' : ''}>
                                <span class="toggle-slider"></span>
                                <span class="toggle-label">Generate Unique Filenames</span>
                            </label>
                        </div>
                        <div class="form-group">
                            <label class="toggle-switch">
                                <input type="checkbox" data-path="output_settings.storage.delete_local_after_upload" 
                                       ${outputConfig.storage?.delete_local_after_upload !== false ? 'checked' : ''}>
                                <span class="toggle-slider"></span>
                                <span class="toggle-label">Delete Local Files After Upload</span>
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            <div class="settings-group">
                <div class="group-header">
                    <h3><i class="fas fa-bell"></i> Notifications</h3>
                </div>
                <div class="profiles-container">
                    <div class="form-grid">
                        <div class="form-group">
                            <label>Webhook URL</label>
                            <input type="url" data-path="output_settings.notifications.webhook_url" 
                                   value="${outputConfig.notifications?.webhook_url || ''}" 
                                   placeholder="https://your-app.com/webhook">
                        </div>
                        <div class="form-group">
                            <label class="toggle-switch">
                                <input type="checkbox" data-path="output_settings.notifications.include_processing_stats" 
                                       ${outputConfig.notifications?.include_processing_stats !== false ? 'checked' : ''}>
                                <span class="toggle-slider"></span>
                                <span class="toggle-label">Include Processing Stats</span>
                            </label>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    updateConfigFromForm() {
        // Update config object from form fields
        document.querySelectorAll('[data-path]').forEach(field => {
            const path = field.dataset.path;
            let value = this.getFieldValue(field);
            
            // Special handling for tags - convert comma-separated string to array
            if (path === 'tags' && typeof value === 'string') {
                value = value.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0);
            }
            
            this.setConfigValue(path, value);
        });

        // Auto-update timestamps
        this.config.updated_at = new Date().toISOString();
        if (!this.config.created_at) {
            this.config.created_at = new Date().toISOString();
        }

        // Update timestamp display fields
        const createdAtField = document.getElementById('createdAt');
        const updatedAtField = document.getElementById('updatedAt');
        if (createdAtField) createdAtField.value = this.config.created_at;
        if (updatedAtField) updatedAtField.value = this.config.updated_at;

        // Update JSON editor if in JSON mode
        if (this.currentMode === 'json') {
            this.updateJsonEditor();
        }

        // Update summary
        this.updateSummary();
    }

    populateFormFromConfig() {
        // Populate basic form fields
        document.querySelectorAll('[data-path]').forEach(field => {
            const path = field.dataset.path;
            let value = this.getConfigValue(path);
            
            // Special handling for tags - convert array to comma-separated string
            if (path === 'tags' && Array.isArray(value)) {
                value = value.join(', ');
            }
            
            if (value !== undefined) {
                this.setFieldValue(field.id || field.name, value);
            }
        });

        // Populate complex sections (profiles, etc.)
        this.populateVideoProfiles();
        this.populateImageProfiles();
        this.populateFaceDetectionSettings();
        this.populateOutputSettings();

        // Update summary and navigation
        this.updateSummary();
        this.updateProgress();
    }

    populateVideoProfiles() {
        // TODO: Implement video profiles population
        const videoProfiles = this.config?.video_settings?.transcode_profiles || [];
        console.log('Populating video profiles:', videoProfiles);
    }

    populateImageProfiles() {
        // TODO: Implement image profiles population
        const imageProfiles = this.config?.image_settings?.transcode_profiles || [];
        console.log('Populating image profiles:', imageProfiles);
    }

    populateFaceDetectionSettings() {
        // TODO: Implement face detection settings population
        const faceDetection = this.config?.face_detection || {};
        console.log('Populating face detection settings:', faceDetection);
        
        // Set the main toggle
        const faceDetectionEnabled = document.getElementById('faceDetectionEnabled');
        if (faceDetectionEnabled) {
            faceDetectionEnabled.checked = faceDetection.enabled || false;
        }
    }

    populateOutputSettings() {
        // TODO: Implement output settings population
        const outputSettings = this.config?.output_settings || {};
        console.log('Populating output settings:', outputSettings);
    }

    getFieldValue(field) {
        if (field.type === 'checkbox') {
            return field.checked;
        } else if (field.type === 'number') {
            return parseFloat(field.value) || 0;
        } else {
            return field.value;
        }
    }

    setFieldValue(fieldId, value) {
        const field = document.getElementById(fieldId);
        if (field) {
            if (field.type === 'checkbox') {
                field.checked = Boolean(value);
            } else {
                field.value = value || '';
            }
        }
    }

    setConfigValue(path, value) {
        const keys = path.split('.');
        let obj = this.config;
        
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i];
            if (!obj[key]) {
                obj[key] = {};
            }
            obj = obj[key];
        }
        
        obj[keys[keys.length - 1]] = value;
    }

    getConfigValue(path) {
        const keys = path.split('.');
        let obj = this.config;
        
        for (const key of keys) {
            if (obj && typeof obj === 'object' && key in obj) {
                obj = obj[key];
            } else {
                return undefined;
            }
        }
        
        return obj;
    }

    updateNavigationButtons() {
        const prevBtn = document.getElementById('prevSectionBtn');
        const nextBtn = document.getElementById('nextSectionBtn');
        
        if (prevBtn) {
            prevBtn.disabled = this.currentSection === 0;
        }
        
        if (nextBtn) {
            nextBtn.disabled = this.currentSection >= this.sections.length - 1;
            nextBtn.innerHTML = this.currentSection >= this.sections.length - 1 
                ? '<i class="fas fa-check"></i> Complete' 
                : 'Next <i class="fas fa-chevron-right"></i>';
        }
    }

    previousSection() {
        if (this.currentSection > 0) {
            this.currentSection--;
            this.loadSection(this.sections[this.currentSection]);
        }
    }

    nextSection() {
        if (this.currentSection < this.sections.length - 1) {
            this.currentSection++;
            this.loadSection(this.sections[this.currentSection]);
        }
    }

    updateProgress() {
        const completedSections = this.getCompletedSections();
        const progressPercent = (completedSections / this.sections.length) * 100;
        
        const progressFill = document.getElementById('configProgress');
        const progressText = document.getElementById('progressText');
        
        if (progressFill) {
            progressFill.style.width = `${progressPercent}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${Math.round(progressPercent)}% Complete`;
        }
    }

    getCompletedSections() {
        let completed = 0;
        
        // Basic info
        if (this.config.config_name) completed++;
        
        // Video settings
        if (this.config.video_settings?.transcode_profiles?.length > 0) completed++;
        
        // Image settings
        if (this.config.image_settings?.transcode_profiles?.length > 0) completed++;
        
        // Always count remaining sections if they have any settings
        completed += 7; // Simplified for now
        
        return Math.min(completed, this.sections.length);
    }

    updateSummary() {
        const videoProfiles = this.config.video_settings?.transcode_profiles?.length || 0;
        const imageProfiles = this.config.image_settings?.transcode_profiles?.length || 0;
        const faceDetection = this.config.face_detection?.enabled ? 'Enabled' : 'Disabled';
        
        this.updateElement('summary-video-profiles', videoProfiles);
        this.updateElement('summary-image-profiles', imageProfiles);
        this.updateElement('summary-face-detection', faceDetection);
        this.updateElement('video-profiles-count', videoProfiles);
        this.updateElement('image-profiles-count', imageProfiles);
    }

    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = content;
        }
    }

    updateProfileCount(elementId, count) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = count;
            element.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    markDirty() {
        this.isDirty = true;
        this.config.updated_at = new Date().toISOString();
    }

    generateId() {
        return 'id_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    // Template Library
    async openTemplateLibrary() {
        const modal = document.getElementById('templateModal');
        if (modal) {
            modal.style.display = 'flex';
            modal.classList.add('active');
            await this.loadTemplates();
        }
    }

    closeTemplateLibrary() {
        const modal = document.getElementById('templateModal');
        if (modal) {
            modal.style.display = 'none';
            modal.classList.remove('active');
        }
    }

    async loadTemplates() {
        const grid = document.getElementById('templateGrid');
        if (!grid) return;

        const templates = [
            {
                name: 'Social Media Optimized',
                description: 'Perfect for Instagram, TikTok, YouTube content',
                file: 'social-media-optimized.json',
                tags: ['social', 'mobile', 'vertical']
            },
            {
                name: 'Enterprise Production',
                description: 'High-quality settings for professional content',
                file: 'enterprise-production.json',
                tags: ['enterprise', '4k', 'professional']
            },
            {
                name: 'AI & Analytics',
                description: 'Optimized for machine learning and analysis',
                file: 'ai-analytics-focused.json',
                tags: ['ai', 'analytics', 'face-detection']
            },
            {
                name: 'Mobile & Web',
                description: 'Lightweight settings for web delivery',
                file: 'mobile-web-optimized.json',
                tags: ['mobile', 'web', 'performance']
            },
            {
                name: 'Development & Testing',
                description: 'Fast settings for development workflows',
                file: 'development-testing.json',
                tags: ['development', 'testing', 'fast']
            }
        ];

        grid.innerHTML = templates.map(template => `
            <div class="template-card" onclick="configBuilder.loadTemplate('${template.file}')">
                <h4>${template.name}</h4>
                <p>${template.description}</p>
                <div class="template-meta">
                    <div class="template-tags">
                        ${template.tags.map(tag => `<span class="template-tag">${tag}</span>`).join('')}
                    </div>
                </div>
            </div>
        `).join('');
    }

    async loadTemplate(filename) {
        try {
            this.showLoading('Loading template...');
            
            const response = await fetch(`/config_samples/${filename}`);
            if (!response.ok) {
                throw new Error(`Failed to load template: ${response.status}`);
            }
            
            const templateConfig = await response.json();
            
            if (this.isDirty) {
                if (!confirm('Loading a template will overwrite your current configuration. Continue?')) {
                    this.hideLoading();
                    return;
                }
            }
            
            this.config = { ...templateConfig };
            this.config.created_at = new Date().toISOString();
            this.config.updated_at = new Date().toISOString();
            
            this.loadSection('basic-info');
            this.updateSummary();
            this.updateProgress();
            this.isDirty = true;
            
            this.closeTemplateLibrary();
            this.hideLoading();
            this.showNotification('Template loaded successfully', 'success');
            
        } catch (error) {
            console.error('Failed to load template:', error);
            this.hideLoading();
            this.showNotification('Failed to load template', 'error');
        }
    }

    // Validation
    validateConfiguration() {
        this.validation = {
            errors: [],
            warnings: [],
            isValid: true
        };

        this.validateBasicInfo();
        this.validateVideoSettings();
        this.validateImageSettings();
        this.validateOutputSettings();

        this.showValidationResults();
        this.updateElement('summary-validation', this.validation.isValid ? 'Valid' : 'Invalid');
    }

    validateBasicInfo() {
        if (!this.config.config_name || this.config.config_name.trim() === '') {
            this.validation.errors.push({
                section: 'Basic Information',
                field: 'Configuration Name',
                message: 'Configuration name is required'
            });
            this.validation.isValid = false;
        }

        if (this.config.version && !this.config.version.match(/^\\d+\\.\\d+\\.\\d+$/)) {
            this.validation.warnings.push({
                section: 'Basic Information',
                field: 'Version',
                message: 'Version should follow semantic versioning (e.g., 1.0.0)'
            });
        }
    }

    validateVideoSettings() {
        if (this.config.video_settings?._enabled) {
            const profiles = this.config.video_settings.transcode_profiles || [];
            if (profiles.length === 0) {
                this.validation.warnings.push({
                    section: 'Video Settings',
                    field: 'Transcode Profiles',
                    message: 'No video transcode profiles configured'
                });
            }

            profiles.forEach((profile, index) => {
                if (!profile.name) {
                    this.validation.errors.push({
                        section: 'Video Settings',
                        field: `Profile ${index + 1} Name`,
                        message: 'Profile name is required'
                    });
                    this.validation.isValid = false;
                }

                if (profile.width < 64 || profile.width > 7680) {
                    this.validation.errors.push({
                        section: 'Video Settings',
                        field: `Profile ${index + 1} Width`,
                        message: 'Width must be between 64 and 7680 pixels'
                    });
                    this.validation.isValid = false;
                }

                if (profile.height < 64 || profile.height > 4320) {
                    this.validation.errors.push({
                        section: 'Video Settings',
                        field: `Profile ${index + 1} Height`,
                        message: 'Height must be between 64 and 4320 pixels'
                    });
                    this.validation.isValid = false;
                }
            });
        }
    }

    validateImageSettings() {
        if (this.config.image_settings?._enabled) {
            const profiles = this.config.image_settings.transcode_profiles || [];
            if (profiles.length === 0) {
                this.validation.warnings.push({
                    section: 'Image Settings',
                    field: 'Transcode Profiles',
                    message: 'No image transcode profiles configured'
                });
            }
        }
    }

    validateOutputSettings() {
        if (!this.config.output_settings?.storage?.s3_bucket) {
            this.validation.warnings.push({
                section: 'Output Settings',
                field: 'S3 Bucket',
                message: 'No S3 bucket configured for output storage'
            });
        }
    }

    showValidationResults() {
        const panel = document.getElementById('validationPanel');
        const content = document.getElementById('validationContent');
        
        if (!panel || !content) return;

        let html = '';

        if (this.validation.errors.length > 0) {
            html += '<div class="validation-group"><h5 class="text-error">Errors</h5>';
            this.validation.errors.forEach(error => {
                html += `<div class="validation-item error">
                    <strong>${error.section} - ${error.field}:</strong> ${error.message}
                </div>`;
            });
            html += '</div>';
        }

        if (this.validation.warnings.length > 0) {
            html += '<div class="validation-group"><h5 class="text-warning">Warnings</h5>';
            this.validation.warnings.forEach(warning => {
                html += `<div class="validation-item warning">
                    <strong>${warning.section} - ${warning.field}:</strong> ${warning.message}
                </div>`;
            });
            html += '</div>';
        }

        if (this.validation.errors.length === 0 && this.validation.warnings.length === 0) {
            html = '<div class="validation-item success">✅ Configuration is valid with no issues found.</div>';
        }

        content.innerHTML = html;
        panel.classList.add('active');
    }

    closeValidationPanel() {
        const panel = document.getElementById('validationPanel');
        if (panel) {
            panel.classList.remove('active');
        }
    }

    // Export/Import
    exportConfiguration() {
        try {
            const configJson = JSON.stringify(this.config, null, 2);
            const blob = new Blob([configJson], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `${this.config.config_name || 'configuration'}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            this.showNotification('Configuration exported successfully', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('Failed to export configuration', 'error');
        }
    }

    async saveConfiguration() {
        try {
            this.showLoading('Saving configuration...');
            
            // Get token from localStorage or session
            const token = localStorage.getItem('token') || sessionStorage.getItem('token');
            
            // Determine if we're creating or updating
            const isEditing = window.CONFIG_ID;
            const url = isEditing ? `/api/configs/${window.CONFIG_ID}` : '/api/configs';
            const method = isEditing ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    name: this.config.config_name,
                    description: this.config.description,
                    config_json: JSON.stringify(this.config)
                })
            });

            if (!response.ok) {
                throw new Error(`Save failed: ${response.status}`);
            }

            const result = await response.json();
            this.isDirty = false;
            this.hideLoading();
            
            const message = isEditing ? 'Configuration updated successfully' : 'Configuration saved successfully';
            this.showNotification(message, 'success');
            
            // If we just created a new config, update the URL to editing mode
            if (!isEditing && result.id) {
                window.CONFIG_ID = result.id;
                // Update browser URL without page refresh
                const newUrl = `/configs/edit/${result.id}`;
                window.history.replaceState({}, '', newUrl);
            }
            
        } catch (error) {
            console.error('Save failed:', error);
            this.hideLoading();
            this.showNotification('Failed to save configuration', 'error');
        }
    }

    // JSON Editor functions
    formatJSON() {
        if (this.jsonEditor) {
            this.jsonEditor.trigger('editor', 'action', 'editor.action.formatDocument');
        }
    }

    validateJSON() {
        if (this.jsonEditor) {
            try {
                const value = this.jsonEditor.getValue();
                const parsed = JSON.parse(value);
                this.config = parsed;
                this.updateSummary();
                this.showNotification('JSON is valid and synchronized', 'success');
            } catch (error) {
                this.showNotification(`Invalid JSON: ${error.message}`, 'error');
            }
        }
    }

    syncFromForm() {
        if (this.jsonEditor) {
            this.updateJsonEditor();
            this.showNotification('JSON synchronized from form', 'success');
        }
    }

    // Utility functions
    showLoading(message = 'Loading...') {
        const overlay = document.getElementById('loadingOverlay');
        const text = document.getElementById('loadingText');
        
        if (overlay) {
            overlay.style.display = 'flex';
        }
        if (text) {
            text.textContent = message;
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    showNotification(message, type = 'info') {
        // Create a simple notification system
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span>${message}</span>
                <button class="notification-close">&times;</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
        
        // Manual close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        });
    }

    getConfigSchema() {
        // Return JSON schema for validation
        return {
            type: 'object',
            properties: {
                config_name: { type: 'string', minLength: 1 },
                description: { type: 'string' },
                version: { type: 'string', pattern: '^\\\\d+\\\\.\\\\d+\\\\.\\\\d+$' },
                video_settings: {
                    type: 'object',
                    properties: {
                        _enabled: { type: 'boolean' },
                        transcode_profiles: {
                            type: 'array',
                            items: {
                                type: 'object',
                                properties: {
                                    name: { type: 'string', minLength: 1 },
                                    width: { type: 'number', minimum: 64, maximum: 7680 },
                                    height: { type: 'number', minimum: 64, maximum: 4320 },
                                    codec: { type: 'string' },
                                    preset: { type: 'string' },
                                    crf: { type: 'number', minimum: 0, maximum: 51 }
                                },
                                required: ['name', 'width', 'height', 'codec']
                            }
                        }
                    }
                }
            },
            required: ['config_name']
        };
    }
}

// Initialize the Configuration Builder when the page loads
let configBuilder;
document.addEventListener('DOMContentLoaded', () => {
    configBuilder = new ConfigurationBuilder();
});

// Add some notification styles
const notificationStyles = `
<style>
.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    max-width: 400px;
    padding: 16px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    animation: slideIn 0.3s ease;
}

.notification-info {
    background: #e1f5fe;
    border-left: 4px solid #0288d1;
    color: #01579b;
}

.notification-success {
    background: #e8f5e8;
    border-left: 4px solid #4caf50;
    color: #1b5e20;
}

.notification-warning {
    background: #fff3e0;
    border-left: 4px solid #ff9800;
    color: #e65100;
}

.notification-error {
    background: #ffebee;
    border-left: 4px solid #f44336;
    color: #b71c1c;
}

.notification-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.notification-close {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    margin-left: 12px;
    opacity: 0.7;
}

.notification-close:hover {
    opacity: 1;
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

.validation-group {
    margin-bottom: 20px;
}

.validation-group h5 {
    margin-bottom: 10px;
    font-weight: 600;
}

.validation-item {
    padding: 8px 12px;
    margin-bottom: 8px;
    border-radius: 4px;
    font-size: 14px;
}

.validation-item.error {
    background: #ffebee;
    border-left: 4px solid #f44336;
    color: #b71c1c;
}

.validation-item.warning {
    background: #fff3e0;
    border-left: 4px solid #ff9800;
    color: #e65100;
}

.validation-item.success {
    background: #e8f5e8;
    border-left: 4px solid #4caf50;
    color: #1b5e20;
}

.text-error {
    color: #f44336;
}

.text-warning {
    color: #ff9800;
}

.text-muted {
    color: #666;
    font-style: italic;
    text-align: center;
    padding: 20px;
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', notificationStyles);