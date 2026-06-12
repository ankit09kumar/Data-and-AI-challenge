// Intelligent Candidate Discovery Frontend Utilities

document.addEventListener('DOMContentLoaded', () => {
    // 1. Drag and Drop File Upload Handling
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('resume-file-input');
    const fileListPreview = document.getElementById('file-list-preview');

    if (uploadZone && fileInput) {
        // Trigger click on input when clicking zone
        uploadZone.addEventListener('click', () => fileInput.click());

        // Highlight upload zone on dragover
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadZone.classList.add('dragover');
            }, false);
        });

        // Remove highlight
        ['dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadZone.classList.remove('dragover');
            }, false);
        });

        // Handle file drop
        uploadZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            fileInput.files = files;
            updateFilePreview(files);
        }, false);

        // Handle file selection
        fileInput.addEventListener('change', () => {
            updateFilePreview(fileInput.files);
        });
    }

    function updateFilePreview(files) {
        if (!fileListPreview) return;
        fileListPreview.innerHTML = '';
        
        if (files.length === 0) {
            fileListPreview.innerHTML = '<p class="text-muted" style="text-align: center;">No files selected</p>';
            return;
        }

        Array.from(files).forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            // Format file size
            const sizeInKb = (file.size / 1024).toFixed(1);
            
            fileItem.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fas ${file.name.endsWith('.pdf') ? 'fa-file-pdf' : 'fa-file-word'}" style="color: ${file.name.endsWith('.pdf') ? '#ef4444' : '#3b82f6'}; font-size: 18px;"></i>
                    <div>
                        <p style="font-size: 14px; font-weight: 500; margin: 0;">${file.name}</p>
                        <span style="font-size: 11px; color: #64748b;">${sizeInKb} KB</span>
                    </div>
                </div>
                <i class="fas fa-check-circle" style="color: #10b981;"></i>
            `;
            fileListPreview.appendChild(fileItem);
        });
    }

    // 2. Load Chart.js Analytics (only if on dashboard containing the charts canvas)
    const scoreChartCanvas = document.getElementById('scoreDistributionChart');
    const skillChartCanvas = document.getElementById('skillsChart');
    const statusChartCanvas = document.getElementById('statusChart');

    if (scoreChartCanvas && skillChartCanvas && statusChartCanvas) {
        fetch('/api/analytics')
            .then(response => response.json())
            .then(data => {
                renderCharts(data);
            })
            .catch(error => console.error('Error fetching analytics data:', error));
    }

    function renderCharts(data) {
        // Common Options
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#94a3b8',
                        font: { family: 'Outfit', size: 12 }
                    }
                }
            },
            scales: {
                r: { grid: { color: 'rgba(255,255,255,0.06)' } },
                x: {
                    grid: { color: 'rgba(255,255,255,0.06)', drawBorder: false },
                    ticks: { color: '#94a3b8', font: { family: 'Outfit' } }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.06)', drawBorder: false },
                    ticks: { color: '#94a3b8', font: { family: 'Outfit' } }
                }
            }
        };

        // Score Distribution Chart (Bar)
        new Chart(scoreChartCanvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.distributions_labels,
                datasets: [{
                    label: 'Number of Candidates',
                    data: data.distributions_values,
                    backgroundColor: 'rgba(99, 102, 241, 0.65)',
                    borderColor: '#6366f1',
                    borderWidth: 1.5,
                    borderRadius: 6,
                    hoverBackgroundColor: 'rgba(99, 102, 241, 0.85)'
                }]
            },
            options: chartOptions
        });

        // Top Extracted Skills Chart (Horizontal Bar)
        new Chart(skillChartCanvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.top_skills_labels,
                datasets: [{
                    label: 'Occurrences in Resumes',
                    data: data.top_skills_values,
                    backgroundColor: 'rgba(6, 182, 212, 0.65)',
                    borderColor: '#06b6d4',
                    borderWidth: 1.5,
                    borderRadius: 6,
                    hoverBackgroundColor: 'rgba(6, 182, 212, 0.85)'
                }]
            },
            options: {
                ...chartOptions,
                indexAxis: 'y'
            }
        });

        // Application Status Chart (Doughnut)
        new Chart(statusChartCanvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: data.status_labels.length ? data.status_labels : ['No Data'],
                datasets: [{
                    data: data.status_values.length ? data.status_values : [1],
                    backgroundColor: data.status_labels.length ? [
                        'rgba(16, 185, 129, 0.75)', // Screened / Hired (Emerald)
                        'rgba(99, 102, 241, 0.75)',  // Shortlisted / Interview (Indigo)
                        'rgba(245, 158, 11, 0.75)',  // Warning
                        'rgba(239, 68, 68, 0.75)',   // Rejected (Rose)
                        'rgba(6, 182, 212, 0.75)'    // Info
                    ] : ['rgba(255,255,255,0.08)'],
                    borderColor: 'rgba(15, 23, 42, 0.6)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#94a3b8',
                            font: { family: 'Outfit', size: 11 }
                        }
                    }
                }
            }
        });
    }
});
