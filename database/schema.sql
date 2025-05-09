-- Bảng Users
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng lưu trữ các cấu hình transcode
CREATE TABLE IF NOT EXISTS configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    config_json TEXT NOT NULL,
    user_id INTEGER,
    is_default BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Bảng jobs: Lưu lại các job transcode
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    config_id INTEGER NOT NULL,
    status TEXT NOT NULL, -- 'pending', 'processing', 'completed', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (config_id) REFERENCES configs(id)
);

-- Bảng media: Lưu thông tin các media được upload
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    original_filename TEXT NOT NULL,
    file_type TEXT NOT NULL, -- 'video' or 'image'
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    local_path TEXT,
    s3_path TEXT,
    duration REAL, -- Chỉ có ý nghĩa với video
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- Bảng transcode_tasks: Lưu thông tin các task transcode cho từng media
CREATE TABLE IF NOT EXISTS transcode_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    task_type TEXT NOT NULL, -- 'transcode', 'preview', 'thumbnail'
    profile_name TEXT NOT NULL,
    status TEXT NOT NULL, -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (media_id) REFERENCES media(id)
);

-- Bảng transcode_outputs: Lưu thông tin các output sau khi transcode
CREATE TABLE IF NOT EXISTS transcode_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    output_filename TEXT NOT NULL,
    s3_url TEXT NOT NULL,
    local_path TEXT,
    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    duration REAL, -- Chỉ có ý nghĩa với video
    format TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES transcode_tasks(id)
);

-- Index để tối ưu tìm kiếm
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_media_job_id ON media(job_id);
CREATE INDEX IF NOT EXISTS idx_transcode_tasks_media_id ON transcode_tasks(media_id);
CREATE INDEX IF NOT EXISTS idx_transcode_outputs_task_id ON transcode_outputs(task_id);