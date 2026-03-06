// Main application class
class CivicFixApp {
    constructor() {
        this.issues = [];
        this.currentPage = 1;
        this.totalPages = 1;
        this.filters = {
            status: '',
            category: '',
            province: '',
            district: '',
            sector: '',
            search: ''
        };
        this.autoRefreshInterval = null;
        this.autoRefreshEnabled = true;
        this.refreshIntervalSeconds = 10; // Auto-refresh every 10 seconds
        this.init();
    }

    async init() {
        // Wait for auth to initialize
        setTimeout(() => {
            this.setupEventListeners();
            this.populateInitialDistricts();
            this.loadIssues();
            // Start auto-refresh for citizen issues
            this.startAutoRefresh();
        }, 1000);
    }

    startAutoRefresh() {
        if (!this.autoRefreshEnabled) return;
        
        console.log(`Citizen issues auto-refresh started: every ${this.refreshIntervalSeconds} seconds`);
        
        this.autoRefreshInterval = setInterval(() => {
            console.log('Auto-refreshing citizen issues...');
            this.loadIssues(this.currentPage, true); // Pass true to indicate auto-refresh
        }, this.refreshIntervalSeconds * 1000);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            console.log('Citizen issues auto-refresh stopped');
        }
    }

    setupEventListeners() {
        // Filter controls
        const applyFiltersBtn = document.getElementById('apply-filters');
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => this.applyFilters());
        }

        // Search functionality
        const searchBtn = document.getElementById('search-btn');
        const searchInput = document.getElementById('search-input');
        const clearBtn = document.getElementById('clear-search');
        
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', () => this.performSearch());
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performSearch();
                }
            });
        }
        
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearSearch());
        }

        // Filter dropdowns
        const statusFilter = document.getElementById('status-filter');
        const categoryFilter = document.getElementById('category-filter');
        const provinceFilter = document.getElementById('province-filter');
        const districtFilter = document.getElementById('district-filter');
        const sectorFilter = document.getElementById('sector-filter');
        
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.applyFilters());
        }
        if (categoryFilter) {
            categoryFilter.addEventListener('change', () => this.applyFilters());
        }
        if (provinceFilter) {
            provinceFilter.addEventListener('change', () => this.onProvinceChange());
        }
        if (districtFilter) {
            districtFilter.addEventListener('change', () => this.onDistrictChange());
        }
        if (sectorFilter) {
            sectorFilter.addEventListener('change', () => this.applyFilters());
        }
    }

    async loadIssues(page = 1, isAutoRefresh = false) {
        try {
            // Only show loading indicator for manual loads, not auto-refresh
            if (!isAutoRefresh) {
                this.showLoading(true);
            }
            
            const params = new URLSearchParams({
                page: page.toString(),
                per_page: '12'
            });

            if (this.filters.status) {
                params.append('status', this.filters.status);
            }
            if (this.filters.category) {
                params.append('category', this.filters.category);
            }
            if (this.filters.province) {
                params.append('province', this.filters.province);
            }
            if (this.filters.district) {
                params.append('district', this.filters.district);
            }
            if (this.filters.sector) {
                params.append('sector', this.filters.sector);
            }
            if (this.filters.search) {
                params.append('search', this.filters.search);
            }

            const response = await fetch(`${API_BASE_URL}/api/issues?${params}`, {
                headers: authManager.getAuthHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const newIssues = data.issues;
            const oldIssues = this.issues;
            
            // For auto-refresh, check if data actually changed before updating
            if (isAutoRefresh && JSON.stringify(oldIssues) === JSON.stringify(newIssues)) {
                console.log('No changes detected in auto-refresh, skipping update');
                return;
            }
            
            this.issues = newIssues;
            this.currentPage = data.current_page;
            this.totalPages = data.pages;

            this.displayIssues();
            this.updatePagination();

        } catch (error) {
            console.error('Error loading issues:', error);
            if (!isAutoRefresh) {
                showNotification('Error loading issues. Please try again.', 'error');
            }
        } finally {
            if (!isAutoRefresh) {
                this.showLoading(false);
            }
        }
    }

    displayIssues() {
        const issuesContainer = document.getElementById('issues-list');
        if (!issuesContainer) return;

        if (this.issues.length === 0) {
            issuesContainer.innerHTML = '<div class="no-issues">No issues found. Be the first to report one!</div>';
            return;
        }

        issuesContainer.innerHTML = this.issues.map(issue => this.createIssueCard(issue)).join('');
    }

    createIssueCard(issue) {
        const statusClass = issue.status.toLowerCase().replace(/\s+/g, '-');
        // Use full URL for Supabase Storage images, prepend API_BASE_URL for local uploads
        const imageSrc = issue.image_url ? 
            (issue.image_url.startsWith('http') ? issue.image_url : `${API_BASE_URL}${issue.image_url}`) : '';
        const imageHtml = imageSrc ? 
            `<img src="${imageSrc}" alt="Issue photo" class="issue-image">` : '';
        
        // Format location information
        const locationInfo = this.formatLocationInfo(issue);
        
        return `
            <div class="issue-card" data-issue-id="${issue.id}">
                <div class="status-banner">
                    <span class="status-label">Status:</span>
                    <span class="status-value ${statusClass}">${issue.status}</span>
                </div>
                <div class="issue-header">
                    <h3 class="issue-title">${this.escapeHtml(issue.title)}</h3>
                </div>
                
                <p class="issue-description">${this.escapeHtml(issue.description)}</p>
                
                ${locationInfo}
                
                ${imageHtml}
                
                <div class="issue-meta">
                    <span class="category">${issue.category}</span>
                    <span class="date">${this.formatDate(issue.created_at)}</span>
                    <button class="vote-btn" onclick="app.voteOnIssue(${issue.id})" 
                            ${!authManager.isAuthenticated() ? 'disabled' : ''}>
                        Vote <span class="vote-count">${issue.vote_count || 0}</span>
                    </button>
                </div>
            </div>
        `;
    }

    formatLocationInfo(issue) {
        let locationHtml = '<div class="issue-location">';
        
        if (issue.street_address) {
            locationHtml += `<div class="location-item"><span class="location-label">Address:</span> ${this.escapeHtml(issue.street_address)}</div>`;
        }
        
        if (issue.landmark_reference) {
            locationHtml += `<div class="location-item"><span class="location-label">Near:</span> ${this.escapeHtml(issue.landmark_reference)}</div>`;
        }
        
        if (issue.detailed_description) {
            locationHtml += `<div class="location-item"><span class="location-label">Details:</span> ${this.escapeHtml(issue.detailed_description)}</div>`;
        }
        
        locationHtml += '</div>';
        return locationHtml;
    }

    async voteOnIssue(issueId) {
        if (!authManager.isAuthenticated()) {
            showNotification('Please login to vote on issues.', 'warning');
            return;
        }

        // Get current vote state to determine action
        const issueCard = document.querySelector(`[data-issue-id="${issueId}"]`);
        const voteButton = issueCard?.querySelector('.vote-btn');
        const isCurrentlyVoted = voteButton?.classList.contains('voted');
        
        // INSTANT OPTIMISTIC UPDATE - Update UI immediately
        const currentVoteCount = parseInt(issueCard?.querySelector('.vote-count')?.textContent || '0');
        const newVoteCount = isCurrentlyVoted ? currentVoteCount - 1 : currentVoteCount + 1;
        const newVotedState = !isCurrentlyVoted;
        
        // Update UI instantly (optimistic)
        this.updateVoteCountInstantly(issueId, newVoteCount, newVotedState);
        
        // Show instant notification
        if (newVotedState) {
            showQuickNotification('Voted!', 'success');
        } else {
            showQuickNotification('Vote removed', 'info');
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/issues/${issueId}/vote`, {
                method: 'POST',
                headers: authManager.getAuthHeaders()
            });

            const data = await response.json();

            if (response.ok) {
                // Server confirmed - update with actual values (in case they differ)
                this.updateVoteCountInstantly(issueId, data.vote_count, data.action === 'voted');
            } else {
                // Server error - revert the optimistic update
                this.updateVoteCountInstantly(issueId, currentVoteCount, isCurrentlyVoted);
                showNotification(data.error || 'Error voting on issue.', 'error');
            }

        } catch (error) {
            // Network error - revert the optimistic update
            this.updateVoteCountInstantly(issueId, currentVoteCount, isCurrentlyVoted);
            console.error('Error voting on issue:', error);
            showNotification('Error voting on issue. Please try again.', 'error');
        }
    }

    updateVoteCountInstantly(issueId, newVoteCount, userVoted) {
        // Find the issue card and update its vote count and button state
        const issueCard = document.querySelector(`[data-issue-id="${issueId}"]`);
        if (!issueCard) return;

        // Update vote count display
        const voteCountElement = issueCard.querySelector('.vote-count');
        if (voteCountElement) {
            voteCountElement.textContent = newVoteCount;
        }

        // Update vote button state
        const voteButton = issueCard.querySelector('.vote-btn');
        if (voteButton) {
            if (userVoted) {
                voteButton.classList.add('voted');
                voteButton.innerHTML = `Voted <span class="vote-count">${newVoteCount}</span>`;
            } else {
                voteButton.classList.remove('voted');
                voteButton.innerHTML = `Vote <span class="vote-count">${newVoteCount}</span>`;
            }
        }
    }

    applyFilters() {
        const statusFilter = document.getElementById('status-filter');
        const categoryFilter = document.getElementById('category-filter');

        this.filters.status = statusFilter ? statusFilter.value : '';
        this.filters.category = categoryFilter ? categoryFilter.value : '';

        this.currentPage = 1;
        this.loadIssues(1);
    }

    updatePagination() {
        const paginationContainer = document.getElementById('pagination');
        if (!paginationContainer) return;

        if (this.totalPages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }

        let paginationHtml = '';

        // Previous button
        paginationHtml += `
            <button onclick="app.goToPage(${this.currentPage - 1})" 
                    ${this.currentPage === 1 ? 'disabled' : ''}>
                Previous
            </button>
        `;

        // Page numbers
        const startPage = Math.max(1, this.currentPage - 2);
        const endPage = Math.min(this.totalPages, this.currentPage + 2);

        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `
                <button onclick="app.goToPage(${i})" 
                        ${i === this.currentPage ? 'class="active"' : ''}>
                    ${i}
                </button>
            `;
        }

        // Next button
        paginationHtml += `
            <button onclick="app.goToPage(${this.currentPage + 1})" 
                    ${this.currentPage === this.totalPages ? 'disabled' : ''}>
                Next
            </button>
        `;

        paginationContainer.innerHTML = paginationHtml;
    }

    goToPage(page) {
        if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
            this.loadIssues(page);
        }
    }

    showLoading(show) {
        const loadingElement = document.getElementById('loading');
        const issuesContainer = document.getElementById('issues-list');

        if (loadingElement) {
            loadingElement.style.display = show ? 'block' : 'none';
        }
        if (issuesContainer) {
            issuesContainer.style.display = show ? 'none' : 'grid';
        }
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    performSearch() {
        const searchInput = document.getElementById('search-input');
        const clearBtn = document.getElementById('clear-search');
        
        if (searchInput) {
            this.filters.search = searchInput.value.trim();
            if (this.filters.search) {
                clearBtn.style.display = 'inline-block';
            }
            this.currentPage = 1;
            this.loadIssues();
        }
    }

    clearSearch() {
        const searchInput = document.getElementById('search-input');
        const clearBtn = document.getElementById('clear-search');
        
        if (searchInput) {
            searchInput.value = '';
            this.filters.search = '';
            clearBtn.style.display = 'none';
            this.currentPage = 1;
            this.loadIssues();
        }
    }

    onProvinceChange() {
        const provinceFilter = document.getElementById('province-filter');
        const districtFilter = document.getElementById('district-filter');
        const sectorFilter = document.getElementById('sector-filter');

        const selectedProvince = provinceFilter.value;
        this.filters.province = selectedProvince;

        // Clear and populate districts
        districtFilter.innerHTML = '<option value="">All Districts</option>';
        sectorFilter.innerHTML = '<option value="">All Sectors</option>';
        sectorFilter.style.display = 'none';

        if (selectedProvince) {
            const districts = LocationManager.getDistricts(selectedProvince);
            districts.forEach(district => {
                const option = document.createElement('option');
                option.value = district;
                option.textContent = district;
                districtFilter.appendChild(option);
            });
        }

        // Reset dependent filters
        this.filters.district = '';
        this.filters.sector = '';
        this.applyFilters();
    }

    onDistrictChange() {
        const provinceFilter = document.getElementById('province-filter');
        const districtFilter = document.getElementById('district-filter');
        const sectorFilter = document.getElementById('sector-filter');

        const selectedProvince = provinceFilter.value;
        const selectedDistrict = districtFilter.value;
        this.filters.district = selectedDistrict;

        // Clear and populate sectors
        sectorFilter.innerHTML = '<option value="">All Sectors</option>';

        if (selectedProvince && selectedDistrict) {
            const sectors = LocationManager.getSectors(selectedProvince, selectedDistrict);
            sectors.forEach(sector => {
                const option = document.createElement('option');
                option.value = sector;
                option.textContent = sector;
                sectorFilter.appendChild(option);
            });
            sectorFilter.style.display = 'inline-block';
        } else {
            sectorFilter.style.display = 'none';
        }

        // Reset sector filter
        this.filters.sector = '';
        this.applyFilters();
    }

    populateInitialDistricts() {
        const districtFilter = document.getElementById('district-filter');
        if (districtFilter && typeof LocationManager !== 'undefined') {
            // Get all districts from all provinces
            const allDistricts = LocationManager.getAllDistricts();
            
            // Clear existing options except "All Districts"
            districtFilter.innerHTML = '<option value="">All Districts</option>';
            
            // Add all districts
            allDistricts.forEach(district => {
                const option = document.createElement('option');
                option.value = district;
                option.textContent = district;
                districtFilter.appendChild(option);
            });
        }
    }

    applyFilters() {
        const statusFilter = document.getElementById('status-filter');
        const categoryFilter = document.getElementById('category-filter');
        const provinceFilter = document.getElementById('province-filter');
        const districtFilter = document.getElementById('district-filter');
        const sectorFilter = document.getElementById('sector-filter');

        if (statusFilter) this.filters.status = statusFilter.value;
        if (categoryFilter) this.filters.category = categoryFilter.value;
        if (provinceFilter) this.filters.province = provinceFilter.value;
        if (districtFilter) this.filters.district = districtFilter.value;
        if (sectorFilter) this.filters.sector = sectorFilter.value;

        this.currentPage = 1;
        this.loadIssues();
    }
}

// Initialize the app
const app = new CivicFixApp();
