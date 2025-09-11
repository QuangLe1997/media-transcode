# Transcode Frontend

Modern React frontend for the Transcode Service with a beautiful gradient UI.

## Features

- 📤 **File Upload**: Drag & drop or click to upload video files
- 🔗 **URL Upload**: Transcode videos from URLs
- 📊 **Real-time Progress**: Track transcoding progress with visual progress bars
- 📋 **Profile Management**: Select custom transcoding profiles
- 🎯 **Detailed Results**: View completed outputs and failed profiles
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile
- 🔄 **Auto Refresh**: Optional auto-refresh for real-time updates

## Technology Stack

- **React 18** - Modern React with hooks
- **React Router** - Client-side routing
- **Axios** - HTTP client for API calls
- **CSS3** - Modern styling with gradients and animations
- **Nginx** - Production web server

## Development

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

## API Integration

The frontend integrates with the Transcode Service API:

- `POST /transcode/mobile` - Upload files
- `POST /transcode/url` - Transcode from URL
- `GET /tasks` - List all tasks
- `GET /task/{id}` - Get task details
- `DELETE /task/{id}` - Delete task

## Docker Deployment

The frontend is containerized with nginx:

```bash
# Build and run with docker-compose
docker-compose up frontend
```

Access the app at http://localhost:3000

## Configuration

Environment variables:

- `REACT_APP_API_URL` - API base URL (default: current host port 8087)

## UI Features

### Upload Page
- Drag & drop file upload
- URL-based transcoding
- Preset selection
- Custom profile selection
- Callback URL configuration

### Results Page
- Task grid with status indicators
- Progress bars for transcoding
- Detailed task modals
- Output file downloads
- Failed profile information
- Auto-refresh toggle
- Status filtering