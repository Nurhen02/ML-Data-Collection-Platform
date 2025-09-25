class MLDataPlatform {
    constructor() {
        this.apiBaseUrl = window.location.origin;
        this.activeJobs = new Map();
        this.pollingInterval = null;
        
        this.initializeEventListeners();
        this.loadActiveJobs();
    }

    initializeEventListeners() {
        // Job submission form - prevent default form submission
        document.getElementById('jobForm').addEventListener('submit', (e) => {
            e.preventDefault(); // This prevents page refresh
            this.submitJob();
        });

        // Modal close button
        document.querySelector('.close').addEventListener('click', () => {
            this.closeModal();
        });

        // Close modal when clicking outside
        window.addEventListener('click', (e) => {
            const modal = document.getElementById('jobModal');
            if (e.target === modal) {
                this.closeModal();
            }
        });
    }

    async submitJob() {
        const urlInput = document.getElementById('url');
        const sourceTypeSelect = document.getElementById('sourceType');
        const submitBtn = document.getElementById('submitBtn');
        const statusMessage = document.getElementById('statusMessage');
        
        const url = urlInput.value.trim();
        const sourceType = sourceTypeSelect.value;

        // Clear previous status message
        statusMessage.style.display = 'none';
        statusMessage.className = '';

        // Validate URL
        if (!this.isValidUrl(url)) {
            this.showMessage('Please enter a valid URL (e.g., https://example.com)', 'error', statusMessage);
            return;
        }

        // Disable button and show loading
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<div class="spinner"></div> Submitting...';

        try {
            console.log('Submitting job:', { url, sourceType });
            
            const response = await fetch(`${this.apiBaseUrl}/jobs`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    source_type: sourceType || null
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
            }

            const job = await response.json();
            console.log('Job submitted successfully:', job);
            
            // Add job to active jobs list
            this.addJobToList(job);
            
            // Clear form but keep the source type
            urlInput.value = '';
            
            this.showMessage('Job submitted successfully! Tracking progress...', 'success', statusMessage);
            
            // Start polling for updates if not already started
            if (!this.pollingInterval) {
                this.startPolling();
            }

        } catch (error) {
            console.error('Error submitting job:', error);
            this.showMessage('Error submitting job: ' + error.message, 'error', statusMessage);
        } finally {
            // Re-enable button
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Job';
        }
    }

    async loadActiveJobs() {
        try {
            // For now, we'll just start with an empty list
            // In a real app, you might want to load existing jobs from the server
            this.renderJobsList();
        } catch (error) {
            console.error('Error loading jobs:', error);
        }
    }

    startPolling() {
        // Poll for job status updates every 3 seconds
        this.pollingInterval = setInterval(() => {
            this.updateJobStatuses();
        }, 3000);
    }

    async updateJobStatuses() {
        const jobsToUpdate = Array.from(this.activeJobs.values())
            .filter(job => job.status === 'PENDING' || job.status === 'PROCESSING');

        if (jobsToUpdate.length === 0) {
            // No active jobs to poll, stop polling
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
                this.pollingInterval = null;
            }
            return;
        }

        console.log(`Polling ${jobsToUpdate.length} active jobs...`);

        for (const job of jobsToUpdate) {
            try {
                const response = await fetch(`${this.apiBaseUrl}/jobs/${job.id}`);
                if (response.ok) {
                    const updatedJob = await response.json();
                    console.log(`Job ${job.id} status: ${updatedJob.status}`);
                    this.updateJobInList(updatedJob);
                } else {
                    console.error(`Failed to fetch job ${job.id}: ${response.status}`);
                }
            } catch (error) {
                console.error(`Error updating job ${job.id}:`, error);
            }
        }
    }

    addJobToList(job) {
        this.activeJobs.set(job.id, job);
        this.renderJobsList();
    }

    updateJobInList(updatedJob) {
        this.activeJobs.set(updatedJob.id, updatedJob);
        this.renderJobsList();

        // If this job was just completed, load its data
        if (updatedJob.status === 'COMPLETED') {
            this.loadJobData(updatedJob.id);
        }
    }

    renderJobsList() {
        const jobsList = document.getElementById('jobsList');
        const jobs = Array.from(this.activeJobs.values())
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

        if (jobs.length === 0) {
            jobsList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No active jobs. Submit a URL to get started!</p>
                </div>
            `;
            return;
        }

        jobsList.innerHTML = jobs.map(job => `
            <div class="job-item" onclick="platform.showJobDetails(${job.id})">
                <div class="job-header">
                    <div class="job-url" title="${job.url}">${this.truncateUrl(job.url)}</div>
                    <span class="job-status status-${job.status.toLowerCase()}">${job.status}</span>
                </div>
                <div class="job-meta">
                    <span>${this.formatDate(job.created_at)}</span>
                    <span>${job.source_type || 'Auto-detected'}</span>
                </div>
            </div>
        `).join('');
    }

    async showJobDetails(jobId) {
        const job = this.activeJobs.get(jobId);
        if (!job) return;

        const modal = document.getElementById('jobModal');
        const detailsDiv = document.getElementById('jobDetails');

        // Show basic job info
        let detailsHTML = `
            <div class="job-detail">
                <label>URL:</label>
                <div><a href="${job.url}" target="_blank">${job.url}</a></div>
            </div>
            <div class="job-detail">
                <label>Status:</label>
                <span class="job-status status-${job.status.toLowerCase()}">${job.status}</span>
            </div>
            <div class="job-detail">
                <label>Submitted:</label>
                <div>${this.formatDate(job.created_at)}</div>
            </div>
            <div class="job-detail">
                <label>Source Type:</label>
                <div>${job.source_type || 'Auto-detected'}</div>
            </div>
        `;

        // If job is completed, show the data
        if (job.status === 'COMPLETED' && job.data) {
            detailsHTML += `
                <div class="job-detail">
                    <label>Clean Text:</label>
                    <div class="data-content">${this.escapeHtml(job.data.clean_text || 'No text content')}</div>
                </div>
            `;

            // Display images if available
            if (job.data.page_metadata.image_urls && job.data.page_metadata.image_urls.length > 0) {
                detailsHTML += `
                    <div class="job-detail">
                        <label>Images (${job.data.page_metadata.image_count}):</label>
                        <div class="images-container">
                            ${job.data.page_metadata.image_urls.map(url => `
                                <div class="image-item">
                                    <img src="${url}" alt="Tweet image" onerror="this.style.display='none'">
                                    <a href="${url}" target="_blank" class="image-link">View Original</a>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            // Display video info if available
            if (job.data.page_metadata.has_video) {
                detailsHTML += `
                    <div class="job-detail">
                        <label>Media:</label>
                        <div class="media-info">
                            <i class="fas fa-video"></i> This tweet contains video content
                            ${job.data.page_metadata.thumbnail_url ? `
                                <br><small>Thumbnail: <a href="${job.data.page_metadata.thumbnail_url}" target="_blank">View</a></small>
                            ` : ''}
                        </div>
                    </div>
                `;
            }

            // Display engagement metrics if available
            const engagementMetrics = this.getEngagementMetrics(job.data.page_metadata);
            if (engagementMetrics) {
                detailsHTML += `
                    <div class="job-detail">
                        <label>Engagement:</label>
                        <div class="engagement-metrics">
                            ${engagementMetrics}
                        </div>
                    </div>
                `;
            }

            detailsHTML += `
                <div class="job-detail">
                    <label>Full Metadata:</label>
                    <div class="data-content">${JSON.stringify(job.data.page_metadata, null, 2)}</div>
                </div>
            `;
        } else if (job.status === 'FAILED') {
            detailsHTML += `
                <div class="job-detail">
                    <label>Error:</label>
                    <div class="data-content" style="color: #e53e3e;">${job.error_message || 'Unknown error occurred'}</div>
                </div>
            `;
        }

        detailsDiv.innerHTML = detailsHTML;
        modal.style.display = 'block';
    }

    getEngagementMetrics(metadata) {
        const metrics = [];
        
        if (metadata.likes) metrics.push(`<span class="metric"><i class="fas fa-heart"></i> ${metadata.likes} Likes</span>`);
        if (metadata.retweets) metrics.push(`<span class="metric"><i class="fas fa-retweet"></i> ${metadata.retweets} Retweets</span>`);
        if (metadata.replies) metrics.push(`<span class="metric"><i class="fas fa-reply"></i> ${metadata.replies} Replies</span>`);
        if (metadata.views) metrics.push(`<span class="metric"><i class="fas fa-eye"></i> ${metadata.views} Views</span>`);
        
        return metrics.length > 0 ? metrics.join(' ') : null;
    }

    async loadJobData(jobId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/data/${jobId}`);
            if (response.ok) {
                const data = await response.json();
                const job = this.activeJobs.get(jobId);
                job.data = data;
                this.activeJobs.set(jobId, job);
                this.renderJobsList();
            }
        } catch (error) {
            console.error(`Error loading job data ${jobId}:`, error);
        }
    }

    closeModal() {
        document.getElementById('jobModal').style.display = 'none';
    }

    // Utility functions
    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }

    truncateUrl(url, maxLength = 50) {
        return url.length > maxLength ? url.substring(0, maxLength) + '...' : url;
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleString();
    }

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    showMessage(message, type, element) {
        element.textContent = message;
        element.className = type;
        element.style.display = 'block';
        
        if (type === 'success') {
            element.style.backgroundColor = '#f0fff4';
            element.style.color = '#38a169';
            element.style.border = '1px solid #9ae6b4';
        } else if (type === 'error') {
            element.style.backgroundColor = '#fff5f5';
            element.style.color = '#e53e3e';
            element.style.border = '1px solid #fc8181';
        }
        
        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                element.style.display = 'none';
            }, 5000);
        }
    }
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.platform = new MLDataPlatform();
    console.log('ML Data Collection Platform initialized');
});