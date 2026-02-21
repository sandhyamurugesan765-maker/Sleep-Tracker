// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize charts
    initializeCharts();
    
    // Real-time clock for sleep logging
    updateRealTimeClocks();
    setInterval(updateRealTimeClocks, 60000);
    
    // Form validation
    setupFormValidation();
    
    // Sleep quality slider
    setupSleepQualitySlider();
});
// Apply progress bar widths from data attributes
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-width]').forEach(function(el) {
        const width = el.getAttribute('data-width');
        if (width) {
            el.style.width = width + '%';
        }
    });
});
// Update real-time clocks
function updateRealTimeClocks() {
    const now = new Date();
    const timeString = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    const dateString = now.toLocaleDateString();
    
    document.querySelectorAll('.current-time').forEach(el => {
        el.textContent = timeString;
    });
    
    document.querySelectorAll('.current-date').forEach(el => {
        el.textContent = dateString;
    });
}

// Setup sleep quality slider
function setupSleepQualitySlider() {
    const slider = document.getElementById('sleepQualitySlider');
    const output = document.getElementById('qualityValue');
    
    if (slider && output) {
        slider.addEventListener('input', function() {
            output.textContent = this.value;
            updateQualityIndicator(this.value);
        });
    }
}

function updateQualityIndicator(value) {
    const indicator = document.getElementById('qualityIndicator');
    if (!indicator) return;
    
    indicator.className = 'quality-indicator ';
    if (value >= 8) {
        indicator.classList.add('quality-excellent');
    } else if (value >= 6) {
        indicator.classList.add('quality-good');
    } else if (value >= 4) {
        indicator.classList.add('quality-fair');
    } else {
        indicator.classList.add('quality-poor');
    }
}

// Calculate sleep duration
function calculateSleepDuration() {
    const bedtimeInput = document.getElementById('bedtime');
    const wakeupInput = document.getElementById('wake_up_time');
    const durationDisplay = document.getElementById('calculatedDuration');
    
    if (!bedtimeInput || !wakeupInput || !durationDisplay) return;
    
    function updateDuration() {
        const bedtime = bedtimeInput.value;
        const wakeup = wakeupInput.value;
        
        if (bedtime && wakeup) {
            const bedtimeDate = new Date(`2000-01-01T${bedtime}`);
            let wakeupDate = new Date(`2000-01-01T${wakeup}`);
            
            // If wakeup is earlier than bedtime, add 24 hours
            if (wakeupDate < bedtimeDate) {
                wakeupDate.setDate(wakeupDate.getDate() + 1);
            }
            
            const durationMs = wakeupDate - bedtimeDate;
            const durationHours = (durationMs / (1000 * 60 * 60)).toFixed(1);
            
            durationDisplay.textContent = `${durationHours} hours`;
            
            // Color code based on recommended sleep duration
            const sleepGoal = document.getElementById('sleepGoal')?.value || 8;
            durationDisplay.className = 'metric-value ';
            if (durationHours >= sleepGoal) {
                durationDisplay.classList.add('text-success');
            } else if (durationHours >= sleepGoal - 1) {
                durationDisplay.classList.add('text-warning');
            } else {
                durationDisplay.classList.add('text-danger');
            }
        }
    }
    
    bedtimeInput.addEventListener('change', updateDuration);
    wakeupInput.addEventListener('change', updateDuration);
}

// Initialize charts
function initializeCharts() {
    // Check if we're on a page that needs charts
    if (document.getElementById('sleepChart')) {
        fetchSleepData();
    }
}

// Fetch sleep data for charts
async function fetchSleepData() {
    try {
        const response = await fetch('/api/sleep_data');
        const data = await response.json();
        
        if (data.dates && data.dates.length > 0) {
            renderSleepChart(data);
        }
    } catch (error) {
        console.error('Error fetching sleep data:', error);
    }
}

// Render sleep chart
function renderSleepChart(data) {
    const ctx = document.getElementById('sleepChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [
                {
                    label: 'Sleep Duration (hours)',
                    data: data.durations,
                    borderColor: '#4361ee',
                    backgroundColor: 'rgba(67, 97, 238, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Sleep Quality (1-10)',
                    data: data.qualities,
                    borderColor: '#4cc9f0',
                    backgroundColor: 'rgba(76, 201, 240, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Form validation
function setupFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
            
            // Custom validation for sleep logging
            if (form.id === 'sleepLogForm') {
                validateSleepTimes(form);
            }
        });
    });
}

// Validate sleep times
function validateSleepTimes(form) {
    const bedtime = form.querySelector('#bedtime');
    const wakeup = form.querySelector('#wake_up_time');
    
    if (bedtime && wakeup && bedtime.value && wakeup.value) {
        const bedtimeDate = new Date(`2000-01-01T${bedtime.value}`);
        const wakeupDate = new Date(`2000-01-01T${wakeup.value}`);
        
        let adjustedWakeup = wakeupDate;
        if (wakeupDate < bedtimeDate) {
            adjustedWakeup.setDate(adjustedWakeup.getDate() + 1);
        }
        
        const duration = (adjustedWakeup - bedtimeDate) / (1000 * 60 * 60);
        
        if (duration < 1) {
            alert('Sleep duration should be at least 1 hour.');
            return false;
        }
        
        if (duration > 14) {
            alert('Sleep duration seems unusually long. Please check your times.');
            return false;
        }
    }
    
    return true;
}

// Mark recommendation as completed
async function completeRecommendation(recId) {
    try {
        const response = await fetch(`/complete_recommendation/${recId}`);
        if (response.ok) {
            // Remove the recommendation from UI
            const card = document.getElementById(`rec-${recId}`);
            if (card) {
                card.style.opacity = '0';
                setTimeout(() => card.remove(), 300);
            }
            
            // Show success message
            showNotification('Recommendation completed!', 'success');
        }
    } catch (error) {
        console.error('Error completing recommendation:', error);
        showNotification('Error completing recommendation', 'error');
    }
}

// Show notification
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 5000);
}

// Export data function
function exportData(format = 'json') {
    fetch('/api/sleep_data')
        .then(response => response.json())
        .then(data => {
            let content, mimeType, filename;
            
            if (format === 'json') {
                content = JSON.stringify(data, null, 2);
                mimeType = 'application/json';
                filename = 'sleep-data.json';
            } else if (format === 'csv') {
                content = convertToCSV(data);
                mimeType = 'text/csv';
                filename = 'sleep-data.csv';
            }
            
            const blob = new Blob([content], { type: mimeType });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            window.URL.revokeObjectURL(url);
        });
}

// Convert data to CSV
function convertToCSV(data) {
    const headers = ['Date', 'Duration', 'Quality'];
    const rows = data.dates.map((date, i) => [
        date,
        data.durations[i] || '',
        data.qualities[i] || ''
    ]);
    
    return [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');
}

// Dark mode toggle
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
}

// Check for saved dark mode preference
if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark-mode');
}

// Add dark mode styles
const darkModeStyles = `
    .dark-mode {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #e2e8f0;
    }
    
    .dark-mode .card {
        background: #2d3748;
        color: #e2e8f0;
    }
    
    .dark-mode .navbar {
        background: rgba(45, 55, 72, 0.95);
    }
`;
const styleSheet = document.createElement('style');
styleSheet.textContent = darkModeStyles;
document.head.appendChild(styleSheet);

// At the top of main.js, wrap everything in a try-catch
(function() {
    'use strict';
    
    try {
        // Your existing code here...
        
        // Update quality indicator function
        window.updateQualityIndicator = function(value) {
            const indicator = document.getElementById('qualityIndicator');
            if (!indicator) return;
            
            indicator.className = 'quality-indicator ';
            if (value >= 8) {
                indicator.classList.add('quality-excellent');
            } else if (value >= 6) {
                indicator.classList.add('quality-good');
            } else if (value >= 4) {
                indicator.classList.add('quality-fair');
            } else {
                indicator.classList.add('quality-poor');
            }
        };
        
        // Calculate sleep duration function
        window.calculateSleepDuration = function() {
            // Your existing calculateSleepDuration code...
        };
        
    } catch (error) {
        console.error('Error in main.js:', error);
    }
})();